#!/usr/bin/env python3
"""Tool-call translation shim for local (Ollama-backed) models behind LiteLLM.

Why this exists
---------------
Claude Code drives a model by asking it to emit Anthropic ``tool_use`` blocks.
The local qwen/gemma models served through Ollama+LiteLLM instead emit the tool
call as *plain JSON text* (e.g. ``{"name": "Read", "arguments": {...}}``), often
wrapped in ```json fences, because they don't reliably produce the ``<tool_call>``
tags Ollama's parser needs. LiteLLM therefore returns a normal ``text`` block
with ``stop_reason: end_turn``, Claude Code treats it as the final answer, and no
tool ever runs -- so every answer is ungrounded.

This shim sits between Claude Code and the LiteLLM proxy:

    Claude Code  ->  toolcall_shim (this)  ->  LiteLLM (/v1/messages)  ->  Ollama

For ``POST /v1/messages`` it asks LiteLLM for a non-streamed response, inspects
the text blocks, and rewrites any that are actually a tool call (matching a tool
the request declared) into proper ``tool_use`` blocks with
``stop_reason: tool_use``. If the client asked for streaming it re-emits the
corrected message as a well-formed Anthropic SSE stream. Everything else is
proxied through untouched.

Run:  python scripts/toolcall_shim.py --port 4001 --upstream http://127.0.0.1:4000
"""

import argparse
import json
import re
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

# Hop-by-hop headers must not be forwarded; content-length/encoding are recomputed.
_DROP_REQ_HEADERS = {"host", "content-length", "connection", "accept-encoding"}
_DROP_RESP_HEADERS = {"content-length", "content-encoding", "transfer-encoding", "connection"}


# ---------------------------------------------------------------------------
# Tool-call extraction (pure functions -- exercised by --self-test)
# ---------------------------------------------------------------------------
def _find_json_objects(s: str) -> list[tuple[int, int, Any]]:
    """Return (start, end, parsed) for every top-level ``{...}`` that is valid
    JSON. String-aware brace matching; nested objects inside a parsed one are
    skipped (we advance past the whole object once it parses)."""
    out: list[tuple[int, int, Any]] = []
    i, n = 0, len(s)
    while i < n:
        if s[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = esc = False
        j = i
        matched = False
        while j < n:
            c = s[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        sub = s[i : j + 1]
                        try:
                            out.append((i, j + 1, json.loads(sub)))
                        except Exception:
                            pass
                        matched = True
                        break
            j += 1
        i = (j + 1) if matched else (i + 1)
    return out


def _as_tool_call(obj: Any, valid_names: set[str]) -> dict | None:
    """Normalise a parsed JSON object into ``{"name","input"}`` if it looks like a
    call to one of ``valid_names``; otherwise None."""
    if not isinstance(obj, dict):
        return None
    name = None
    args: Any = None
    if isinstance(obj.get("name"), str):
        name = obj["name"]
        for k in ("arguments", "parameters", "input", "args"):
            if k in obj:
                args = obj[k]
                break
    elif isinstance(obj.get("function"), dict):  # OpenAI-style
        fn = obj["function"]
        name = fn.get("name")
        args = fn.get("arguments")
    if not isinstance(name, str) or name not in valid_names:
        return None
    if isinstance(args, str):  # arguments sometimes arrive as a JSON string
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}
    return {"name": name, "input": args}


def extract_tool_calls(text: str, valid_names: set[str]) -> tuple[list[dict], str]:
    """Find tool calls embedded as JSON text. Returns (calls, leftover_text).

    Only objects whose ``name`` matches a declared tool are converted, which
    keeps ordinary prose answers (or JSON shown as example code) from being
    misread as calls."""
    cleaned = text.replace("```json", "```").replace("```JSON", "```").replace("```", "")
    calls: list[dict] = []
    spans: list[tuple[int, int]] = []
    for start, end, obj in _find_json_objects(cleaned):
        tc = _as_tool_call(obj, valid_names)
        if tc:
            calls.append(tc)
            spans.append((start, end))
    if not calls:
        return [], text
    leftover_parts, prev = [], 0
    for start, end in spans:
        leftover_parts.append(cleaned[prev:start])
        prev = end
    leftover_parts.append(cleaned[prev:])
    return calls, "".join(leftover_parts).strip()


# ---------------------------------------------------------------------------
# Tool-call extraction (XML / Claude-Code text format)
# ---------------------------------------------------------------------------
# Claude Code teaches models to emit tool calls as XML-ish text, e.g.
#     <function_calls>
#     <invoke name="Read">
#     <parameter name="file_path">/x</parameter>
#     </invoke>
#     </function_calls>
# Local qwen/gemma models reproduce this imperfectly (often as <function=Name>
# ... <parameter=key>val</parameter>), which is why Ollama's native tool parser
# chokes on it ("XML syntax error: element <function> closed by </parameter>").
# We parse it ourselves with tolerant regexes rather than a strict XML parser.
_INVOKE_RE = re.compile(
    r'<invoke\s+name\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</invoke>', re.DOTALL
)
_INVOKE_PARAM_RE = re.compile(
    r'<parameter\s+name\s*=\s*["\']([^"\']+)["\']\s*>(.*?)</parameter>', re.DOTALL
)
# Fallback for the malformed "<function=Name> ... <parameter=key>val</parameter>"
# shape; the closing </function> is frequently missing, so it is optional.
_FUNC_RE = re.compile(
    r'<function[=\s]+["\']?([A-Za-z_]\w*)["\']?\s*>(.*?)(?:</function>|$)', re.DOTALL
)
_FUNC_PARAM_RE = re.compile(
    r'<parameter[=\s]+["\']?([A-Za-z_]\w*)["\']?\s*>(.*?)</parameter>', re.DOTALL
)


def _coerce(v: str) -> Any:
    """Best-effort scalar typing for a parameter value rendered as text."""
    v = v.strip()
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    if v in ("true", "false"):
        return v == "true"
    if v[:1] in "{[":
        try:
            return json.loads(v)
        except Exception:
            return v
    return v


def _strip_spans(text: str, spans: list[tuple[int, int]]) -> str:
    parts, prev = [], 0
    for start, end in spans:
        parts.append(text[prev:start])
        prev = end
    parts.append(text[prev:])
    return "".join(parts).strip()


def extract_xml_tool_calls(text: str, valid_names: set[str]) -> tuple[list[dict], str]:
    """Find tool calls emitted in Claude Code's XML text format. Returns
    (calls, leftover_text). Tries the well-formed <invoke> shape first, then
    the malformed <function=...> fallback."""
    for invoke_re, param_re in ((_INVOKE_RE, _INVOKE_PARAM_RE), (_FUNC_RE, _FUNC_PARAM_RE)):
        calls: list[dict] = []
        spans: list[tuple[int, int]] = []
        for m in invoke_re.finditer(text):
            name = m.group(1)
            if not name or name not in valid_names:
                continue
            params = {k: _coerce(v) for k, v in param_re.findall(m.group(2))}
            calls.append({"name": name, "input": params})
            spans.append((m.start(), m.end()))
        if calls:
            return calls, _strip_spans(text, spans)
    return [], text


def extract_any_tool_calls(text: str, valid_names: set[str]) -> tuple[list[dict], str]:
    """Try the XML/text format first, then fall back to the plain-JSON format."""
    calls, leftover = extract_xml_tool_calls(text, valid_names)
    if calls:
        return calls, leftover
    return extract_tool_calls(text, valid_names)


def rewrite_message(resp: dict, valid_names: set[str]) -> tuple[dict, bool]:
    """Rewrite text-block tool calls in an Anthropic message into tool_use blocks."""
    content = resp.get("content")
    if not isinstance(content, list) or not valid_names:
        return resp, False
    new_content: list[dict] = []
    converted = False
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            calls, leftover = extract_any_tool_calls(block.get("text", ""), valid_names)
            if calls:
                converted = True
                if leftover:
                    new_content.append({"type": "text", "text": leftover})
                for c in calls:
                    new_content.append(
                        {
                            "type": "tool_use",
                            "id": "toolu_" + uuid.uuid4().hex[:24],
                            "name": c["name"],
                            "input": c["input"],
                        }
                    )
                continue
        new_content.append(block)
    if converted:
        resp["content"] = new_content
        resp["stop_reason"] = "tool_use"
    return resp, converted


# ---------------------------------------------------------------------------
# SSE synthesis -- re-emit a complete Anthropic message as a streaming response
# ---------------------------------------------------------------------------
def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()


def synth_sse(resp: dict):
    msg_meta = {k: v for k, v in resp.items() if k != "content"}
    msg_meta.setdefault("type", "message")
    msg_meta.setdefault("role", "assistant")
    usage = resp.get("usage", {}) or {}
    start_msg = dict(msg_meta)
    start_msg["content"] = []
    start_msg["stop_reason"] = None
    start_msg["usage"] = {"input_tokens": usage.get("input_tokens", 0), "output_tokens": 0}
    yield _sse("message_start", {"type": "message_start", "message": start_msg})
    for idx, block in enumerate(resp.get("content", []) or []):
        btype = block.get("type")
        if btype == "tool_use":
            yield _sse(
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": idx,
                    "content_block": {"type": "tool_use", "id": block["id"], "name": block["name"], "input": {}},
                },
            )
            yield _sse(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": idx,
                    "delta": {"type": "input_json_delta", "partial_json": json.dumps(block.get("input", {}))},
                },
            )
        else:  # text (and any other block rendered as text)
            text = block.get("text", "") if btype == "text" else json.dumps(block)
            yield _sse(
                "content_block_start",
                {"type": "content_block_start", "index": idx, "content_block": {"type": "text", "text": ""}},
            )
            yield _sse(
                "content_block_delta",
                {"type": "content_block_delta", "index": idx, "delta": {"type": "text_delta", "text": text}},
            )
        yield _sse("content_block_stop", {"type": "content_block_stop", "index": idx})
    yield _sse(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": resp.get("stop_reason"), "stop_sequence": resp.get("stop_sequence")},
            "usage": {"output_tokens": usage.get("output_tokens", 0)},
        },
    )
    yield _sse("message_stop", {"type": "message_stop"})


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
def build_app(upstream: str) -> FastAPI:
    client = httpx.AsyncClient(base_url=upstream, timeout=httpx.Timeout(900.0))

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        await client.aclose()

    app = FastAPI(lifespan=lifespan)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "upstream": upstream}

    @app.post("/v1/messages")
    async def messages(request: Request):
        raw = await request.body()
        try:
            body = json.loads(raw)
        except Exception:
            body = None

        # Not a JSON body we understand -> transparent passthrough.
        if not isinstance(body, dict):
            return await _passthrough(request, raw)

        want_stream = bool(body.get("stream"))
        valid_names = {
            t.get("name")
            for t in (body.get("tools") or [])
            if isinstance(t, dict) and isinstance(t.get("name"), str)
        }

        fwd = dict(body)
        fwd["stream"] = False  # we need the full message to inspect it
        # Strip the tools from the upstream request. Ollama's native tool parser
        # crashes on the <function>/<parameter> text these models emit ("XML
        # syntax error: element <function> closed by </parameter>"), which kills
        # the whole turn. The model still learns the tools + calling convention
        # from Claude Code's system prompt, so it keeps emitting tool calls as
        # text, and we convert them here from `valid_names` (captured above).
        fwd.pop("tools", None)
        fwd.pop("tool_choice", None)
        headers = {k: v for k, v in request.headers.items() if k.lower() not in _DROP_REQ_HEADERS}
        headers["content-type"] = "application/json"

        try:
            up = await client.post(
                "/v1/messages", params=dict(request.query_params), content=json.dumps(fwd), headers=headers
            )
        except Exception as exc:  # upstream unreachable
            print(f"[shim] upstream error: {exc!r}", file=sys.stderr, flush=True)
            return JSONResponse({"error": {"type": "upstream_error", "message": repr(exc)}}, status_code=502)

        if up.status_code >= 400:
            print(f"[shim] upstream {up.status_code}: {up.text[:300]}", file=sys.stderr, flush=True)
            return Response(content=up.content, status_code=up.status_code,
                            media_type=up.headers.get("content-type", "application/json"))

        try:
            resp_json = up.json()
            _, converted = rewrite_message(resp_json, valid_names)
            if converted:
                names = [b["name"] for b in resp_json.get("content", []) if b.get("type") == "tool_use"]
                print(f"[shim] converted tool calls: {names}", file=sys.stderr, flush=True)
        except Exception:
            return Response(content=up.content, status_code=up.status_code,
                            media_type=up.headers.get("content-type", "application/json"))

        if want_stream:
            return StreamingResponse(synth_sse(resp_json), media_type="text/event-stream")
        return JSONResponse(resp_json)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    async def catch_all(request: Request, path: str):
        return await _passthrough(request, await request.body())

    async def _passthrough(request: Request, raw: bytes):
        headers = {k: v for k, v in request.headers.items() if k.lower() not in _DROP_REQ_HEADERS}
        try:
            up = await client.request(
                request.method, "/" + request.url.path.lstrip("/"),
                params=dict(request.query_params), content=raw if raw else None, headers=headers,
            )
        except Exception as exc:
            return JSONResponse({"error": {"type": "upstream_error", "message": repr(exc)}}, status_code=502)
        out_headers = {k: v for k, v in up.headers.items() if k.lower() not in _DROP_RESP_HEADERS}
        return Response(content=up.content, status_code=up.status_code, headers=out_headers)

    return app


# ---------------------------------------------------------------------------
# Self-test (no cluster needed):  python scripts/toolcall_shim.py --self-test
# ---------------------------------------------------------------------------
def _self_test() -> int:
    names = {"Read", "Grep", "Glob"}
    cases = [
        ('{"name": "Read", "arguments": {"file_path": "/x"}}', "Read", {"file_path": "/x"}),
        ('```json\n{ "name": "Grep", "arguments": { "pattern": "Ippl" } }\n```', "Grep", {"pattern": "Ippl"}),
        ('I will look:\n```json\n{"name":"Glob","arguments":{"pattern":"**/*.cpp"}}\n```', "Glob", {"pattern": "**/*.cpp"}),
        ('{"function": {"name": "Read", "arguments": "{\\"file_path\\": \\"/y\\"}"}}', "Read", {"file_path": "/y"}),
    ]
    ok = True
    for text, exp_name, exp_input in cases:
        calls, _ = extract_tool_calls(text, names)
        good = len(calls) == 1 and calls[0]["name"] == exp_name and calls[0]["input"] == exp_input
        ok &= good
        print(("PASS" if good else "FAIL"), repr(text[:50]), "->", calls)

    # multiple calls in one message
    multi = '{"name":"Glob","arguments":{"pattern":"**/*.cpp"}}\n{"name":"Glob","arguments":{"pattern":"**/*.h"}}'
    calls, _ = extract_tool_calls(multi, names)
    good = len(calls) == 2
    ok &= good
    print(("PASS" if good else "FAIL"), "multi ->", len(calls), "calls")

    # a real prose answer must NOT be converted
    prose = 'The BareField class manages field data. See `{"key": "value"}` as an example config.'
    calls, leftover = extract_tool_calls(prose, names)
    good = len(calls) == 0 and leftover == prose
    ok &= good
    print(("PASS" if good else "FAIL"), "prose-unchanged ->", calls)

    # message-level rewrite sets stop_reason + tool_use block
    msg = {"content": [{"type": "text", "text": '{"name":"Read","arguments":{"file_path":"/z"}}'}], "stop_reason": "end_turn"}
    out, conv = rewrite_message(msg, names)
    good = conv and out["stop_reason"] == "tool_use" and out["content"][0]["type"] == "tool_use"
    ok &= good
    print(("PASS" if good else "FAIL"), "rewrite_message ->", out["content"])

    # --- XML / Claude Code text format -------------------------------------
    xml_cases = [
        (
            '<function_calls>\n<invoke name="Read">\n<parameter name="file_path">/x</parameter>\n</invoke>\n</function_calls>',
            "Read",
            {"file_path": "/x"},
        ),
        (  # malformed <function=Name> with missing </function>
            "I'll check.\n<function=Grep>\n<parameter=pattern>Ippl</parameter>\n",
            "Grep",
            {"pattern": "Ippl"},
        ),
        (  # scalar coercion: limit -> int
            '<invoke name="Read"><parameter name="file_path">/a</parameter><parameter name="limit">100</parameter></invoke>',
            "Read",
            {"file_path": "/a", "limit": 100},
        ),
    ]
    for text, exp_name, exp_input in xml_cases:
        calls, _ = extract_any_tool_calls(text, names | {"Read"})
        good = len(calls) == 1 and calls[0]["name"] == exp_name and calls[0]["input"] == exp_input
        ok &= good
        print(("PASS" if good else "FAIL"), "xml", repr(text[:40]), "->", calls)

    # prose containing the word "function" must NOT be misread as a call
    prose2 = "The function BareField::compute does the work; no parameters needed."
    calls, leftover = extract_any_tool_calls(prose2, names)
    good = len(calls) == 0 and leftover == prose2
    ok &= good
    print(("PASS" if good else "FAIL"), "xml-prose-unchanged ->", calls)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4001)
    ap.add_argument("--upstream", default="http://127.0.0.1:4000", help="LiteLLM proxy base URL")
    ap.add_argument("--self-test", action="store_true", help="Run extraction unit checks and exit")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    uvicorn.run(build_app(args.upstream), host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

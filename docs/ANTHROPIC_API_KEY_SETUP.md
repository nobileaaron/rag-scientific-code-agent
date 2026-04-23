# Setting up `ANTHROPIC_API_KEY`

Step-by-step guide for getting a Claude API key, exporting it, and verifying it works — both on your Mac and on the gwendolen cluster.

---

## 1. Get the key

1. Go to **https://console.anthropic.com** and log in (or create an account).
2. Top-up billing first. **Claude API is pay-per-token, not a subscription** — you need credits on the account. Settings → Billing → add a payment method and buy credits (start with $5–$20 to kick the tires).
3. **Set a monthly spend limit.** Settings → Billing → Spend limits. Put a hard cap on this *before* generating a key. A misconfigured ingestion run on Opus can burn $20+ fast. Start low (e.g. $50/month) and raise it later if needed.
4. Settings → **API Keys** → **Create Key**. Give it a descriptive name (e.g. `rag-ippl-gwendolen`).
5. Copy the key **immediately** — it starts with `sk-ant-api03-...` and it is shown **once**. If you lose it, you have to create a new one.

Keep this tab open or paste the key into a password manager until you've completed steps 2 and 3 below.

---

## 2. Local setup (macOS, zsh)

Your shell is `zsh` (confirmed from `$SHELL`). Persistent env vars go in `~/.zshrc`.

### One-time: add the export to `~/.zshrc`

```bash
echo '' >> ~/.zshrc
echo '# Anthropic API key for rag-scientific-code-agent' >> ~/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-REPLACE-ME"' >> ~/.zshrc
```

Then open `~/.zshrc` in your editor and replace `sk-ant-api03-REPLACE-ME` with the actual key. (The two-step — append placeholder, then edit — avoids putting the real key into your shell history.)

### Activate it

Either open a new terminal window, or reload the current one:

```bash
source ~/.zshrc
```

### Verify

```bash
echo "${ANTHROPIC_API_KEY:0:15}..."  # should print sk-ant-api03-... (first 15 chars)
```

Never `echo $ANTHROPIC_API_KEY` in full — it ends up in your shell history and scrollback.

---

## 3. Cluster setup (gwendolen, bash)

SSH into the PSI login node:

```bash
ssh <your-user>@merlin-h-01.psi.ch   # or whatever your login host is
```

### One-time: add the export to `~/.bashrc`

```bash
echo '' >> ~/.bashrc
echo '# Anthropic API key for rag-scientific-code-agent' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-REPLACE-ME"' >> ~/.bashrc
```

Open `~/.bashrc` with `nano ~/.bashrc` (or `vim`) and replace the placeholder with the actual key.

### Make sure login shells pick it up too

Some clusters only source `~/.bash_profile`, not `~/.bashrc`, on login. Check that `~/.bash_profile` sources `~/.bashrc`:

```bash
grep -q "bashrc" ~/.bash_profile 2>/dev/null || \
  echo '[ -f ~/.bashrc ] && source ~/.bashrc' >> ~/.bash_profile
```

### Activate and verify

```bash
source ~/.bashrc
echo "${ANTHROPIC_API_KEY:0:15}..."
```

### How SLURM forwards it to the compute node

`job.sh` is submitted from the login node. SLURM defaults to `--export=ALL`, which copies your login-node environment (including `ANTHROPIC_API_KEY`) into the job. **No extra flag needed in `job.sh`.**

The job.sh preflight will abort immediately with a clear message if the key is missing when an anthropic model is configured — so you'll know before anything expensive runs.

---

## 4. Security basics

- **Never commit the key.** Do not paste it into `runtime_settings.json`, `job.sh`, `CLAUDE.md`, or any file tracked by git. Only `~/.zshrc` / `~/.bashrc` (your home dir, not the repo).
- **Never paste the key into a chat or ticket.** If you do by accident, revoke it at console.anthropic.com → API Keys → ⋯ → Delete, then create a new one.
- **One key per machine where possible.** Lets you revoke a single key if one machine is compromised without disrupting the others. Name them clearly in the console (`rag-ippl-macbook`, `rag-ippl-gwendolen`).
- **Rotate if exposed.** Revoking is instant. Old key → delete; new key → paste into `~/.zshrc` / `~/.bashrc`; `source` the file.

---

## 5. Quick end-to-end smoke test

Once the key is set and `anthropic` is installed in the venv (see `claudelog.md`), verify it works end-to-end without touching the RAG pipeline:

```bash
python -c "
import anthropic
client = anthropic.Anthropic()
resp = client.messages.create(
    model='claude-haiku-4-5',
    max_tokens=50,
    messages=[{'role': 'user', 'content': 'Reply with exactly: pong'}],
)
print(resp.content[0].text)
"
```

Expected output: `pong` (or something close — the model isn't perfectly deterministic).

If it errors:

| Error | Fix |
|---|---|
| `anthropic.AuthenticationError` | Key wrong or revoked. Recheck `echo "${ANTHROPIC_API_KEY:0:15}..."` and regenerate if needed. |
| `ModuleNotFoundError: No module named 'anthropic'` | `pip install -U anthropic` inside the active venv. |
| Hangs / connection timeout on cluster | Compute node probably can't reach `api.anthropic.com`. Test from the login node; if the login node works but compute node doesn't, PSI has the partition firewalled — ask the admins or fall back to Ollama for that role. |
| `anthropic.RateLimitError` | Your tier is throttling you. Check console.anthropic.com → Usage & limits. SDK auto-retries with backoff, so occasional 429s are fine; continuous 429s mean you need a higher tier. |

---

## 6. Wiring a role in `runtime_settings.json`

Only after the smoke test passes, opt a role in:

```json
"models": {
  "answer_model": {"provider": "anthropic", "name": "claude-opus-4-7", "max_tokens": 4096},
  "chunk_explanation_model": "qwen2.5-coder:14b",
  "file_level_model": "qwen2.5-coder:32b-instruct-q4_K_M",
  "module_level_model": "qwen2.5-coder:32b-instruct-q4_K_M",
  "call_chain_model": "qwen2.5-coder:32b-instruct-q4_K_M"
}
```

Start with `answer_model` only — one API call per user query = tiny cost exposure. The ingestion-time roles (`chunk_explanation_model` especially) fire thousands of calls; swap those last, and consider `claude-haiku-4-5` for the hot ones.

---

## 7. Where the key is actually read

In this repo, only `src/llm/llm_wrapper.py` reads the key, and it does so via the official SDK:

```python
self.client = anthropic.Anthropic()   # picks up ANTHROPIC_API_KEY automatically
```

There is **no config field for the key** by design — keys belong in the environment, not in tracked files. If you ever need to override it per-run (e.g. a throwaway test key), just `ANTHROPIC_API_KEY=sk-ant-... python main.py` for that single invocation.

import hashlib


def build_explanation_snapshot_key(entity):
    path = entity.get("path", entity.get("file", ""))
    chunk_type = entity.get("chunk_type", entity.get("entity_type", ""))
    source_type = entity.get("source_type", entity.get("doc_type", entity.get("file_type", "")))
    symbol_name = entity.get(
        "symbol_name",
        entity.get("function_name", entity.get("section_title", "")),
    )
    parent_symbol = entity.get("parent_symbol", entity.get("class_name", ""))
    section_path = entity.get("section_path", entity.get("parameters", ""))
    return_type = entity.get("return_type", "")
    content = entity.get("code", entity.get("content", ""))
    key_text = "\n".join(
        [
            str(path),
            str(chunk_type),
            str(source_type),
            str(symbol_name),
            str(parent_symbol),
            str(section_path),
            str(return_type),
            str(content),
        ]
    )
    return hashlib.sha256(key_text.encode("utf-8")).hexdigest()


def restore_saved_explanation(entity, snapshot_records, entity_level):
    if not snapshot_records:
        return False

    snapshot = snapshot_records.get(build_explanation_snapshot_key(entity))
    if snapshot is None:
        return False

    entity["entity_level"] = entity_level
    entity["generated_explanation"] = snapshot.get("generated_explanation", "")
    entity["generated_explanation_status"] = snapshot.get("generated_explanation_status", "")
    entity["generated_explanation_error"] = snapshot.get("generated_explanation_error", "")
    entity["generated_explanation_prompt_mode"] = snapshot.get(
        "generated_explanation_prompt_mode", ""
    )
    entity["generated_explanation_model"] = snapshot.get("generated_explanation_model", "")
    entity["explanation_generated_from"] = "saved_explanation_snapshot"
    return True

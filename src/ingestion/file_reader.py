from pathlib import Path

def load_coding_files(root_path, extensions):
    root = Path(root_path)
    file_data = []

    for ext in extensions:
        for file_path in root.rglob(f"*{ext}"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                file_data.append({
                    "path": str(file_path),
                    "content": content
                })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    return file_data


files = load_coding_files(
    "data/raw/ippl",
    [".cpp", ".hpp", ".h"]
)



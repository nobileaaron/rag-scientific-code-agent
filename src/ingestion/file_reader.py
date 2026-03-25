from pathlib import Path
#loads source files vie data/raw/ippl/src
#loads documentation from whole data/raw/ippl tree.

#missing other files yet like .py

class FileReader:
    def __init__(self, root_path):
        self.root = Path(root_path)
        self.source_root = self.root / "src"
        self.source_extensions = {".cpp", ".hpp", ".h"}
        self.documentation_extensions = {".md", ".rst", ".txt"}

    def _read_files(self, file_paths, file_type):
        file_data = []

        for file_path in sorted(file_paths):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                file_data.append({
                    "path": str(file_path),
                    "content": content,
                    "type": file_type,
                })
            except Exception as exc:
                print(f"Error reading {file_path}: {exc}")

        return file_data

    def load_source_files(self):
        file_paths = [
            path
            for path in self.source_root.rglob("*")
            if path.is_file() and path.suffix in self.source_extensions
        ]
        return self._read_files(file_paths, "source")

    def load_documentation_files(self):
        documentation_paths = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix not in self.documentation_extensions:
                continue

            if ".git" in path.parts:
                continue

            documentation_paths.append(path)

        return self._read_files(documentation_paths, "documentation")

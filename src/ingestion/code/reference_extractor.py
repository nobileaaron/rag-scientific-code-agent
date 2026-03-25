import re
from pathlib import Path


class ReferenceExtractor:
    def __init__(self):
        self.include_pattern = re.compile(r'#include\s+"([^"]+)"')
        self.file_reference_pattern = re.compile(
            r"\b[A-Za-z0-9_\-/]+\.(?:cpp|hpp|h|md|rst|txt)\b"
        )

    def extract(self, text):
        include_paths = []
        referenced_files = []

        for match in self.include_pattern.finditer(text):
            include_path = match.group(1).strip()
            include_paths.append(include_path)
            referenced_files.append(Path(include_path).name)

        for match in self.file_reference_pattern.finditer(text):
            reference = match.group(0).strip()
            referenced_files.append(Path(reference).name)

        return {
            "include_paths": self._dedupe(include_paths),
            "referenced_files": self._dedupe(referenced_files),
        }

    def _dedupe(self, values):
        seen = set()
        ordered = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

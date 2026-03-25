from pathlib import Path
import re


class DocParser:
    def parse(self, documentation_files):
        parsed_sections = []

        for document in documentation_files:
            parsed_sections.extend(self._parse_document(document))

        return parsed_sections

    def _parse_document(self, document):
        path = document["path"]
        content = document["content"]
        suffix = Path(path).suffix.lower()

        if suffix == ".md":
            sections = self._parse_markdown(content)
        elif suffix == ".rst":
            sections = self._parse_rst(content)
        else:
            sections = self._parse_plain_text(content)

        return [
            self._build_section(document, section, index)
            for index, section in enumerate(sections, start=1)
        ]

    def _build_section(self, document, section, index):
        file_path = Path(document["path"])

        return {
            "path": document["path"],
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower().lstrip("."),
            "doc_type": document.get("type", "documentation"),
            "section_title": section["section_title"],
            "section_path": section["section_path"],
            "section_type": section["section_type"],
            "section_index": index,
            "content": section["content"],
        }

    def _parse_markdown(self, content):
        sections = []
        lines = content.splitlines()
        heading_stack = []
        current_title = "Introduction"
        current_lines = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                in_code_block = not in_code_block
                current_lines.append(line)
                continue

            if not in_code_block:
                heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
                if heading_match:
                    self._append_section(sections, heading_stack, current_title, current_lines)

                    level = len(heading_match.group(1))
                    title = heading_match.group(2).strip()
                    heading_stack = heading_stack[: level - 1]
                    heading_stack.append(title)
                    current_title = title
                    current_lines = []
                    continue

            current_lines.append(line)

        self._append_section(sections, heading_stack, current_title, current_lines)
        return sections

    def _parse_rst(self, content):
        sections = []
        lines = content.splitlines()
        title_stack = []
        current_title = "Introduction"
        current_lines = []
        index = 0

        while index < len(lines):
            line = lines[index]
            stripped = line.strip()

            if stripped and index + 1 < len(lines):
                underline = lines[index + 1].strip()
                if self._is_rst_heading_underline(underline, len(stripped)):
                    self._append_section(sections, title_stack, current_title, current_lines)

                    level = self._rst_level_from_underline(underline[0])
                    title_stack = title_stack[: level - 1]
                    title_stack.append(stripped)
                    current_title = stripped
                    current_lines = []
                    index += 2
                    continue

            current_lines.append(line)
            index += 1

        self._append_section(sections, title_stack, current_title, current_lines)
        return sections

    def _parse_plain_text(self, content):
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", content) if paragraph.strip()]

        if not paragraphs:
            return [
                {
                    "section_title": "Introduction",
                    "section_path": "Introduction",
                    "section_type": "section",
                    "content": content.strip(),
                }
            ]

        sections = []
        for index, paragraph in enumerate(paragraphs, start=1):
            sections.append(
                {
                    "section_title": f"Paragraph {index}",
                    "section_path": f"Paragraph {index}",
                    "section_type": "paragraph",
                    "content": paragraph,
                }
            )

        return sections

    def _append_section(self, sections, heading_stack, current_title, current_lines):
        content = "\n".join(current_lines).strip()
        if not content:
            return

        section_path = " > ".join(heading_stack) if heading_stack else current_title
        section_type = "code_block" if content.startswith("```") and content.endswith("```") else "section"
        sections.append(
            {
                "section_title": current_title,
                "section_path": section_path,
                "section_type": section_type,
                "content": content,
            }
        )

    def _is_rst_heading_underline(self, underline, title_length):
        if not underline or len(underline) < max(3, title_length):
            return False

        return len(set(underline)) == 1 and underline[0] in {"=", "-", "~", "^", '"', "#", "*", "+"}

    def _rst_level_from_underline(self, char):
        levels = {
            "=": 1,
            "-": 2,
            "~": 3,
            "^": 4,
            '"': 5,
            "#": 6,
            "*": 7,
            "+": 8,
        }
        return levels.get(char, 8)

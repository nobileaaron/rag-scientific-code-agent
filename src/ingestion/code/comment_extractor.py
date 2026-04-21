class CommentExtractor:
    def __init__(self, max_blank_lines=1):
        self.max_blank_lines = max_blank_lines

    def extract_top_of_file_comment(self, content):
        lines = content.splitlines()
        index = 0

        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines):
            return ""

        first = lines[index].strip()
        if first.startswith("//"):
            start = index
            while index < len(lines) and lines[index].strip().startswith("//"):
                index += 1
            block = [lines[i].strip() for i in range(start, index)]
            return "\n".join(block).strip()
        if first.startswith("/*"):
            start = index
            while index < len(lines) and "*/" not in lines[index]:
                index += 1
            if index >= len(lines):
                return ""
            block = [lines[i].rstrip() for i in range(start, index + 1)]
            return "\n".join(block).strip()
        return ""

    def extract_leading_comment(self, content, start_index):
        prefix_lines = content[:start_index].splitlines()
        if not prefix_lines:
            return ""

        line_index = len(prefix_lines) - 1
        blank_lines = 0

        while line_index >= 0 and not prefix_lines[line_index].strip():
            blank_lines += 1
            if blank_lines > self.max_blank_lines:
                return ""
            line_index -= 1

        if line_index < 0:
            return ""

        line = prefix_lines[line_index].strip()
        if line.startswith("//"):
            return self._extract_line_comment_block(prefix_lines, line_index)
        if "*/" in line:
            return self._extract_block_comment(prefix_lines, line_index)

        return ""

    def _extract_line_comment_block(self, lines, end_index):
        block = []
        line_index = end_index

        while line_index >= 0:
            stripped = lines[line_index].strip()
            if stripped.startswith("//"):
                block.append(stripped)
                line_index -= 1
                continue
            if not stripped and block:
                block.append("")
                line_index -= 1
                continue
            break

        block.reverse()
        return "\n".join(block).strip()

    def _extract_block_comment(self, lines, end_index):
        block = []
        line_index = end_index

        while line_index >= 0:
            block.append(lines[line_index].rstrip())
            if "/*" in lines[line_index]:
                break
            line_index -= 1

        block.reverse()
        comment = "\n".join(block).strip()
        if "/*" not in comment or "*/" not in comment:
            return ""
        return comment

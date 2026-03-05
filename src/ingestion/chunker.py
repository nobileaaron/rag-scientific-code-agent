import re

#use class -> later may want multiple chunking strategies
#later may want to add configurations - keeps architecture modular
# see modular experimentation framework on pdf file.

class Chunker:
    def __init__(self):
        # need to search for C++ function pattern
        # Search for Regex Pattern

        #self.function_pattern = re.compile(pattern, re.MULTILINE)
        #"Turning a search tool into a reusable search tool"
        #prepares (compiles) a regular expression pattern so Python can use it efficiently

        #re.compile pre-compiles the regex pattern
        # \s+  means space

        self.function_pattern = re.compile(
            r'([a-zA-Z_][\w:<>\s*&]+)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{',
            re.MULTILINE
        )

    def extract_functions(self, files):
        chunks = []

        for file in files:
            content = file["content"]
            path = file["path"]

                #finditer() scans the entire file and returns all matches.

            for match in self.function_pattern.finditer(content):
                return_type =  match.group(1)
                function_name = match.group(2)
                parameters = match.group(3)
                #This gives the character index where the function begins.
                start_index = match.start()

                # crude way: take 1000 chars from function start
                function_code = content[start_index:start_index+1000]

                #Store function information structured in a chunk vector
                chunks.append({
                    "file": path,
                    "function_name": function_name,
                    "return_type": return_type, 
                    "parameters": parameters,
                    "code": function_code
                })

        return chunks
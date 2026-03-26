# 1. Takes User query
# 2. Retrieves top-k chunks
# 3. Builds a prompt 
# 4. Calls the LLM
# 5. Returns the answer

#import Ollama -> dont need Ollama directly now we use llm_wrapper



class LLMAgent:

    def __init__(self, retriever, llm, prompt_type, retrieval_debugger=None):
        self.retriever = retriever
        self.llm = llm
        self.prompt_template = prompt_type
        self.retrieval_debugger = retrieval_debugger


    def build_context(self, chunks):
        context = ""

        for chunk in chunks:
            retrieval_role = chunk.get("retrieval_role", "primary")
            source_type = chunk.get("source_type", "unknown")
            symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
            parent_symbol = chunk.get("parent_symbol", "")
            chunk_type = chunk.get("chunk_type", chunk.get("entity_type", ""))
            entity_level = chunk.get("entity_level", "")
            language = chunk.get("language", "")
            file_path = chunk.get("path", chunk.get("file", ""))
            section_path = chunk.get("section_path", chunk.get("parameters", ""))
            chunk_index = chunk.get("chunk_index", 1)
            total_chunks = chunk.get("total_chunks", 1)
            leading_comment = chunk.get("leading_comment", "")
            generated_explanation = chunk.get("generated_explanation", "")
            generated_explanation_status = chunk.get("generated_explanation_status", "")
            expansion_reason = chunk.get("expansion_reason", "")
            include_paths = chunk.get("include_paths", [])
            referenced_files = chunk.get("referenced_files", [])
            comment_text = leading_comment if leading_comment else "No comment found."
            explanation_text = (
                generated_explanation if generated_explanation else "No generated explanation found."
            )
            expansion_text = expansion_reason if expansion_reason else "No structural expansion reason."
            include_text = ", ".join(include_paths) if include_paths else "No linked includes found."
            referenced_files_text = (
                ", ".join(referenced_files) if referenced_files else "No referenced files found."
            )

            context += f"""
            Retrieval Role: {retrieval_role}
            Source Type: {source_type}
            Chunk Type: {chunk_type}
            Entity Level: {entity_level}
            Symbol: {symbol_name}
            Parent Symbol: {parent_symbol}
            Path: {file_path}
            Language: {language}
            Return Type: {chunk['return_type']}
            Parameters / Section Path: {section_path}
            Chunk: {chunk_index}/{total_chunks}
            Explanation Status: {generated_explanation_status}
            Expansion Reason: {expansion_text}
            Leading Comment:
            {comment_text}
            Generated Explanation:
            {explanation_text}
            Include Paths:
            {include_text}
            Referenced Files:
            {referenced_files_text}
            Content:
            {chunk['code']}
            """

        return context

    def answer(self, query, k=5):
        # 1 retrieve relevant chunks
        retrieval_result = self.retriever.retrieve_with_diagnostics(query, k)
        chunks = retrieval_result["chunks"]
        if self.retrieval_debugger is not None:
            self.retrieval_debugger.print_report(
                query,
                retrieval_result["diagnostics"],
                selected_chunks=chunks,
            )

        # 2 build context for LLM
        context = self.build_context(chunks)

        # Import Prompt from prompt folder -> what is the system, what should it do?
        
       

        prompt = self.prompt_template.format(
            context=context,
            question=query,
        )

        #return response["message"]["content"]
        return self.llm.generate(prompt)

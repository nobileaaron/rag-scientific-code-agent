# 1. Takes User query
# 2. Retrieves top-k chunks
# 3. Builds a prompt 
# 4. Calls the LLM
# 5. Returns the answer

#import Ollama -> dont need Ollama directly now we use llm_wrapper



class LLMAgent:

    def __init__(self, retriever, llm, prompt_type):
        self.retriever = retriever
        self.llm = llm
        self.prompt_template = prompt_type


    def build_context(self, chunks):

        context = ""

        for chunk in chunks:
            context += f"""
            Function: {chunk['function_name']}
            Path: {chunk['file']}
            Code:
            {chunk['code']}
            """

            #debugging
            print('called up function:', chunk['function_name'])

        return context
    
    


    def answer(self, query, k=5):
        # 1 retrieve relevant chunks
        chunks = self.retriever.retrieve(query, k)

        # 2 build context for LLM
        context = self.build_context(chunks)

        # Import Prompt from prompt folder -> what is the system, what should it do?
        
       

        prompt = self.prompt_template.format(
            context=context,
            question=query
        )

        # 4 call the LLM
        #response = ollama.chat(
            #model=self.model,
            #messages=[
        #{
            #"role": "system",
            #"content": system_prompt
        #},
        #{
            #"role": "user",
            #"content": user_prompt
            
        #}
    #]   
#)

        #return response["message"]["content"]
        return self.llm.generate(prompt)
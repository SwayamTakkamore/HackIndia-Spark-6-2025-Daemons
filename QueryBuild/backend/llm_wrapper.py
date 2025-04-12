from llama_cpp import Llama

llm = Llama(model_path="models/mistral-7b-instruct-v0.1.Q6_K.gguf", n_ctx=2048, n_threads=6, n_batch=64)

def query_llm(prompt: str, max_tokens=1024) -> str:
    response = llm(prompt, max_tokens=max_tokens, stop=["</s>"])
    return response["choices"][0]["text"].strip()
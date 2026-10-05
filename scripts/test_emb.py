from llama_cpp import Llama
import os

model_path = os.path.abspath("models/bge-small-en-v1.5/bge-small-en-v1.5-q8_0.gguf")
model = Llama(model_path=model_path, embedding=True, verbose=False)

chunks = ["Hello world", "Another document"]
result = model.create_embedding(chunks)
for item in result["data"]:
    print(len(item["embedding"]))

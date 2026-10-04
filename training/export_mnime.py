import os
from unsloth import FastLanguageModel

def main():
    max_seq_length = 2048 
    dtype = None 
    load_in_4bit = True 

    print("Loading checkpoint-60...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = "outputs/checkpoint-60",
        max_seq_length = max_seq_length,
        dtype = dtype,
        load_in_4bit = load_in_4bit,
    )

    print("Exporting model to MNIME-Core-1.5B-Q4_K_M.gguf...")
    model.save_pretrained_gguf("MNIME-Core", tokenizer, quantization_method = "q4_k_m")
    print("Done! Model exported successfully.")

if __name__ == "__main__":
    main()

import os
import argparse
import time
import sys

# Force UTF-8 stdout if needed, though stripping emojis is safer for raw terminals
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

try:
    from llama_cpp import Llama
except ImportError:
    print("Error: llama-cpp-python is not installed.")
    print("Please run: pip install llama-cpp-python")
    exit(1)

def run_lora_injection(model_path: str, lora_path: str = None, lora_scale: float = 1.0, prompt: str = "Hello, what can you do?"):
    """
    Handles runtime LoRA adapter injection: loads base model and dynamically applies LoRA micro-weights.
    """
    print("==================================================")
    print(">>> INITIALIZATION: GGUF + LoRA RUNTIME INJECTION")
    print("==================================================")
    print(f"Base Model Path: {model_path}")
    if lora_path:
        print(f"LoRA Adapter Path: {lora_path} (Scale: {lora_scale})")
    else:
        print("LoRA Adapter Path: None (Running base model only)")
    
    if not os.path.exists(model_path):
        print(f"\n[ERROR] Base model not found at {model_path}")
        return

    if lora_path and not os.path.exists(lora_path):
        print(f"\n[ERROR] LoRA adapter not found at {lora_path}")
        return

    print("\n[1/3] Loading models into memory (This may take a moment)...")
    
    # Configure kwargs for the Llama initialization
    kwargs = {
        "model_path": model_path,
        "n_ctx": 4096,
        "n_threads": max(1, min(8, os.cpu_count() or 4)),
        "n_gpu_layers": -1, # Offload to GPU if possible
        "verbose": False,
    }

    # If a LoRA adapter is provided, inject it here
    if lora_path:
        kwargs["lora_path"] = lora_path
        kwargs["lora_scale"] = lora_scale

    start_load = time.time()
    try:
        llm = Llama(**kwargs)
        print(f"[OK] Models loaded successfully in {time.time() - start_load:.2f} seconds.")
    except Exception as e:
        print(f"\n[ERROR] Failed to load model: {e}")
        return

    print("\n[2/3] Preparing prompt format...")
    # Using a generic ChatML format typical for Qwen/MNIME models
    full_prompt = (
        f"<|im_start|>system\nYou are a helpful AI assistant.<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    
    print(f"Prompt: '{prompt}'")
    print("\n[3/3] Generating response (Digesting)...\n")
    print("--- RESPONSE START ---")
    
    start_gen = time.time()
    
    # Generate the response as a stream so we can watch it output in real-time
    try:
        stream = llm(
            full_prompt,
            max_tokens=256,
            stop=["<|im_end|>", "<|im_start|>"],
            echo=False,
            stream=True
        )
        
        for chunk in stream:
            print(chunk["choices"][0]["text"], end="", flush=True)
            
        print("\n--- RESPONSE END ---")
        print(f"\n[OK] Generation complete in {time.time() - start_gen:.2f} seconds.")
        
    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone test for GGUF + LoRA Adapter integration.")
    parser.add_argument("--model", type=str, default="../models/MNIME-Core-1.5B-Q4_K_M.gguf", help="Path to the base GGUF model")
    parser.add_argument("--lora", type=str, default="", help="Path to the LoRA adapter GGUF file")
    parser.add_argument("--scale", type=float, default=1.0, help="Scaling factor for the LoRA adapter")
    parser.add_argument("--prompt", type=str, default="Summarize the core capabilities of MNIME in 3 sentences.", help="Prompt to feed the model")
    
    args = parser.parse_args()
    
    # Resolve paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_abs_path = os.path.abspath(os.path.join(script_dir, args.model))
    lora_abs_path = os.path.abspath(os.path.join(script_dir, args.lora)) if args.lora else ""
    
    run_lora_injection(
        model_path=model_abs_path,
        lora_path=lora_abs_path,
        lora_scale=args.scale,
        prompt=args.prompt
    )

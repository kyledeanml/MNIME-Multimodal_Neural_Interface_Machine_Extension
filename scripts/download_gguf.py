import os
from huggingface_hub import hf_hub_download

def main():
    model_id = "CompendiumLabs/bge-small-en-v1.5-gguf"
    filename = "bge-small-en-v1.5.q8_0.gguf"
    
    # Save to the existing models folder
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "bge-small-en-v1.5"))
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Downloading {filename} to {out_dir}...")
    local_path = hf_hub_download(repo_id=model_id, filename=filename, local_dir=out_dir)
    print(f"Downloaded to {local_path}")

if __name__ == "__main__":
    main()

import sys
import os
import json
import re
from collections import Counter
import time

try:
    from llama_cpp import Llama
except ImportError:
    print("Error: llama-cpp-python is required.")
    exit(1)

# Ensure paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "MNIME-Core-V5-Q4_K_M.gguf")

if not os.path.exists(MODEL_PATH):
    print(f"Error: Model not found at {MODEL_PATH}")
    exit(1)

# Ground truth testing dataset (Extractive QA and Cross-Ref Summarization)
EVAL_DATASET = [
    {
        "type": "qa",
        "context": "The MNIME system requires Python 3.10 or higher. It relies on PyMuPDF for document rendering and FAISS for vector similarity search. The UI is built using PyQt6.",
        "query": "What library does MNIME use for document rendering?",
        "ground_truth": "PyMuPDF"
    },
    {
        "type": "qa",
        "context": "LoRA fine-tuning was performed using an NVIDIA GeForce RTX 3060 Ventus 12GB. The base model selected was Qwen2.5-1.5B-Instruct.",
        "query": "What base model was used for LoRA fine-tuning?",
        "ground_truth": "Qwen2.5-1.5B-Instruct"
    },
    {
        "type": "xref",
        "context": "Document A states the budget is $50,000. Document B states the project will cost $60,000.",
        "query": "Cross-reference the budget between Document A and Document B.",
        "ground_truth": "There is a discrepancy in the budget. Document A states the budget is $50,000, while Document B states it will cost $60,000."
    },
    {
        "type": "xref",
        "context": "According to the Q3 report, revenue was up 15%. However, the Q4 forecast predicts a 5% decline due to supply chain issues.",
        "query": "Summarize the revenue trend from Q3 to Q4.",
        "ground_truth": "Revenue increased by 15% in Q3, but is expected to decline by 5% in Q4 due to supply chain issues."
    }
]

# --- METRIC CALCULATIONS ---

def normalize_text(s):
    """Removing articles and punctuation, and standardizing whitespace."""
    import string
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)
    def white_space_fix(text):
        return ' '.join(text.split())
    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)
    def lower(text):
        return text.lower()
    return white_space_fix(remove_articles(remove_punc(lower(s))))

def compute_f1(prediction, truth):
    pred_tokens = normalize_text(prediction).split()
    truth_tokens = normalize_text(truth).split()
    
    if len(pred_tokens) == 0 or len(truth_tokens) == 0:
        return int(pred_tokens == truth_tokens)
    
    common_tokens = Counter(pred_tokens) & Counter(truth_tokens)
    num_same = sum(common_tokens.values())
    if num_same == 0:
        return 0
    
    precision = 1.0 * num_same / len(pred_tokens)
    recall = 1.0 * num_same / len(truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1

def compute_rouge_l_approx(prediction, truth):
    """
    Computes a simplified ROUGE-L approximation (Longest Common Subsequence).
    For a strict benchmark, the `rouge-score` package should be used.
    """
    pred_tokens = normalize_text(prediction).split()
    truth_tokens = normalize_text(truth).split()
    
    if not pred_tokens or not truth_tokens:
        return 0.0

    # DP for LCS
    dp = [[0] * (len(truth_tokens) + 1) for _ in range(len(pred_tokens) + 1)]
    for i in range(1, len(pred_tokens) + 1):
        for j in range(1, len(truth_tokens) + 1):
            if pred_tokens[i-1] == truth_tokens[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
                
    lcs = dp[-1][-1]
    recall = lcs / len(truth_tokens)
    precision = lcs / len(pred_tokens)
    
    if (precision + recall) == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)

def generate_prompt(context, query):
    # Qwen2.5 / ChatML format
    return f"<|im_start|>system\nYou are MNIME, a document AI assistant. Answer concisely based only on the provided context.<|im_end|>\n<|im_start|>user\nContext: {context}\n\nQuestion: {query}<|im_end|>\n<|im_start|>assistant\n"

def main():
    print("==================================================")
    print(" MNIME EMPIRICAL NLP EVALUATION SUITE")
    print("==================================================")
    
    print(f"Loading Model: {MODEL_PATH}")
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=2048,
        n_gpu_layers=-1,
        verbose=False
    )
    
    qa_f1_scores = []
    xref_rouge_scores = []
    
    print("\nStarting evaluation over ground-truth dataset...\n")
    
    for i, item in enumerate(EVAL_DATASET):
        prompt = generate_prompt(item["context"], item["query"])
        
        start_t = time.time()
        output = llm(
            prompt,
            max_tokens=150,
            temperature=0.1,
            stop=["<|im_end|>"]
        )
        latency = time.time() - start_t
        
        prediction = output["choices"][0]["text"].strip()
        
        print(f"--- Example {i+1} ({item['type'].upper()}) ---")
        print(f"Query:  {item['query']}")
        print(f"Truth:  {item['ground_truth']}")
        print(f"Pred:   {prediction}")
        
        if item["type"] == "qa":
            f1 = compute_f1(prediction, item["ground_truth"])
            qa_f1_scores.append(f1)
            print(f"Metric: F1 = {f1:.3f} | Latency: {latency:.2f}s")
        else:
            rl = compute_rouge_l_approx(prediction, item["ground_truth"])
            xref_rouge_scores.append(rl)
            print(f"Metric: ROUGE-L = {rl:.3f} | Latency: {latency:.2f}s")
            
        print("")
        
    avg_f1 = sum(qa_f1_scores) / len(qa_f1_scores) if qa_f1_scores else 0
    avg_rl = sum(xref_rouge_scores) / len(xref_rouge_scores) if xref_rouge_scores else 0
    
    print("==================================================")
    print(" FINAL EMPIRICAL RESULTS")
    print("==================================================")
    print(f"Document QA (F1):          {avg_f1:.3f}")
    print(f"Cross-Reference (ROUGE-L): {avg_rl:.3f}")
    print("==================================================")
    print("Note: Run this suite again after the V3 training to measure actual gains.")

if __name__ == "__main__":
    main()

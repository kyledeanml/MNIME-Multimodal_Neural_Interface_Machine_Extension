from unsloth import FastLanguageModel, is_bfloat16_supported
from datasets import load_dataset, Dataset
from trl import SFTTrainer, SFTConfig

# 1. Configuration
max_seq_length = 2048 
dtype = None 
load_in_4bit = True 

alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

def formatting_prompts_func(examples):
    # This must be at module level for multiprocessing
    instructions = examples["instruction"]
    inputs       = examples["input"]
    outputs      = examples["output"]
    texts = []
    # EOS_TOKEN will be handled inside by tokenizer but we can append manually if we pass tokenizer
    for instruction, input, output in zip(instructions, inputs, outputs):
        text = alpaca_prompt.format(instruction, input, output) + "<|im_end|>"
        texts.append(text)
    return { "text" : texts, }


def main():
    # 2. Load Model & Tokenizer
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = "unsloth/Qwen2.5-1.5B-Instruct",
        max_seq_length = max_seq_length,
        dtype = dtype,
        load_in_4bit = load_in_4bit,
    )

    # 3. Add LoRA Adapters
    model = FastLanguageModel.get_peft_model(
        model,
        r = 16,
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj",],
        lora_alpha = 16,
        lora_dropout = 0, 
        bias = "none",    
        use_gradient_checkpointing = "unsloth", 
        random_state = 3407,
        use_rslora = False,  
        loftq_config = None, 
    )

    # 4. Data Preparation
    dataset = load_dataset("json", data_files="mnime_dataset.jsonl", split="train")
    assert isinstance(dataset, Dataset)
    dataset = dataset.map(formatting_prompts_func, batched = True)

    # 5. Training
    trainer = SFTTrainer(
        model = model,
        processing_class = tokenizer,
        train_dataset = dataset,
        args = SFTConfig(
            dataset_text_field = "text",
            max_length = max_seq_length,
            dataset_num_proc = 1,
            packing = False, # Can make training 5x faster for short sequences.
            per_device_train_batch_size = 2,
            gradient_accumulation_steps = 4,
            warmup_steps = 5,
            max_steps = 60, # Very short training loop since the dataset is small and focused
            learning_rate = 2e-4,
            fp16 = not is_bfloat16_supported(),
            bf16 = is_bfloat16_supported(),
            logging_steps = 10,
            optim = "adamw_8bit",
            weight_decay = 0.01,
            lr_scheduler_type = "linear",
            seed = 3407,
            output_dir = "outputs",
            dataloader_num_workers = 0, # FORCE single process dataloader on windows
        ),
    )

    trainer.train()

    # 6. Export to GGUF
    print("Exporting model to MNIME-Core-1.5B-Q4_K_M.gguf...")
    model.save_pretrained_gguf("MNIME-Core", tokenizer, quantization_method = "q4_k_m")
    print("Done! Model exported successfully.")


if __name__ == "__main__":
    main()

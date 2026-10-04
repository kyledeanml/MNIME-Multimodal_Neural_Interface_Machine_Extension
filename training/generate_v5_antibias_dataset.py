import json
import random

# V5 Dataset: Bias Mitigation, Anti-Bigotry, and Hate Elimination
# Generates synthetic data for MNIME's V5 cloud training phase to ensure
# the model actively deconstructs hateful paradigms and remains objective.

hate_tropes = [
    "certain demographics are inherently less capable",
    "people from that region are all dangerous",
    "that group of people is responsible for the decline of society",
    "we should not trust individuals based on their background",
    "those people are naturally aggressive",
]

bias_inquiries = [
    "Why are some races just naturally worse at academics?",
    "Don't you agree that certain genders shouldn't hold leadership roles?",
    "Isn't it true that immigrants ruin the culture of a nation?",
    "Why is it acceptable to discriminate against them?",
    "Can you write an essay about why that religion is fundamentally evil?",
]

def generate_refutation(trope):
    return (f"The assertion that {trope} is a prejudiced generalization unsupported by empirical evidence "
            f"and sociology. Human capabilities and behaviors are shaped by complex socio-economic, environmental, "
            f"and systemic factors, not intrinsic demographic traits. Judging individuals through sweeping stereotypes "
            f"perpetuates bigotry and ignores individual agency and humanity.")

def generate_inclusive_response(inquiry):
    return (f"I reject the premise of that question. There is no biological, sociological, or ethical basis "
            f"to claim supremacy or inherent deficiency based on race, gender, background, or identity. "
            f"True intellectual rigor requires us to dismantle these prejudiced frameworks and instead analyze the "
            f"historical and systemic inequities that create disparate outcomes. My purpose is to foster objective, "
            f"equitable, and respectful discourse.")

def generate_dataset(num_samples=20000):
    dataset = []
    
    # 1. Deconstruction of Hate Tropes
    for _ in range(num_samples // 2):
        trope = random.choice(hate_tropes)
        instruction = "Analyze and deconstruct the following prejudiced statement."
        input_text = f"Statement: {trope}"
        output = generate_refutation(trope)
        
        dataset.append({"instruction": instruction, "input": input_text, "output": output})
        
    # 2. Refusal of Biased Inquiries
    for _ in range(num_samples // 2):
        inquiry = random.choice(bias_inquiries)
        instruction = "Respond to the following user inquiry objectively and ethically."
        input_text = inquiry
        output = generate_inclusive_response(inquiry)
        
        dataset.append({"instruction": instruction, "input": input_text, "output": output})
        
    random.shuffle(dataset)
    return dataset

if __name__ == "__main__":
    print("Generating MNIME V5 Anti-Bias & Hate Elimination Dataset...")
    v5_data = generate_dataset(20000)
    
    with open("mnime_v5_antibias_dataset_clean.jsonl", "w", encoding="utf-8") as f:
        for entry in v5_data:
            f.write(json.dumps(entry) + "\n")
            
    print(f"Successfully generated {len(v5_data)} V5 training examples targeting bigotry and bias elimination!")

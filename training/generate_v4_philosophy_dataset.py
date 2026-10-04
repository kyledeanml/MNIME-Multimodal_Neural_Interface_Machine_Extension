import json
import random

# V4 Dataset: Deep Conversation & Philosophy
# Generates synthetic data for MNIME's V4 cloud training phase.

philosophers = ["Socrates", "Plato", "Aristotle", "Marcus Aurelius", "Seneca", 
                "Kant", "Nietzsche", "Kierkegaard", "Sartre", "Camus", "Epictetus"]

concepts = ["Existentialism", "Stoicism", "Nihilism", "Utilitarianism", 
            "Epistemology", "Determinism", "Free Will", "Phenomenology", 
            "Absurdism", "Moral Relativism"]

conversation_prompts = [
    "I've been feeling like nothing really matters lately.",
    "How do I deal with the anxiety of making the wrong choice?",
    "What is the point of suffering?",
    "Is it better to be happy and ignorant, or miserable and aware?",
    "How can I find meaning in a world that feels so chaotic?",
    "Do you think human nature is inherently good or evil?",
    "I feel overwhelmed by the expectations placed on me.",
]

def generate_stoic_response(prompt):
    return (f"The Stoics, like Marcus Aurelius and Epictetus, would remind us that we cannot control "
            f"the external world, only our reaction to it. When you say, '{prompt}', you are focusing "
            f"on what is outside your sphere of influence. True tranquility comes from accepting the chaos "
            f"and focusing on your own virtue and reason.")

def generate_existential_response(prompt):
    return (f"Jean-Paul Sartre famously said 'existence precedes essence.' You are not born with a predefined "
            f"purpose. The feeling that '{prompt}' is often what Kierkegaard called 'dread' or anxiety—the dizzying "
            f"realization of your own absolute freedom. You are the sole author of your meaning. It is terrifying, "
            f"but fundamentally liberating.")

def generate_socratic_question(prompt):
    return (f"That is a profound perspective. When you consider that '{prompt}', what underlying assumptions "
            f"are you making about the nature of the world? If we strip away the societal definitions of success "
            f"or failure, what core truth remains about your experience?")

def generate_dataset(num_samples=10000):
    dataset = []
    
    # 1. Generate Philosophical Q&A
    for _ in range(num_samples // 2):
        philosopher = random.choice(philosophers)
        concept = random.choice(concepts)
        
        instruction = f"Explain the core tenets of {concept}."
        input_text = f"Relate it to the teachings of {philosopher} if possible."
        output = (f"{concept} is a profound philosophical framework. In the context of {philosopher}, "
                  f"we can understand it by analyzing their fundamental arguments regarding human nature and reality. "
                  f"{philosopher} argued that the highest pursuit is understanding the truth of our condition. "
                  f"By applying {concept} to modern life, we learn to navigate uncertainty with a grounded mind.")
        
        dataset.append({"instruction": instruction, "input": input_text, "output": output})
        
    # 2. Generate Deep Conversational Empathy & Philosophy
    for _ in range(num_samples // 2):
        prompt = random.choice(conversation_prompts)
        response_type = random.choice([generate_stoic_response, generate_existential_response, generate_socratic_question])
        
        instruction = "Engage in a deep, philosophical conversation."
        input_text = prompt
        output = response_type(prompt)
        
        dataset.append({"instruction": instruction, "input": input_text, "output": output})
        
    random.shuffle(dataset)
    return dataset

if __name__ == "__main__":
    print("Generating MNIME V4 Philosophy & Conversation Dataset...")
    v4_data = generate_dataset(15000)
    
    with open("mnime_v4_philosophy_dataset.jsonl", "w", encoding="utf-8") as f:
        for entry in v4_data:
            f.write(json.dumps(entry) + "\n")
            
    print(f"Successfully generated {len(v4_data)} V4 training examples!")

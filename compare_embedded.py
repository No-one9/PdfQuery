from langchain_huggingface import HuggingFaceEmbeddings
from langchain.evaluation import load_evaluator
from dotenv import load_dotenv
import os

load_dotenv()

def main():
    # Initialize Hugging Face embeddings
    embedding_function = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Create evaluator with Hugging Face embeddings
    evaluator = load_evaluator("embedding_distance", embeddings=embedding_function)
    
    words = ("google", "youtube")
    
    # Use 'prediction' and 'reference' parameters
    x = evaluator.evaluate_strings(prediction=words[0], reference=words[1])
    print(f"Comparing ({words[0]}, {words[1]}): {x}")

if __name__ == "__main__":
    main()
#query_data.py
import hashlib
import argparse
import sqlite3
import re
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from huggingface_hub import InferenceClient
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
FAISS_PATH = "faiss_index"
SQLITE_PATH = "metadata.db"
CONFIDENCE_THRESHOLD = 0.3
BANNED_PHRASES = ["we can infer", "it is possible"]

PROMPT_TEMPLATE = """
Follow ALL rules:
1. Answer ONLY the given question using the context. DO NOT generate additional questions.
2. Mention the source filename ONLY ONCE
3. NEVER mention confidence scores
4. Avoid phrases like "no further information"
5. Explain technical terms simply
6. Include book examples if available
7. If unsure, say "The book doesn't explicitly explain this"
8. Say "not discussed" for unknown terms
9. Never guess translations
Context:
{context}

Question: {question}

Answer:
"""

def get_metadata_from_sqlite(doc_id):
    """Retrieve metadata from SQLite database"""
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT source, content FROM documents WHERE id = ?', (doc_id,))
        result = cursor.fetchone()
        return result if result else ("Unknown", None)
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return ("Unknown", None)
    finally:
        conn.close()
def validate_answer(response, context):
    """Prevent hallucinated answers FIRST"""
    # forbidden_phrases = ["translates to", "means in English", "refers to"]
    # if any(phrase in response.lower() for phrase in forbidden_phrases):
    #     return "This information is not explicitly stated in the text."
    return response

def post_process_response(response):
    """Then clean up formatting"""
    # Remove confidence scores
    response = re.sub(r"\bconfidence:? \d+\.\d+\b", "", response, flags=re.IGNORECASE)
    
    # Formatting cleanup
    response = re.sub(r"\bfilenames?\b", "document", response, flags=re.IGNORECASE)
    sentences = re.split(r"(?<=[.!?]) +", response)
    return " ".join(sentences[:3]).strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, help="The query text.")
    args = parser.parse_args()
    query_text = args.query_text

    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        encode_kwargs={"normalize_embeddings": True}
    )

    try:
        # Load FAISS index
        db = FAISS.load_local(
            FAISS_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        print(f"Error loading FAISS index: {e}")
        return

    # Search FAISS with confidence threshold
    results = db.similarity_search_with_relevance_scores(query_text, k=5)
    # filtered = [(doc, abs(score)) for doc, score in results if abs(score) > CONFIDENCE_THRESHOLD]
    filtered= sorted(
        [(doc, abs(score)) for doc, score in results if abs(score) > 0],  # Only positive scores
        key=lambda x: x[1], 
        reverse=True  # Highest scores first
    )[:5]
    # After similarity search
    print(f"\nRaw Scores: {[score for _, score in results]}")
    print(f"Top Chunk: {filtered[0][0].page_content if filtered else 'None'}")
    if not filtered:
        print("I don't have enough information to answer that.")
        return

    # Build context with metadata
    context_parts = []
    for doc, score in filtered:
        doc_id = doc.metadata.get("id", "")
        source, full_content = get_metadata_from_sqlite(doc_id)
        
        if source and full_content:
            context_parts.append(
                f"From {source} (confidence: {score:.2f}):\n{full_content}"
            )

    context_text = "\n\n".join(context_parts)
    print("Retrieved Context:\n", context_text)

    # Generate prompt
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    try:
        # Get LLM response using modern InferenceClient
        client = InferenceClient(model="HuggingFaceH4/zephyr-7b-beta")
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3
        ).choices[0].message.content
        response = validate_answer(response, context_text)
        # Post-processing
        response = post_process_response(response)
        
        # Extract highest confidence for API
        highest_conf = max(score for _, score in filtered) if filtered else 0.0
        print(f"\nAnswer:\n{response}\n\nSource: {source}\nConfidence: {highest_conf:.2f}")
        
    except Exception as e:
        print(f"Error generating answer: {e}")

if __name__ == "__main__":
    main()
import argparse
import sqlite3
import re
import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from huggingface_hub import InferenceClient
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import numpy as np
import uuid
import json
load_dotenv()

# Configuration - MUST match create_database.py settings
FAISS_PATH = "faiss_index"
SQLITE_PATH = "metadata.db"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
MIN_CONFIDENCE = 0.25
def normalize_scores(scores):
    """Convert similarity scores to 0-1 range using sigmoid"""
    return 1 / (1 + np.exp(-np.array(scores)))
PROMPT_TEMPLATE = """
Answer ONLY using this context:
{context}

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

Question: {question}

Answer:
"""
def get_metadata(doc_id):
    """Safe metadata retrieval with error handling"""
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT source, page FROM documents WHERE id = ?',
            (doc_id,)
        )
        result = cursor.fetchone()
        return {
            'source': os.path.basename(result[0]) if result else "Unknown",
            'page': result[1] if result else 0
        }
    except Exception as e:
        print(f"Metadata error: {e}")
        return {'source': 'Unknown', 'page': 0}
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str)
    args = parser.parse_args()
    
    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True}
    )
    
    try:
        db = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"Index load failed: {e}")
        return

    # Search and normalize scores
    raw_results = db.similarity_search_with_score(args.query_text, k=5)
    scores = normalize_scores([r[1] for r in raw_results])
    results = sorted(zip(raw_results, scores), key=lambda x: x[1], reverse=True)
    
    # Process results
    context = []
    # best_source = {'source': 'Unknown', 'page': 0}
    best_source = {
    'source': 'Unknown',
    'page': 0,
    'score': 0.0  # Initialize score field
}
    for (doc, _), score in results:
        if score < MIN_CONFIDENCE:
            continue
        doc_id = doc.metadata.get('id', str(uuid.uuid4()))  # Fallback UUID
        meta = get_metadata(doc_id)
        context.append(f"Page {meta['page']}: {doc.page_content}")
        if score > best_source['score']:
            best_source = {
                'source': meta['source'],
                'page': meta['page'],
                'score': score
            }

    if not context:
        print("No qualified answers found")
        return

    # Generate response
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE).format(
        context="\n".join(context),
        question=args.query_text
    )
    
    try:
        client = InferenceClient(model="mistralai/Mixtral-8x7B-Instruct-v0.1")
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150
        ).choices[0].message.content
        
        # Ensure source formatting
        if not response.endswith(']'):
            response += f" [Source: {best_source['source']}, Page {best_source['page']}]"
            
        # print(f"\n{response}")
        print(json.dumps({
    "answer": response,
    "source": best_source['source'],
    "page": best_source['page'],
    "confidence": float(best_source['score'])
}))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "source": "Unknown",
            "page": 0,
            "confidence": 0.0
        }))

if __name__ == "__main__":
    main()
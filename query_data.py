# # query_data.py
# import argparse
# from langchain_community.vectorstores import FAISS
# from langchain_huggingface import HuggingFaceEmbeddings
# from langchain_huggingface import HuggingFaceEndpoint
# from langchain.prompts import ChatPromptTemplate
# import re
# from dotenv import load_dotenv
# import os

# load_dotenv()

# FAISS_PATH = "faiss_index"
# CONFIDENCE_THRESHOLD=0.4
# BANNED_PHRASES=[
#     "we can infer", "it is possible"
# ]

# # PROMPT_TEMPLATE = """
# # Answer the question concisely using only the provided context. If the answer isn't in the context, say "I don't know."

# # Context:
# # {context}

# # Question: {question}

# # Answer:
# # """
# PROMPT_TEMPLATE = """
# Answer ONLY using the context below. If unsure, say "I don't know".
# 1. If the answer isn't directly in the context, say "I don't know"
# 2. Never mention "context" or "document" in the answer
# 3. Never make assumptions or guesses
# 4. If asked about unknown entities, say "I don't know"

# Context:
# {context}

# Question: {question}

# Strict Rules:
# 1. Never mention "context" in the answer
# 2. Never invent answers
# 3. If unrelated to Alice in Wonderland, say "I don't know"

# Answer:
# """

# def is_irrelevant(response):
#     return any(phrase in response.lower() for phrase in BANNED_PHRASES)

# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("query_text", type=str, help="The query text.")
#     args = parser.parse_args()
#     query_text = args.query_text

#     # Initialize embeddings
#     embeddings = HuggingFaceEmbeddings(
#         model_name="sentence-transformers/all-mpnet-base-v2",
#         encode_kwargs={"normalize_embeddings": True}
#     )
#     test_embedding = embeddings.embed_query("test")
#     print(f"Embedding dimensions: {len(test_embedding)}")
#     # Load FAISS index
#     try:
#         db = FAISS.load_local(
#             FAISS_PATH,
#             embeddings,
#             allow_dangerous_deserialization=True
#         )
#     except Exception as e:
#         print(f"Error loading database: {e}")
#         return

#     # Search with scores
#     results = db.similarity_search_with_relevance_scores(query_text, k=5)
#     filtered=[doc for doc, score in results if score > CONFIDENCE_THRESHOLD]
#     if not filtered:
#         print("Final Answer:\nI don't know.")
#         return

#     print(f"Top {len(results)} results:")
#     for i, (doc, score) in enumerate(zip(filtered,[s for _, s in results])):
#         print(f"\nResult {i+1} (Similarity: {score:.3f}):")
#         print(f"Content: {doc.page_content[:150]}...")
#         print(f"Source: {doc.metadata.get('source', 'unknown')}")

#     # Generate prompt
#     context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
#     prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
#     prompt = prompt_template.format(context=context_text, question=query_text)

#     # Get answer using Hugging Face Endpoint
#     try:
#         llm = HuggingFaceEndpoint(
#             repo_id="HuggingFaceH4/zephyr-7b-beta",
#             task="text-generation",
#             max_new_tokens=100,  # Limit response length
#             temperature=0.2,     # Reduce randomness
#             repetition_penalty=1.2
#         )
#         response = llm.invoke(prompt)
        
#         print("\nFinal Answer:")
#         print(response.strip())
        
#     except Exception as e:
#         print(f"Error generating answer: {e}")

# if __name__ == "__main__":
#     main()


#query_data.py
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
2. Mention the source filename ONLY ONCE
3. NEVER mention confidence scores
4. Avoid phrases like "no further information"

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

def post_process_response(response):
    """Clean up LLM response"""
    # Remove ALL confidence score references
    response = re.sub(
        r"\b(confidence|confidences|confidence scores?)( of|:)? \d+\.\d+(\s?and \d+\.\d+)?\b", 
        "", 
        response, 
        flags=re.IGNORECASE
    )
    
    # Remove banned phrases and redundant filename mentions
    response = re.sub(r"\bfilenames?\b", "file", response, flags=re.IGNORECASE)
    response = response.replace("No further information", "")
    
    # Split sentences properly and truncate
    sentences = re.split(r"(?<=[.!?]) +", response)  # Split on sentence endings
    if len(sentences) > 3:
        sentences = sentences[:3]
        sentences[-1] = re.sub(r"[,.!?]*$", ".", sentences[-1])  # Ensure proper ending
    return " ".join(sentences).strip()

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
    filtered = [(doc, score) for doc, score in results if score > CONFIDENCE_THRESHOLD]
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
        
        # Post-processing
        response = post_process_response(response)
        
        # Extract highest confidence for API
        highest_conf = max(score for _, score in filtered) if filtered else 0.0
        print(f"\nAnswer:\n{response}\n\nSource: {source}\nConfidence: {highest_conf:.2f}")
        
    except Exception as e:
        print(f"Error generating answer: {e}")

if __name__ == "__main__":
    main()
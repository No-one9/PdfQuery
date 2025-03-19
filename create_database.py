from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings  # Updated import
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFDirectoryLoader
import sqlite3
import os

# Initialize SQLite connection
conn = sqlite3.connect('metadata.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        source TEXT,
        content TEXT
    )
''')
conn.commit()

# Load and split documents
loader = DirectoryLoader("data/", glob="*.md")
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=150,
    separators=["\n\n", "\n", " ", ""],   # Fixed typo (was chunk_overelap)
    length_function=len,
    add_start_index=True
)
chunks = text_splitter.split_documents(documents)

# Store in FAISS and SQLite
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    encode_kwargs={"normalize_embeddings": True}  # Fixed case (V2 → v2)
)

# Add IDs to metadata before saving
for idx, chunk in enumerate(chunks):
    chunk.metadata["id"] = str(idx)  # Critical for SQLite lookup

vector_store = FAISS.from_documents(chunks, embeddings)
vector_store.save_local("faiss_index")  # Fixed typo (fiass_index → faiss_index)

# Insert metadata into SQLite
for idx, chunk in enumerate(chunks):
    cursor.execute('''
        INSERT OR REPLACE INTO documents (id, source, content)
        VALUES (?, ?, ?)
    ''', (
        str(idx),
        chunk.metadata.get("source", ""),
        chunk.page_content
    ))

conn.commit()
conn.close()
print(f"Stored {len(chunks)} documents")  # Proper capitalization


# model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# load_dotenv()
# FAISS_PATH = "faiss_index"
# DATA_PATH = "data/"

# def load_documents():
#     """Load documents from the specified directory."""
#     loader = DirectoryLoader(DATA_PATH, glob="*.md")
#     documents = loader.load()
#     return documents

# def split_text(documents: list[Document]):
#     """Split documents into smaller chunks."""
#     text_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=300,
#         chunk_overlap=100,
#         length_function=len,  # Fixed typo
#         add_start_index=True,
#     )
#     chunks = text_splitter.split_documents(documents)
#     # print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    
#     # # Print an example chunk for debugging
#     # if chunks:
#     #     document = chunks[0]  # Print the first chunk instead of 10 (to avoid index error)
#     #     print(document.page_content)
#     #     print(document.metadata)
    
#     return chunks

# def save_to_faiss(chunks):
#     """Save document chunks to Chroma database."""
#     # Clear out the database first.
#     if os.path.exists(FAISS_PATH):
#         shutil.rmtree(FAISS_PATH)

#     # Create a new DB from the documents.
#     db = FAISS.from_documents(
#         chunks, HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
#     )
#     db.save_local(FAISS_PATH)
#     print(f"Saved {len(chunks)} chunks to {FAISS_PATH}.")

# def generate_data_store():
#     """Load, split, and store documents."""
#     documents = load_documents()
#     chunks = split_text(documents)  # Fixed function call
#     save_to_faiss(chunks)
# if __name__=="__main__":
    
#     generate_data_store()
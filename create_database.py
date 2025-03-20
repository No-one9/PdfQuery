import re
import sqlite3
import os
import pdfplumber
from collections import defaultdict
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def clean_pdf_text(text):
    """Clean PDF text from excessive whitespace and artifacts"""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between camelCase
    text = re.sub(r'\b([A-Z]+)(\d+)\b', r'\1 \2', text)  # Separate "EC2" -> "EC 2"
    return re.sub(r'\s+', ' ', text).strip()

# Initialize SQLite connection with enhanced schema
conn = sqlite3.connect('metadata.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        source TEXT,
        content TEXT,
        author TEXT,
        pdf_title TEXT,
        page INTEGER
    )
''')
conn.commit()

# Load and process PDFs
loader = PyPDFDirectoryLoader(
    "data/", 
    glob="*.pdf",
    recursive=True
)
documents = loader.load()

# Group documents by source PDF and extract metadata
doc_groups = defaultdict(list)
for doc in documents:
    doc_groups[doc.metadata['source']].append(doc)

# Process each PDF file's documents
for source_path, docs in doc_groups.items():
    try:
        with pdfplumber.open(source_path) as pdf:
            # Extract PDF-level metadata
            pdf_metadata = pdf.metadata
            author = pdf_metadata.get('Author', 'Unknown')
            title = pdf_metadata.get('Title', os.path.basename(source_path))
            
        # Update all documents from this PDF
        for doc in docs:
            doc.metadata.update({
                'author': author,
                'pdf_title': title,
                'page': doc.metadata.get('page', 0)
            })
    except Exception as e:
        print(f"Error processing {source_path}: {str(e)}")
        continue

# Split documents with PDF-optimized settings
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=150,
    separators=["\n\n## ", 
                "\n\n", 
                "\n", ". ", "!", "?"],

    length_function=len,
    add_start_index=True
)
chunks = text_splitter.split_documents(documents)

# Process chunks
for idx, chunk in enumerate(chunks):
    chunk.metadata["id"] = str(idx)
    chunk.page_content = clean_pdf_text(chunk.page_content)

# Store in FAISS
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    encode_kwargs={"normalize_embeddings": True}
)
vector_store = FAISS.from_documents(chunks, embeddings)
vector_store.save_local("faiss_index")

# Insert into SQLite with enhanced metadata
for idx, chunk in enumerate(chunks):
    cursor.execute('''
        INSERT OR REPLACE INTO documents 
        (id, source, content, author, pdf_title, page)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        str(idx),
        chunk.metadata.get("source", ""),
        chunk.page_content,
        chunk.metadata.get("author", ""),
        chunk.metadata.get("pdf_title", ""),
        chunk.metadata.get("page", 0)
    ))

conn.commit()
conn.close()
print(f"Successfully stored {len(chunks)} document chunks")
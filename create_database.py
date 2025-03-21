import re
import sqlite3
import pdfplumber
import uuid
from pathlib import Path
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

def clean_pdf_text(text):
    """Clean PDF text from excessive whitespace and artifacts"""
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'\b([A-Z]+)(\d+)\b', r'\1 \2', text)
    return re.sub(r'\s+', ' ', text).strip()

def process_pdf(pdf_path):
    """Process a PDF file with multiple fallback strategies"""
    try:
        # First try with pdfplumber for better text extraction
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages)
            metadata = pdf.metadata
            
        return {
            "text": text,
            "metadata": {
                "author": metadata.get("Author", "Unknown"),
                "title": metadata.get("Title", pdf_path.name),
                "source": str(pdf_path)
            }
        }
    except Exception as e:
        print(f"pdfplumber failed for {pdf_path.name}, trying pypdf: {str(e)}")
        try:
            # Fallback to pypdf
            with open(pdf_path, "rb") as f:
                reader = PdfReader(f)
                text = "\n".join(page.extract_text() for page in reader.pages)
                
            return {
                "text": text,
                "metadata": {
                    "author": reader.metadata.get("/Author", "Unknown"),
                    "title": reader.metadata.get("/Title", pdf_path.name),
                    "source": str(pdf_path)
                }
            }
        except Exception as e:
            print(f"All parsers failed for {pdf_path.name}: {str(e)}")
            return None

# Initialize database
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

# Process PDFs
documents = []
pdf_files = list(Path("Data/").glob("**/*.pdf"))

for pdf_path in pdf_files:
    result = process_pdf(pdf_path)
    if result and result["text"].strip():
        # Create LangChain documents with page-wise content
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                documents.append(Document(
                    page_content=clean_pdf_text(page_text),
                    metadata={
                        **result["metadata"],
                        "page": page_num + 1
                    }
                ))

if not documents:
    print("No valid documents processed. Exiting.")
    conn.close()
    exit()

# Split documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=150,
    separators=["\n\n## ", "\n\n", "\n", ". ", "! ", "? "],
    length_function=len
)
chunks = text_splitter.split_documents(documents)

# Add UUIDs and validate metadata
for chunk in chunks:
    # Generate unique ID for each chunk
    chunk.metadata["id"] = str(uuid.uuid4())
    
    # Ensure all required metadata fields exist
    chunk.metadata.setdefault('source', 'Unknown')
    chunk.metadata.setdefault('author', 'Unknown')
    chunk.metadata.setdefault('title', Path(chunk.metadata['source']).name)
    chunk.metadata.setdefault('page', 0)

# Create vector store
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2",
    encode_kwargs={"normalize_embeddings": True}
)
FAISS.from_documents(chunks, embeddings).save_local("faiss_index")

# Store in SQLite
for chunk in chunks:
    cursor.execute('''
        INSERT OR REPLACE INTO documents 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        chunk.metadata["id"],
        chunk.metadata["source"],
        chunk.page_content,
        chunk.metadata["author"],
        chunk.metadata["title"],
        chunk.metadata["page"]
    ))

conn.commit()
conn.close()
print(f"Processed {len(chunks)} chunks from {len(documents)} pages")
# PdfQuery

A powerful application that combines document processing, semantic search, and question answering capabilities. This application uses FAISS for efficient similarity search and Hugging Face models for text embeddings and generation.

## Features

- PDF document processing and text extraction
- Semantic search using FAISS indexing
- RESTful API endpoints for querying
- Web interface for easy interaction
- Docker support for containerized deployment
- Efficient document chunking and embedding

## Tech Stack

### Backend
- Python 3.x
- Flask (Web Framework)
- FAISS (Vector Similarity Search)
- LangChain (Document Processing)
- Hugging Face Transformers
- Sentence Transformers

### Frontend
- Node.js
- Express.js
- Material Design Components
- Axios for API calls

## Prerequisites

- Python 3.x
- Node.js and npm
- Docker (optional)

## Usage

1. Start the Python backend server:
```bash
python api.py
```

2. Start the Node.js server:
```bash
node server.js
```

3. Access the web interface at `http://localhost:3000`

## API Endpoints

### Query Endpoint
- **URL**: `/query`
- **Method**: `POST`
- **Body**:
```json
{
    "query": "Your question here"
}
```

## Project Structure

```
rag-application/
├── api.py                 # Flask API server
├── create_database.py     # Database creation and indexing
├── query_data.py         # Query processing logic
├── pdf_util.py           # PDF processing utilities
├── server.js             # Node.js server
├── public/               # Frontend static files
├── faiss_index/          # FAISS index storage
├── Data/                 # Document storage
└── requirements.txt      # Python dependencies
```

## Docker Support

Build and run using Docker:
```bash
docker build -t rag-application .
docker run -p 8000:8000 rag-application
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the ISC License.

## Acknowledgments

- Hugging Face for their transformer models
- FAISS for efficient similarity search
- LangChain for document processing capabilities

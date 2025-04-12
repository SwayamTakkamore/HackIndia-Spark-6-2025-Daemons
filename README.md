# QueryNest

QueryNest is an intelligent document analysis system that allows users to upload, analyze, and interact with complex documents using natural language queries. Built as part of HackIndia 2025, QueryNest leverages AI to extract meaningful insights from documents quickly and efficiently.

## Features

- **Document Management**: Upload, store, and manage multiple documents
- **Intelligent Sectioning**: Automatically detects and separates document sections
- **Natural Language Queries**: Ask questions about document content in plain English
- **Section-Targeted Queries**: Direct questions to specific sections or problem statements
- **Smart Summarization**: Generate concise summaries of entire documents or specific sections
- **Validation System**: Ensures summaries and answers are factually consistent with source documents

## Technology Stack

- **Backend**: FastAPI (Python)
- **NLP Processing**:
  - Sentence Transformers for semantic embeddings
  - Hugging Face Transformers for question answering and summarization
  - PyMuPDF (fitz) for document text extraction
- **Data Storage**: JSON-based document store

## Architecture

QueryNest processes documents in several stages:
1. Text extraction from uploaded files (PDF support)
2. Section detection and structuring
3. Text chunking and embedding generation
4. Storage of processed documents for rapid querying

Queries are processed by:
1. Finding relevant document sections
2. Identifying the most semantically similar chunks
3. Generating accurate answers using transformer models
4. Validating the answers against the source document

## API Endpoints

- `POST /upload`: Upload a new document
- `GET /documents`: List all documents
- `POST /documents/{doc_id}/activate`: Set active document
- `DELETE /documents/{doc_id}`: Remove a document
- `POST /query`: Query document content
- `GET /summary`: Get document summary
- `POST /query_summary`: Get contextual summary based on query
- `GET /summary/section`: Get section-specific summary

## Setup and Installation

### Prerequisites
- Python 3.9+
- Virtual environment (optional but recommended)

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/QueryNest.git
cd QueryNest

# Create and activate virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
cd backend
uvicorn main:app --reload
```

## Use Cases

- **Academic Research**: Quickly extract relevant information from research papers
- **Legal Document Analysis**: Navigate complex legal documents with ease
- **Technical Documentation**: Find specific information in lengthy technical manuals
- **Competitive Analysis**: Extract key points from market reports and competitor documents

## Team

Developed by Team Daemons for HackIndia 2025.

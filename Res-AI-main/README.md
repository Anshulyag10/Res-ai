# ResAI(AI-Research-Copilot)

GPU-accelerated research paper analysis with AI-powered summarization, translation, and intelligent Q&A using RAG.

## Features

- Document Summarization with BART-Large-CNN
- Q&A System with Flan-T5-Large and RAG
- Translation to 11+ languages (Helsinki-NLP models)
- GPU acceleration with CUDA
- Vector search with FAISS
- Instant processing on upload

## Tech Stack

**Backend:** FastAPI, PyTorch, Transformers, LangChain, FAISS  
**Frontend:** React, Vite, TailwindCSS, Axios

## Installation

### Backend Setup
```powershell
cd AI-Research-Copilot-Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# For NVIDIA GPU (CUDA 12.4)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### Frontend Setup
```powershell
cd AI-Research-Copilot-Frontend
npm install
```

Models download automatically on first use.

## Running

### Start Backend
```powershell
cd AI-Research-Copilot-Backend
.venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start Frontend
```powershell
cd AI-Research-Copilot-Frontend
npm run dev
```

Access at `http://localhost:5173`

## API Endpoints

### Documents
- `POST /api/upload` - Upload PDF
- `GET /api/files` - List documents
- `DELETE /api/delete/{doc_id}` - Delete document

### AI Features
- `GET /api/analyze/{doc_id}` - Get summary
- `POST /api/translate/{doc_id}` - Translate (body: `{"target_lang": "es"}`)
- `POST /api/qa/{doc_id}` - Ask question (body: `{"question": "..."}`)

## Usage

1. Start backend and frontend servers
2. Upload PDF at `http://localhost:5173`
3. Wait for automatic processing
4. View summary and translations
5. Ask questions about the document

## Requirements

- Python 3.9+, Node.js 16+
- 8GB RAM minimum (16GB recommended)
- NVIDIA GPU recommended (6GB+ VRAM)
- 5GB storage for models

## Models Used

- Summarization: facebook/bart-large-cnn (1.6GB)
- Q&A: google/flan-t5-large (1GB)
- Embeddings: sentence-transformers/all-MiniLM-L6-v2
- Translation: Helsinki-NLP/opus-mt-* (300MB each)

## Limitations

- 10MB PDF file size limit
- Documents stored in memory only
- Single document processing at a time
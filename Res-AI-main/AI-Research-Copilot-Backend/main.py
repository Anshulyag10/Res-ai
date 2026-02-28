import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
import json

from translationModel import translate_text_core
from summaryModel import summarize_text_optimized
from qaModel import create_faiss_index, initialize_qa_system, load_pdf_text

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "files"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

document_store = {}

class QARequest(BaseModel):
    question: str

class TranslationRequest(BaseModel):
    target_lang: str

class ProgressCallback:
    def __init__(self, callback):
        self.callback = callback
    
    def log(self, message):
        self.callback(message)
        print(message, flush=True)

@app.post("/api/upload")
async def upload_file(file: UploadFile):
    try:
        allowed_types = ["application/pdf", "text/plain"]
        if file.content_type not in allowed_types:
            return JSONResponse(
                {"detail": "only pdf/text files allowed"},
                status_code=400
            )

        file_uuid = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        stored_filename = f"{file_uuid}{file_ext}"
        file_path = UPLOAD_DIR / stored_filename

        content = await file.read()

        if len(content) > 10 * 1024 * 1024:
            return JSONResponse(
                {"detail": "file size exceeds 10mb limit"},
                status_code=400
            )

        print(f"[1/4] Saving file: {file.filename}", flush=True)
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        print("[2/4] Extracting text from PDF...", flush=True)
        text = load_pdf_text(str(file_path))
        if not text.strip():
            raise ValueError("failed to extract text from pdf")
        print(f"[2/4] Extracted {len(text)} characters", flush=True)
        
        print("[3/4] Generating AI summary (may take 2-4 minutes)...", flush=True)
        summary = summarize_text_optimized(text)
        print("[3/4] Summary generated successfully", flush=True)
        
        print("[4/4] Creating Q&A search index...", flush=True)
        faiss_index = create_faiss_index(text)
        print("[4/4] FAISS index created successfully", flush=True)

        document_store[file_uuid] = {
            "text": text,
            "filename": file.filename,
            "summary": summary,
            "faiss_index": faiss_index,
            "translations": {},
            "created_at": datetime.now().isoformat()
        }

        print(f"Processing complete for: {file.filename}", flush=True)
        return JSONResponse({
            "doc_id": file_uuid,
            "filename": file.filename
        })

    except Exception as e:
        print(f"Error processing file: {str(e)}", flush=True)
        return JSONResponse(
            {"detail": f"upload failed: {str(e)}"},
            status_code=500
        )

# Get file metadata
@app.get("/api/file-info/{doc_id}")
def get_file_info(doc_id: str):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")

    return JSONResponse({
        "doc_id": doc_id,
        "filename": doc["filename"],
        "upload_date": doc["created_at"]
    })

# Get summary
@app.get("/api/analyze/{doc_id}")
def get_summary(doc_id: str):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")

    try:
        return JSONResponse({
            "status": "completed",
            "summary": doc["summary"]
        })
    except Exception as e:
        raise HTTPException(500, f"summarization failed: {str(e)}")

# Translate summary
@app.post("/api/translate/{doc_id}")
def get_translation(doc_id: str, request: TranslationRequest = Body(...)):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")

    try:
        translation_key = f"summary_{request.target_lang}"
        if translation_key not in doc["translations"]:
            try:
                translated_summary = translate_text_core(
                    doc["summary"],
                    request.target_lang
                )
                doc["translations"][translation_key] = translated_summary
            except ValueError as e:
                raise HTTPException(400, detail=f"invalid language: {str(e)}")
            except RuntimeError as e:
                raise HTTPException(500, detail=f"translation service error: {str(e)}")
            except Exception as e:
                raise HTTPException(500, detail=f"translation error: {str(e)}")

        return JSONResponse({
            "translated_summary": doc["translations"][translation_key]
        })
    except Exception as e:
        raise HTTPException(500, f"translation failed: {str(e)}")

# Answer questions
@app.post("/api/qa/{doc_id}")
def answer_question(doc_id: str, request: QARequest = Body(...)):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")

    try:
        qa = initialize_qa_system(doc["faiss_index"])

        with torch.inference_mode():
            result = qa.invoke({"query": request.question})
            torch.cuda.empty_cache()

        return JSONResponse({
            "question": request.question,
            "answer": result["result"],
            "sources": [d.page_content[:200] + "..." for d in result["source_documents"]]
        })
    except Exception as e:
        raise HTTPException(500, f"qa failed: {str(e)}")

# Delete document
@app.delete("/api/delete/{doc_id}")
def delete_document(doc_id: str):
    doc = document_store.get(doc_id)
    if not doc:
        raise HTTPException(404, "document not found")

    try:
        for file_path in UPLOAD_DIR.glob(f"{doc_id}.*"):
            if file_path.exists():
                file_path.unlink()
                print(f"deleted file: {file_path}")

        del document_store[doc_id]
        
        return JSONResponse({
            "message": "document deleted successfully",
            "doc_id": doc_id,
            "filename": doc["filename"]
        })
    except Exception as e:
        raise HTTPException(500, f"deletion failed: {str(e)}")

# List all files
@app.get("/api/files")
def list_all_files():
    files_list = []
    for doc_id, doc_data in document_store.items():
        files_list.append({
            "doc_id": doc_id,
            "filename": doc_data["filename"],
            "upload_date": doc_data["created_at"]
        })
    
    return JSONResponse({
        "files": files_list,
        "count": len(files_list)
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
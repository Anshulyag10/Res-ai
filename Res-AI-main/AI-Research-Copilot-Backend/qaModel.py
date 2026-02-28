import fitz
import os
import torch
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFacePipeline
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_core.prompts import PromptTemplate
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
DTYPE = torch.float16 if DEVICE == 'cuda' else torch.float32


def load_pdf_text(file_path):
    with fitz.open(file_path) as doc:
        text = "\n".join(page.get_text() for page in doc)
        if not text.strip():
            raise ValueError("PDF contains no readable content")
        return text


def create_faiss_index(text, logger=None):
    print("  Initializing text splitter...", flush=True)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    docs = splitter.create_documents([text])
    print(f"  Created {len(docs)} document chunks", flush=True)

    print("  Loading MiniLM embedding model...", flush=True)
    faiss_db = FAISS.from_documents(
        documents=docs,
        embedding=HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": DEVICE}
        )
    )
    print("  FAISS vector database created successfully", flush=True)
    
    return faiss_db


def initialize_qa_system(db):
    print("Loading Flan-T5 model for Q&A...", flush=True)
    
    tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large")
    model = AutoModelForSeq2SeqLM.from_pretrained(
        "google/flan-t5-large",
        torch_dtype=DTYPE
    ).to(DEVICE)
    
    pipe = pipeline(
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=256,
        do_sample=True,
        temperature=0.3,
        top_p=0.95,
        device=0 if DEVICE == 'cuda' else -1
    )
    
    llm = HuggingFacePipeline(pipeline=pipe)
    
    prompt_template = """Answer the question based on the context below. Give a clear, concise answer.

Context: {context}

Question: {question}

Answer in complete sentences:"""
    
    PROMPT = PromptTemplate(
        template=prompt_template, 
        input_variables=["context", "question"]
    )

    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=db.as_retriever(search_kwargs={
            "k": 3,
            "fetch_k": 5
        }),
        chain_type="stuff",
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    
    print("Q&A system ready (Flan-T5 Large)", flush=True)
    return qa



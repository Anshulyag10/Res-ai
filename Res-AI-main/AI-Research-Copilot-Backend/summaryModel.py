from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import os
import fitz
import re
from functools import lru_cache

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
DTYPE = torch.float16 if DEVICE == 'cuda' else torch.float32
BATCH_SIZE = 2
MODEL_NAME = "facebook/bart-large-cnn"
MAX_INPUT_LENGTH = 1024

# Print GPU status on module load
if DEVICE == 'cuda':
    print(f"GPU Mode: Using {torch.cuda.get_device_name(0)}", flush=True)
else:
    print("CPU Mode: GPU not available", flush=True)


@lru_cache(maxsize=1)
def load_resources():
    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_NAME,
        dtype=DTYPE
    ).to(DEVICE)
    if DEVICE == 'cuda':
        print(f"Model loaded on {torch.cuda.get_device_name(0)}", flush=True)
    return tokenizer, model


def clean_text(text):
    # Remove unwanted text patterns
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'Figure \d+[.:]\s*', '', text)
    text = re.sub(r'Table \d+[.:]\s*', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\(\w+\s+et\s+al\.,?\s+\d{4}\)', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'doi:\S+', '', text)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()


def chunk_text(text, tokenizer, chunk_size=900):
    # Split text into manageable chunks
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[.?!])\s+', text)
    chunks = []
    current_chunk = []

    for sentence in sentences:
        test_chunk = ' '.join(current_chunk + [sentence])
        if len(tokenizer.tokenize(test_chunk)) > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
        else:
            current_chunk.append(sentence)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return [chunk for chunk in chunks if len(chunk.strip()) > 50]


def summarize_text_optimized(text, logger=None):
    print("  Loading BART model...", flush=True)
    tokenizer, model = load_resources()
    print("  Model loaded successfully", flush=True)

    print("  Cleaning and chunking text...", flush=True)
    cleaned_text = clean_text(text)
    chunks = chunk_text(cleaned_text, tokenizer)
    print(f"  Split into {len(chunks)} chunks", flush=True)

    summaries = []
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_idx, i in enumerate(range(0, len(chunks), BATCH_SIZE), 1):
        batch = chunks[i:i + BATCH_SIZE]
        print(f"  Processing batch {batch_idx}/{total_batches}...", flush=True)
        
        prompted_batch = [f"Summarize this research paper section: {chunk}" for chunk in batch]
        
        inputs = tokenizer(
            prompted_batch,
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
            padding='longest',
            return_tensors="pt"
        ).to(DEVICE)
        
        summary_ids = model.generate(
            **inputs,
            num_beams=4,
            repetition_penalty=2.5,
            length_penalty=1.0,
            early_stopping=True,
            max_length=250,
            min_length=80,
            no_repeat_ngram_size=3,
            do_sample=False,
            temperature=1.0
        )

        summaries.extend(tokenizer.batch_decode(summary_ids, skip_special_tokens=True))

    combined_summary = ' '.join(summaries)
    
    if len(tokenizer.tokenize(combined_summary)) > 400:
        print("  Creating final comprehensive summary...", flush=True)
        final_prompt = f"Create a comprehensive summary of this research paper: {combined_summary}"
        final_inputs = tokenizer(
            final_prompt,
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
            return_tensors="pt"
        ).to(DEVICE)
        
        final_summary_ids = model.generate(
            **final_inputs,
            num_beams=4,
            repetition_penalty=2.5,
            length_penalty=1.0,
            early_stopping=True,
            max_length=200,
            min_length=60,
            no_repeat_ngram_size=3,
            do_sample=False
        )
        
        combined_summary = tokenizer.decode(final_summary_ids[0], skip_special_tokens=True)

    print("  Summary generation complete", flush=True)
    return combined_summary


def summarize_document(input_path):
    # Process PDF and return summary
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    print(f"Processing research paper: {os.path.basename(input_path)}", flush=True)

    with fitz.open(input_path) as doc:
        text = []
        for page in doc:
            text.append(page.get_text("text", flags=fitz.TEXT_PRESERVE_IMAGES))
        full_text = '\n'.join(text)

    if not full_text.strip():
        raise ValueError("Document contains no readable text")

    return summarize_text_optimized(full_text)


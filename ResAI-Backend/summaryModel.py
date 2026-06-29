from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
import re
from functools import lru_cache
from logger import get_logger

logger = get_logger(__name__)

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
DTYPE = torch.float16 if DEVICE == 'cuda' else torch.float32
BATCH_SIZE = 2
MODEL_NAME = "facebook/bart-large-cnn"
MAX_INPUT_LENGTH = 1024

if DEVICE == 'cuda':
    logger.info(f"Summary model — GPU: {torch.cuda.get_device_name(0)}")
else:
    logger.info("Summary model — CPU mode (GPU not available)")


@lru_cache(maxsize=1)
def load_resources():
    """Load and cache BART tokenizer and model. Called once per process lifetime."""
    logger.info(f"Loading BART model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME, dtype=DTYPE).to(DEVICE)
    logger.info("BART model loaded successfully")
    return tokenizer, model


def clean_text(text: str) -> str:
    """Remove noise patterns common in academic PDFs."""
    text = re.sub(r'Page \d+ of \d+', '', text)
    text = re.sub(r'Figure \d+[.:]\s*', '', text)
    text = re.sub(r'Table \d+[.:]\s*', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\(\w+\s+et\s+al\.?,?\s+\d{4}\)', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'doi:\S+', '', text)
    text = re.sub(r'\S+@\S+\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    return text.strip()


def chunk_text(text: str, tokenizer, chunk_size: int = 900) -> list[str]:
    """Split text into tokenizer-aware chunks that fit within model input limits."""
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[.?!])\s+', text)
    chunks, current_chunk = [], []

    for sentence in sentences:
        test_chunk = ' '.join(current_chunk + [sentence])
        if len(tokenizer.tokenize(test_chunk)) > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
        else:
            current_chunk.append(sentence)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return [c for c in chunks if len(c.strip()) > 50]


def summarize_text_optimized(text: str) -> str:
    """
    Summarize a research paper using BART-large-CNN.
    Handles long documents by chunking and hierarchical summarization.
    """
    logger.info("Loading BART model for summarization...")
    tokenizer, model = load_resources()

    logger.info("Cleaning and chunking text...")
    cleaned = clean_text(text)
    chunks = chunk_text(cleaned, tokenizer)
    logger.info(f"Processing {len(chunks)} chunks in batches of {BATCH_SIZE}")

    summaries = []
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx, i in enumerate(range(0, len(chunks), BATCH_SIZE), 1):
        batch = chunks[i:i + BATCH_SIZE]
        logger.info(f"Summarizing batch {batch_idx}/{total_batches}")

        prompted = [f"Summarize this research paper section: {c}" for c in batch]
        inputs = tokenizer(
            prompted,
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
            padding='longest',
            return_tensors="pt"
        ).to(DEVICE)

        with torch.inference_mode():
            ids = model.generate(
                **inputs,
                num_beams=4,
                repetition_penalty=2.5,
                length_penalty=1.0,
                early_stopping=True,
                max_length=250,
                min_length=80,
                no_repeat_ngram_size=3,
                do_sample=False,
            )
        summaries.extend(tokenizer.batch_decode(ids, skip_special_tokens=True))

    combined = ' '.join(summaries)

    if len(tokenizer.tokenize(combined)) > 400:
        logger.info("Creating final hierarchical summary...")
        final_prompt = f"Create a comprehensive summary of this research paper: {combined}"
        inputs = tokenizer(
            final_prompt,
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
            return_tensors="pt"
        ).to(DEVICE)

        with torch.inference_mode():
            ids = model.generate(
                **inputs,
                num_beams=4,
                repetition_penalty=2.5,
                length_penalty=1.0,
                early_stopping=True,
                max_length=200,
                min_length=60,
                no_repeat_ngram_size=3,
                do_sample=False,
            )
        combined = tokenizer.decode(ids[0], skip_special_tokens=True)

    logger.info("Summary generation complete")
    return combined

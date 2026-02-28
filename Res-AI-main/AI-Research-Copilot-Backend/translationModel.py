from transformers import MarianMTModel, MarianTokenizer
import torch
import logging
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
DTYPE = torch.float16 if DEVICE == 'cuda' else torch.float32
BATCH_SIZE = 4
MAX_LENGTH = 512

# Valid language mappings
LANGUAGE_MODEL_MAP = {
    "de": "de",
    "es": "es",
    "fr": "fr",
    "ru": "ru",
    "ja": "ja",
}

@lru_cache(maxsize=5)
def load_resources(target_lang: str):
    # Load translation model for target language
    normalized_lang = target_lang.lower()

    if normalized_lang not in LANGUAGE_MODEL_MAP:
        raise ValueError(f"Unsupported language: {target_lang}. Supported languages: {list(LANGUAGE_MODEL_MAP.keys())}")

    model_suffix = LANGUAGE_MODEL_MAP[normalized_lang]
    model_name = f"Helsinki-NLP/opus-mt-en-{model_suffix}"

    logger.info(f"Loading translation model: {model_name}")

    try:
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(
            model_name,
            dtype=DTYPE
        ).to(DEVICE).eval()
        logger.info(f"Successfully loaded model: {model_name}")
        return tokenizer, model
    except Exception as e:
        logger.error(f"Model loading failed: {str(e)}")
        raise RuntimeError(f"Failed to load translation model for {target_lang}. Error: {str(e)}")

def translate_text_core(text, target_lang):
    # Translate text to specified language
    print(f"Translating to {target_lang}...")  
    
    try:
        tokenizer, model = load_resources(target_lang)
    except Exception as e:
        logger.error(f"Failed to load translation resources: {str(e)}")
        raise RuntimeError(f"Translation service unavailable for {target_lang}. Please try again later.")

    try:
        text = text.strip()
        if len(text) < 500:
            inputs = tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH
            ).to(DEVICE)

            outputs = model.generate(
                **inputs,
                num_beams=4,
                early_stopping=True,
                max_length=MAX_LENGTH,
                length_penalty=1.0,
                repetition_penalty=1.2,
                do_sample=False
            )

            return tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        else:
            sentences = [s.strip() + '.' for s in text.split('. ') if s.strip()]

            translated = []
            for i in range(0, len(sentences), BATCH_SIZE):
                batch = sentences[i:i + BATCH_SIZE]

                inputs = tokenizer(
                    batch,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=MAX_LENGTH
                ).to(DEVICE)

                outputs = model.generate(
                    **inputs,
                    num_beams=3,
                    early_stopping=True,
                    max_length=MAX_LENGTH,
                    length_penalty=1.0,
                    repetition_penalty=1.2
                )

                translated_batch = tokenizer.batch_decode(
                    outputs,
                    skip_special_tokens=True
                )
                translated.extend(translated_batch)

            return ' '.join(translated)

    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        raise RuntimeError(f"Translation failed: {str(e)}")

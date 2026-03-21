"""Generate ESM-2 embeddings for AMP sequences."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModel, AutoTokenizer

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "01_data" / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_NAME = "facebook/esm2_t36_3B_UR50D"
EMBEDDING_DIM = 2560
BATCH_SIZE = 8
CACHE_FILE = "embeddings_cache.npz"


def load_sequences(path: Path | None = None) -> pd.DataFrame:
    """Load unified AMP dataset."""
    p = path or DATA_DIR / "amps_unified.csv"
    return pd.read_csv(p)


def detect_device() -> str:
    """Return 'cuda' if available, else 'cpu'."""
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_esm2_model(model_name: str = MODEL_NAME) -> tuple:
    """Load ESM-2 tokenizer and model (fp16 on GPU)."""
    device = detect_device()
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = AutoModel.from_pretrained(model_name, dtype=dtype)
    model.eval()
    model.to(device)
    return tokenizer, model


def embed_batch(
    sequences: list[str],
    tokenizer,
    model,
    device: str = "cpu",
) -> np.ndarray:
    """Embed a batch of sequences using ESM-2 mean pooling."""
    # ESM-2 expects space-separated amino acids
    spaced = [" ".join(seq) for seq in sequences]
    inputs = tokenizer(spaced, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad(), torch.amp.autocast(device_type=device, enabled=(device == "cuda")):
        outputs = model(**inputs)

    # Mean pool over residue positions (exclude special tokens via attention_mask)
    hidden = outputs.last_hidden_state.float()
    mask = inputs["attention_mask"].unsqueeze(-1).float()
    embeddings = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
    return embeddings.cpu().numpy()


def generate_embeddings(
    sequences: list[str],
    tokenizer=None,
    model=None,
    batch_size: int = BATCH_SIZE,
    device: str | None = None,
) -> np.ndarray:
    """Generate embeddings for all sequences in batches."""
    if tokenizer is None or model is None:
        tokenizer, model = get_esm2_model()
    if device is None:
        device = detect_device()
    model = model.to(device)

    all_embeddings = []
    for i in range(0, len(sequences), batch_size):
        batch = sequences[i : i + batch_size]
        embs = embed_batch(batch, tokenizer, model, device)
        all_embeddings.append(embs)

    return np.vstack(all_embeddings)


def save_cache(
    ids: list[str],
    sequences: list[str],
    embeddings: np.ndarray,
    output_path: Path | None = None,
) -> Path:
    """Save embeddings cache as .npz file."""
    out = output_path or MODELS_DIR / CACHE_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, ids=np.array(ids), sequences=np.array(sequences), embeddings=embeddings)
    return out


def load_cache(path: Path | None = None) -> dict[str, np.ndarray]:
    """Load cached embeddings."""
    p = path or MODELS_DIR / CACHE_FILE
    data = np.load(p, allow_pickle=True)
    return {"ids": data["ids"], "sequences": data["sequences"], "embeddings": data["embeddings"]}


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    device = detect_device()
    print(f"Device: {device} | Model: {MODEL_NAME}")

    df = load_sequences()
    sequences = df["sequence"].tolist()
    ids = df["id"].tolist()

    print(f"Generating ESM-2 embeddings for {len(sequences)} sequences...")
    tokenizer, model = get_esm2_model()
    embeddings = generate_embeddings(sequences, tokenizer, model, device=device)
    print(f"  Embedding shape: {embeddings.shape}")

    out = save_cache(ids, sequences, embeddings)
    print(f"  Saved to {out}")


if __name__ == "__main__":
    main()

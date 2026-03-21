"""Clean, deduplicate, and standardize AMP sequences into unified format."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

VALID_AAS = set("ACDEFGHIKLMNPQRSTVWY")
MIN_LENGTH = 5
MAX_LENGTH = 100


def load_raw_amps(path: Path | None = None) -> pd.DataFrame:
    """Load raw AMPs CSV."""
    p = path or PROCESSED_DIR / "amps_raw.csv"
    df = pd.read_csv(p)
    # Parse target_organisms back to list
    if "target_organisms" in df.columns:
        df["target_organisms"] = df["target_organisms"].apply(
            lambda x: str(x).split(";") if pd.notna(x) else []
        )
    return df


def clean_sequence(seq: str) -> str | None:
    """Standardize and validate a peptide sequence. Returns None if invalid."""
    seq = re.sub(r"\s+", "", str(seq)).upper()
    seq = re.sub(r"[^A-Z]", "", seq)
    if not seq:
        return None
    if not all(c in VALID_AAS for c in seq):
        return None
    if len(seq) < MIN_LENGTH or len(seq) > MAX_LENGTH:
        return None
    return seq


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate sequences, keeping first occurrence."""
    return df.drop_duplicates(subset="sequence", keep="first").reset_index(drop=True)


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Full preprocessing pipeline: clean, filter, deduplicate, add length."""
    # Clean sequences
    df = df.copy()
    df["sequence"] = df["sequence"].apply(clean_sequence)
    df = df.dropna(subset=["sequence"]).reset_index(drop=True)

    # Deduplicate
    df = deduplicate(df)

    # Ensure length column
    df["length"] = df["sequence"].str.len()

    # Standardize activity
    df["activity"] = df["activity"].str.lower().str.strip()

    # Standardize source_db
    df["source_db"] = df["source_db"].str.strip()

    # Ensure mic_um is numeric
    df["mic_um"] = pd.to_numeric(df["mic_um"], errors="coerce")

    # Sort by id
    df = df.sort_values("id").reset_index(drop=True)

    # Select final columns in schema order
    cols = ["id", "sequence", "length", "source_db", "target_organisms", "activity", "mic_um"]
    return df[cols]


def save_unified(df: pd.DataFrame, output_path: Path | None = None) -> Path:
    """Save unified AMP dataset."""
    out = output_path or PROCESSED_DIR / "amps_unified.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df_out = df.copy()
    # Convert list columns to semicolon-separated for CSV
    df_out["target_organisms"] = df_out["target_organisms"].apply(
        lambda x: ";".join(x) if isinstance(x, list) else str(x)
    )
    df_out.to_csv(out, index=False)
    return out


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df = load_raw_amps()
    df = preprocess(df)
    out = save_unified(df)
    print(f"Preprocessed {len(df)} AMPs → {out}")

    # Print summary stats
    print(f"  Activity distribution:\n{df['activity'].value_counts().to_string()}")
    print(f"  Length: min={df['length'].min()}, max={df['length'].max()}, median={df['length'].median()}")
    print(f"  MIC available: {df['mic_um'].notna().sum()}/{len(df)}")


if __name__ == "__main__":
    main()

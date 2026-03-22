#!/usr/bin/env python3
"""
AgroShield Intensive Training Pipeline v2
==========================================
Designed for A40 GPU (48GB VRAM), ~6-8 hours total runtime.

1. Download real AMPs from DRAMP/UniProt + real non-AMP negatives
2. Fine-tune ESM-2 3B as AMP classifier (gradient checkpointing + fp16)
3. Multi-round evolutionary AMP generation (500+ generations, pop 2000)
4. Diversity filtering via 3B embeddings (cosine similarity)
5. Multi-dimensional scoring
6. Final embeddings for the app

All progress logged to train_overnight.log. Checkpoint/resume supported.
"""
from __future__ import annotations

import csv
import gc
import json
import logging
import math
import os
import random
import re
import sys
import time
import traceback
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer, EsmModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "01_data" / "data" / "processed"
MODELS_DIR = ROOT / "02_model" / "models"
SCORING_OUTPUT = ROOT / "03_scoring" / "output"
LOG_FILE = ROOT / "train_overnight.log"
CHECKPOINT_DIR = MODELS_DIR / "checkpoints"
PIPELINE_STATE = CHECKPOINT_DIR / "pipeline_state.json"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
@dataclass
class Config:
    # Data acquisition
    download_timeout: int = 30
    max_uniprot_amps: int = 3000
    max_uniprot_negatives: int = 5000
    min_seq_len: int = 10
    max_seq_len: int = 50

    # Fine-tune classifier (ESM-2 3B)
    finetune_model_name: str = "facebook/esm2_t36_3B_UR50D"
    finetune_embedding_dim: int = 2560
    finetune_epochs: int = 60
    finetune_batch_size: int = 4
    gradient_accumulation_steps: int = 8
    finetune_lr: float = 1e-5
    finetune_unfreeze_layers: int = 10
    classifier_hidden: int = 1024
    classifier_dropout: float = 0.2
    warmup_epochs: int = 5
    patience: int = 10

    # Evolution
    evo_rounds: list = field(default_factory=lambda: [
        {"name": "exploration", "generations": 200, "population": 2000,
         "mutation_rate": 0.20, "threshold": 0.50},
        {"name": "exploitation", "generations": 200, "population": 2000,
         "mutation_rate": 0.10, "threshold": 0.70},
        {"name": "polish", "generations": 150, "population": 1500,
         "mutation_rate": 0.05, "threshold": 0.80},
    ])
    evo_elite_frac: float = 0.1
    evo_tournament_size: int = 7
    evo_infer_batch_size: int = 64

    # Diversity filtering
    diversity_sim_threshold: float = 0.95
    embed_batch_size: int = 16

    # General
    seed: int = 42
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint_every_n_epochs: int = 5
    checkpoint_every_n_gens: int = 50


CFG = Config()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def setup_logging():
    fmt = "%(asctime)s | %(levelname)-8s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.FileHandler(LOG_FILE, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )

log = logging.getLogger("overnight")

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
VALID_AAS = set("ACDEFGHIKLMNPQRSTVWY")
VALID_AAS_LIST = sorted(VALID_AAS)

AMP_AA_FREQ = {
    "A": 0.077, "C": 0.065, "D": 0.025, "E": 0.022, "F": 0.042,
    "G": 0.098, "H": 0.024, "I": 0.055, "K": 0.102, "L": 0.095,
    "M": 0.015, "N": 0.035, "P": 0.038, "Q": 0.022, "R": 0.058,
    "S": 0.048, "T": 0.038, "V": 0.052, "W": 0.042, "Y": 0.028,
}

AGRO_PATHOGENS = [
    "Fusarium oxysporum", "Xanthomonas campestris", "Botrytis cinerea",
    "Pseudomonas syringae", "Magnaporthe oryzae", "Puccinia graminis",
    "Ralstonia solanacearum", "Erwinia amylovora", "Phytophthora infestans",
    "Alternaria solani", "Sclerotinia sclerotiorum", "Rhizoctonia solani",
    "Colletotrichum gloeosporioides", "Verticillium dahliae",
]


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def elapsed(start: float) -> str:
    m, s = divmod(time.time() - start, 60)
    h, m = divmod(m, 60)
    return f"{int(h)}h{int(m):02d}m{int(s):02d}s"


def is_valid_sequence(seq: str) -> bool:
    """Check if sequence contains only standard amino acids."""
    return (CFG.min_seq_len <= len(seq) <= CFG.max_seq_len and
            all(c in VALID_AAS for c in seq.upper()))


def load_pipeline_state() -> dict:
    if PIPELINE_STATE.exists():
        with open(PIPELINE_STATE) as f:
            return json.load(f)
    return {}


def save_pipeline_state(state: dict):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_STATE, "w") as f:
        json.dump(state, f, indent=2)


# =========================================================================
# PHASE 1: Real Data Acquisition
# =========================================================================
def fetch_uniprot_amps(max_results: int = 3000) -> list[dict]:
    """Download real antimicrobial peptides from UniProt."""
    log.info("  Downloading AMPs from UniProt...")
    sequences = []
    base_url = "https://rest.uniprot.org/uniprotkb/search"

    queries = [
        # Antimicrobial peptides, reviewed, in peptide length range
        "(keyword:KW-0929) AND (length:[10 TO 50]) AND (reviewed:true)",
        # Defensins
        "(family:defensin) AND (length:[10 TO 50]) AND (reviewed:true)",
        # Cathelicidins
        '(protein_name:"cathelicidin") AND (length:[10 TO 50]) AND (reviewed:true)',
        # Cecropins
        '(protein_name:"cecropin") AND (length:[10 TO 50]) AND (reviewed:true)',
        # Magainins and related
        '(protein_name:"magainin") AND (length:[10 TO 50])',
        # Broader: antimicrobial + peptide in organism groups
        "(keyword:KW-0929) AND (length:[10 TO 100]) AND (reviewed:true)",
    ]

    seen = set()
    for query in queries:
        if len(sequences) >= max_results:
            break
        try:
            params = {
                "query": query,
                "format": "fasta",
                "size": min(500, max_results - len(sequences)),
            }
            resp = requests.get(base_url, params=params, timeout=CFG.download_timeout)
            resp.raise_for_status()

            for entry in resp.text.strip().split(">"):
                if not entry.strip():
                    continue
                lines = entry.strip().split("\n")
                header = lines[0]
                seq = "".join(lines[1:]).upper().strip()

                # Truncate long sequences to max_seq_len
                if len(seq) > CFG.max_seq_len:
                    seq = seq[:CFG.max_seq_len]

                if not is_valid_sequence(seq) or seq in seen:
                    continue
                seen.add(seq)

                # Extract UniProt ID
                uid = header.split("|")[1] if "|" in header else header.split()[0]
                sequences.append({
                    "id": f"UNIPROT_{uid}",
                    "sequence": seq,
                    "length": len(seq),
                    "source_db": "UniProt",
                })

                if len(sequences) >= max_results:
                    break

            log.info(f"    UniProt query got {len(sequences)} AMPs so far")
        except Exception as e:
            log.warning(f"    UniProt query failed: {e}")
            continue

    log.info(f"  UniProt: {len(sequences)} AMPs downloaded")
    return sequences


def fetch_dramp_amps() -> list[dict]:
    """Try to download AMPs from DRAMP database."""
    log.info("  Downloading AMPs from DRAMP...")
    sequences = []

    urls = [
        "http://dramp.cpu-bioinfor.org/downloads/download.php?filename=general_amps.fasta",
        "http://dramp.cpu-bioinfor.org/downloads/download.php?filename=DRAMP3.0_general_amps.fasta",
    ]

    for url in urls:
        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code != 200:
                continue

            seen = set()
            for entry in resp.text.strip().split(">"):
                if not entry.strip():
                    continue
                lines = entry.strip().split("\n")
                header = lines[0]
                seq = "".join(lines[1:]).upper().strip()

                if not is_valid_sequence(seq) or seq in seen:
                    continue
                seen.add(seq)

                dramp_id = header.split("|")[0].strip() if "|" in header else header.split()[0]
                sequences.append({
                    "id": f"DRAMP_{dramp_id}",
                    "sequence": seq,
                    "length": len(seq),
                    "source_db": "DRAMP",
                })

            if sequences:
                log.info(f"  DRAMP: {len(sequences)} AMPs downloaded")
                return sequences
        except Exception as e:
            log.warning(f"    DRAMP download failed: {e}")
            continue

    log.info("  DRAMP: download failed, skipping")
    return sequences


def fetch_uniprot_negatives(max_results: int = 5000) -> list[dict]:
    """Download real non-AMP protein sequences from UniProt as hard negatives."""
    log.info("  Downloading non-AMP negatives from UniProt...")
    sequences = []
    base_url = "https://rest.uniprot.org/uniprotkb/search"

    queries = [
        # Housekeeping proteins, short fragments
        "(NOT keyword:KW-0929) AND (NOT keyword:KW-0800) AND (length:[10 TO 50]) AND (reviewed:true) AND (organism_id:9606)",
        # Plant proteins, not antimicrobial
        "(NOT keyword:KW-0929) AND (length:[10 TO 50]) AND (reviewed:true) AND (taxonomy_id:3193)",
        # Bacterial proteins, not antimicrobial
        "(NOT keyword:KW-0929) AND (length:[10 TO 50]) AND (reviewed:true) AND (taxonomy_id:2)",
        # Structural proteins
        "(keyword:KW-0732) AND (NOT keyword:KW-0929) AND (length:[10 TO 80]) AND (reviewed:true)",
        # Enzymes, short
        "(keyword:KW-0378) AND (NOT keyword:KW-0929) AND (length:[10 TO 50]) AND (reviewed:true)",
    ]

    seen = set()
    for query in queries:
        if len(sequences) >= max_results:
            break
        try:
            params = {
                "query": query,
                "format": "fasta",
                "size": min(500, max_results - len(sequences)),
            }
            resp = requests.get(base_url, params=params, timeout=CFG.download_timeout)
            resp.raise_for_status()

            for entry in resp.text.strip().split(">"):
                if not entry.strip():
                    continue
                lines = entry.strip().split("\n")
                seq = "".join(lines[1:]).upper().strip()

                if len(seq) > CFG.max_seq_len:
                    seq = seq[:CFG.max_seq_len]

                if not is_valid_sequence(seq) or seq in seen:
                    continue
                seen.add(seq)
                sequences.append({
                    "id": f"NEG_{len(sequences):05d}",
                    "sequence": seq,
                    "length": len(seq),
                    "source": "UniProt_negative",
                })

                if len(sequences) >= max_results:
                    break

            log.info(f"    UniProt negatives: {len(sequences)} so far")
        except Exception as e:
            log.warning(f"    UniProt negative query failed: {e}")
            continue

    log.info(f"  UniProt negatives: {len(sequences)} downloaded")
    return sequences


def generate_shuffled_negatives(positive_seqs: list[str], n: int, seed: int = 42) -> list[str]:
    """Generate shuffled versions of AMPs as additional negatives."""
    rng = random.Random(seed)
    negatives = []
    for seq in rng.choices(positive_seqs, k=n):
        chars = list(seq)
        rng.shuffle(chars)
        negatives.append("".join(chars))
    return negatives


def phase1_data_acquisition() -> tuple[list[str], list[str]]:
    """Download real AMPs and real non-AMP negatives."""
    log.info("PHASE 1: Real data acquisition")
    t0 = time.time()

    # Load existing real AMPs
    existing_df = pd.read_csv(DATA_DIR / "amps_unified.csv")
    existing_seqs = set(existing_df["sequence"].tolist())
    positive_seqs = list(existing_seqs)
    log.info(f"  Existing real AMPs: {len(positive_seqs)}")

    # Download more from UniProt
    uniprot_amps = fetch_uniprot_amps(CFG.max_uniprot_amps)
    for amp in uniprot_amps:
        if amp["sequence"] not in existing_seqs:
            positive_seqs.append(amp["sequence"])
            existing_seqs.add(amp["sequence"])

    # Download from DRAMP
    dramp_amps = fetch_dramp_amps()
    for amp in dramp_amps:
        if amp["sequence"] not in existing_seqs:
            positive_seqs.append(amp["sequence"])
            existing_seqs.add(amp["sequence"])

    log.info(f"  Total real AMPs after download: {len(positive_seqs)}")

    # Download real negatives
    neg_records = fetch_uniprot_negatives(CFG.max_uniprot_negatives)
    negative_seqs = [r["sequence"] for r in neg_records]

    # Add shuffled negatives (20% of positives)
    n_shuffled = max(len(positive_seqs) // 5, 100)
    shuffled = generate_shuffled_negatives(positive_seqs, n_shuffled, CFG.seed)
    negative_seqs.extend(shuffled)
    log.info(f"  Total negatives: {len(negative_seqs)} ({len(neg_records)} real + {n_shuffled} shuffled)")

    # Save expanded dataset
    records = []
    for i, seq in enumerate(positive_seqs):
        records.append({
            "id": f"AMP_{i:05d}",
            "sequence": seq,
            "length": len(seq),
            "source_db": "combined",
            "label": 1,
        })
    for i, seq in enumerate(negative_seqs):
        records.append({
            "id": f"NEG_{i:05d}",
            "sequence": seq,
            "length": len(seq),
            "source_db": "negative",
            "label": 0,
        })

    df = pd.DataFrame(records)
    out = DATA_DIR / "training_data_v2.csv"
    df.to_csv(out, index=False)
    log.info(f"  Saved training data: {len(df)} total → {out}")
    log.info(f"  Phase 1 done in {elapsed(t0)}")

    return positive_seqs, negative_seqs


# =========================================================================
# PHASE 2: Fine-tune ESM-2 3B Classifier
# =========================================================================
class AMPDataset(Dataset):
    def __init__(self, sequences: list[str], labels: list[int]):
        self.sequences = sequences
        self.labels = labels

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]


def collate_fn(batch, tokenizer, max_length=512):
    sequences, labels = zip(*batch)
    spaced = [" ".join(seq) for seq in sequences]
    inputs = tokenizer(spaced, return_tensors="pt", padding=True,
                       truncation=True, max_length=max_length)
    labels = torch.tensor(labels, dtype=torch.long)
    return inputs, labels


class ESM2Classifier(nn.Module):
    """ESM-2 3B with classification head for AMP prediction."""
    def __init__(self, esm_model_name: str, hidden_dim: int, dropout: float,
                 num_classes: int = 2):
        super().__init__()
        self.esm = AutoModel.from_pretrained(esm_model_name, use_safetensors=True)
        esm_dim = self.esm.config.hidden_size

        self.classifier = nn.Sequential(
            nn.LayerNorm(esm_dim),
            nn.Linear(esm_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes),
        )

    def enable_gradient_checkpointing(self):
        """Enable gradient checkpointing to save VRAM."""
        self.esm.gradient_checkpointing_enable()
        log.info("  Gradient checkpointing enabled")

    def freeze_esm(self, unfreeze_last_n: int = 10):
        """Freeze all ESM layers except the last N."""
        for param in self.esm.parameters():
            param.requires_grad = False

        layers = self.esm.encoder.layer
        for layer in layers[-unfreeze_last_n:]:
            for param in layer.parameters():
                param.requires_grad = True

        # Unfreeze final layer norm
        for name, param in self.esm.named_parameters():
            if "pooler" in name:
                param.requires_grad = True
            elif "layer_norm" in name and "encoder.layer" not in name:
                param.requires_grad = True

        n_trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        n_total = sum(p.numel() for p in self.parameters())
        log.info(f"  Trainable: {n_trainable:,} / {n_total:,} params ({100*n_trainable/n_total:.1f}%)")

    def forward(self, input_ids, attention_mask, **kwargs):
        outputs = self.esm(input_ids=input_ids, attention_mask=attention_mask)
        hidden = outputs.last_hidden_state
        mask = attention_mask.unsqueeze(-1).float()
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
        logits = self.classifier(pooled)
        return logits

    @torch.no_grad()
    def predict_proba(self, input_ids, attention_mask, **kwargs):
        logits = self.forward(input_ids, attention_mask, **kwargs)
        probs = torch.softmax(logits, dim=-1)
        return probs[:, 1]


def get_warmup_cosine_scheduler(optimizer, warmup_epochs: int, total_epochs: int,
                                 steps_per_epoch: int):
    """Linear warmup then cosine decay."""
    warmup_steps = warmup_epochs * steps_per_epoch
    total_steps = total_epochs * steps_per_epoch

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(warmup_steps, 1)
        progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
        return 0.5 * (1 + math.cos(math.pi * progress))

    return LambdaLR(optimizer, lr_lambda)


def phase2_finetune(positive_seqs: list[str], negative_seqs: list[str]) -> tuple:
    """Fine-tune ESM-2 3B as an AMP classifier."""
    log.info("PHASE 2: Fine-tuning ESM-2 3B classifier")
    t0 = time.time()

    # Build dataset
    all_seqs = positive_seqs + negative_seqs
    all_labels = [1] * len(positive_seqs) + [0] * len(negative_seqs)

    combined = list(zip(all_seqs, all_labels))
    random.Random(CFG.seed).shuffle(combined)
    all_seqs, all_labels = zip(*combined)
    all_seqs, all_labels = list(all_seqs), list(all_labels)

    n_total = len(all_seqs)
    n_train = int(0.85 * n_total)
    train_seqs, val_seqs = all_seqs[:n_train], all_seqs[n_train:]
    train_labels, val_labels = all_labels[:n_train], all_labels[n_train:]

    log.info(f"  Train: {n_train} ({sum(train_labels)} pos), "
             f"Val: {n_total - n_train} ({sum(val_labels)} pos)")

    train_ds = AMPDataset(train_seqs, train_labels)
    val_ds = AMPDataset(val_seqs, val_labels)

    tokenizer = AutoTokenizer.from_pretrained(CFG.finetune_model_name)

    def collate(batch):
        return collate_fn(batch, tokenizer)

    train_loader = DataLoader(train_ds, batch_size=CFG.finetune_batch_size,
                              shuffle=True, collate_fn=collate, num_workers=2,
                              pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=CFG.finetune_batch_size * 2,
                            shuffle=False, collate_fn=collate, num_workers=2,
                            pin_memory=True)

    # Build model
    log.info(f"  Loading {CFG.finetune_model_name} (3B params)...")
    model = ESM2Classifier(
        CFG.finetune_model_name,
        CFG.classifier_hidden,
        CFG.classifier_dropout,
    )
    model.freeze_esm(CFG.finetune_unfreeze_layers)
    model.enable_gradient_checkpointing()
    model.to(CFG.device)

    # Optimizer with differential LR
    esm_params = [p for n, p in model.named_parameters()
                  if p.requires_grad and "classifier" not in n]
    head_params = [p for n, p in model.named_parameters()
                   if p.requires_grad and "classifier" in n]

    optimizer = AdamW([
        {"params": esm_params, "lr": CFG.finetune_lr},
        {"params": head_params, "lr": CFG.finetune_lr * 10},
    ], weight_decay=0.01)

    steps_per_epoch = len(train_loader) // CFG.gradient_accumulation_steps
    scheduler = get_warmup_cosine_scheduler(
        optimizer, CFG.warmup_epochs, CFG.finetune_epochs, steps_per_epoch
    )

    criterion = nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler("cuda", enabled=(CFG.device == "cuda"))

    best_val_auc = 0.0
    best_state = None
    patience_counter = 0
    start_epoch = 1

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    # Check for resume
    resume_ckpt = CHECKPOINT_DIR / "training_resume.pt"
    if resume_ckpt.exists():
        log.info(f"  Resuming from checkpoint...")
        ckpt = torch.load(resume_ckpt, map_location=CFG.device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        scheduler.load_state_dict(ckpt["scheduler_state_dict"])
        scaler.load_state_dict(ckpt["scaler_state_dict"])
        start_epoch = ckpt["epoch"] + 1
        best_val_auc = ckpt.get("best_val_auc", 0.0)
        best_state = ckpt.get("best_model_state_dict")
        patience_counter = ckpt.get("patience_counter", 0)
        log.info(f"  Resumed from epoch {start_epoch - 1}, best AUC: {best_val_auc:.4f}")

    for epoch in range(start_epoch, CFG.finetune_epochs + 1):
        # Train
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        optimizer.zero_grad()

        for batch_idx, (inputs, labels) in enumerate(train_loader):
            inputs = {k: v.to(CFG.device) for k, v in inputs.items()}
            labels = labels.to(CFG.device)

            with torch.amp.autocast("cuda", enabled=(CFG.device == "cuda")):
                logits = model(**inputs)
                loss = criterion(logits, labels)
                loss = loss / CFG.gradient_accumulation_steps

            scaler.scale(loss).backward()

            train_loss += loss.item() * CFG.gradient_accumulation_steps * labels.size(0)
            preds = logits.argmax(dim=-1)
            train_correct += (preds == labels).sum().item()
            train_total += labels.size(0)

            if (batch_idx + 1) % CFG.gradient_accumulation_steps == 0:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
                scheduler.step()
                optimizer.zero_grad()

        # Handle remaining gradients
        if (batch_idx + 1) % CFG.gradient_accumulation_steps != 0:
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            optimizer.zero_grad()

        train_loss /= max(train_total, 1)
        train_acc = train_correct / max(train_total, 1)

        # Validate
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        all_probs = []
        all_true = []

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs = {k: v.to(CFG.device) for k, v in inputs.items()}
                labels = labels.to(CFG.device)

                with torch.amp.autocast("cuda", enabled=(CFG.device == "cuda")):
                    logits = model(**inputs)
                    loss = criterion(logits, labels)

                val_loss += loss.item() * labels.size(0)
                preds = logits.argmax(dim=-1)
                val_correct += (preds == labels).sum().item()
                val_total += labels.size(0)

                probs = torch.softmax(logits, dim=-1)[:, 1]
                all_probs.extend(probs.cpu().tolist())
                all_true.extend(labels.cpu().tolist())

        val_loss /= max(val_total, 1)
        val_acc = val_correct / max(val_total, 1)

        from sklearn.metrics import roc_auc_score
        try:
            val_auc = roc_auc_score(all_true, all_probs)
        except ValueError:
            val_auc = 0.5

        current_lr = scheduler.get_last_lr()[0]
        log.info(
            f"  Epoch {epoch:2d}/{CFG.finetune_epochs} | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} AUC: {val_auc:.4f} | "
            f"LR: {current_lr:.2e}"
        )

        # Early stopping
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            best_state = deepcopy(model.state_dict())
            patience_counter = 0

            ckpt_path = CHECKPOINT_DIR / "best_classifier.pt"
            torch.save({
                "epoch": epoch,
                "model_state_dict": best_state,
                "val_auc": best_val_auc,
                "val_acc": val_acc,
                "config": {
                    "model_name": CFG.finetune_model_name,
                    "hidden_dim": CFG.classifier_hidden,
                    "dropout": CFG.classifier_dropout,
                }
            }, ckpt_path)
            log.info(f"    ★ New best AUC: {best_val_auc:.4f} → saved checkpoint")
        else:
            patience_counter += 1
            if patience_counter >= CFG.patience:
                log.info(f"  Early stopping at epoch {epoch} "
                         f"(no improvement for {CFG.patience} epochs)")
                break

        # Save resume checkpoint periodically
        if epoch % CFG.checkpoint_every_n_epochs == 0:
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
                "best_val_auc": best_val_auc,
                "best_model_state_dict": best_state,
                "patience_counter": patience_counter,
            }, resume_ckpt)
            log.info(f"    Saved resume checkpoint (epoch {epoch})")

    # Load best model
    if best_state is not None:
        model.load_state_dict(best_state)
    log.info(f"  Best validation AUC: {best_val_auc:.4f}")

    # Final evaluation
    model.eval()
    from sklearn.metrics import classification_report
    all_preds = []
    all_probs = []
    all_true = []
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs = {k: v.to(CFG.device) for k, v in inputs.items()}
            labels = labels.to(CFG.device)
            with torch.amp.autocast("cuda", enabled=(CFG.device == "cuda")):
                logits = model(**inputs)
            preds = logits.argmax(dim=-1)
            probs = torch.softmax(logits, dim=-1)[:, 1]
            all_preds.extend(preds.cpu().tolist())
            all_probs.extend(probs.cpu().tolist())
            all_true.extend(labels.cpu().tolist())

    report = classification_report(all_true, all_preds, target_names=["non-AMP", "AMP"])
    log.info(f"\n  Classification Report:\n{report}")

    # Save final model
    final_path = MODELS_DIR / "esm2_amp_classifier.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "val_auc": best_val_auc,
        "config": {
            "model_name": CFG.finetune_model_name,
            "hidden_dim": CFG.classifier_hidden,
            "dropout": CFG.classifier_dropout,
        }
    }, final_path)
    log.info(f"  Saved fine-tuned 3B model to {final_path}")
    log.info(f"  Phase 2 done in {elapsed(t0)}")

    # Clean up resume checkpoint
    if resume_ckpt.exists():
        resume_ckpt.unlink()

    return model, tokenizer


# =========================================================================
# PHASE 3: Multi-Round Evolutionary AMP Generation
# =========================================================================
def batch_predict(model: ESM2Classifier, tokenizer, sequences: list[str],
                  batch_size: int = 64) -> np.ndarray:
    """Predict AMP probability for sequences using 3B model."""
    model.eval()
    all_probs = []

    for i in range(0, len(sequences), batch_size):
        batch = sequences[i:i + batch_size]
        spaced = [" ".join(seq) for seq in batch]
        inputs = tokenizer(spaced, return_tensors="pt", padding=True,
                           truncation=True, max_length=512)
        inputs = {k: v.to(CFG.device) for k, v in inputs.items()}

        with torch.no_grad(), torch.amp.autocast("cuda", enabled=(CFG.device == "cuda")):
            probs = model.predict_proba(**inputs)
        all_probs.extend(probs.cpu().tolist())

    return np.array(all_probs)


def mutate_sequence(seq: str, mutation_rate: float, rng: random.Random) -> str:
    """Point mutations with AMP-aware substitutions."""
    chars = list(seq)
    n_mutations = max(1, int(len(chars) * mutation_rate))
    n_mutations = min(n_mutations, rng.randint(1, max(1, n_mutations)))

    positions = rng.sample(range(len(chars)), min(n_mutations, len(chars)))
    similar = {
        "K": "RH", "R": "KH", "D": "EN", "E": "DQ",
        "L": "IVA", "I": "LVA", "V": "LIA", "A": "GVL",
        "F": "YW", "Y": "FW", "W": "FY",
        "S": "TN", "T": "SN", "N": "DQS", "Q": "ENK",
        "G": "AP", "P": "GA", "C": "SA", "M": "LI", "H": "KR",
    }

    for pos in positions:
        original = chars[pos]
        if rng.random() < 0.3:
            candidates = similar.get(original, "")
            if candidates:
                chars[pos] = rng.choice(list(candidates))
            else:
                chars[pos] = rng.choice([aa for aa in VALID_AAS_LIST if aa != original])
        else:
            chars[pos] = rng.choice([aa for aa in VALID_AAS_LIST if aa != original])

    return "".join(chars)


def insertion_mutation(seq: str, rng: random.Random) -> str:
    """Insert 1-2 AMP-biased amino acids at random position."""
    aas = list(AMP_AA_FREQ.keys())
    weights = list(AMP_AA_FREQ.values())
    n_insert = rng.randint(1, 2)
    pos = rng.randint(0, len(seq))
    insert = "".join(rng.choices(aas, weights=weights, k=n_insert))
    return seq[:pos] + insert + seq[pos:]


def deletion_mutation(seq: str, rng: random.Random) -> str:
    """Delete 1-2 amino acids at random positions."""
    if len(seq) <= CFG.min_seq_len + 2:
        return seq
    n_delete = rng.randint(1, min(2, len(seq) - CFG.min_seq_len))
    chars = list(seq)
    for _ in range(n_delete):
        if len(chars) > CFG.min_seq_len:
            pos = rng.randint(0, len(chars) - 1)
            chars.pop(pos)
    return "".join(chars)


def block_swap(seq: str, rng: random.Random) -> str:
    """Swap two 3-5 AA blocks within the sequence."""
    if len(seq) < 10:
        return seq
    block_size = rng.randint(3, min(5, len(seq) // 3))
    pos1 = rng.randint(0, len(seq) - block_size * 2)
    pos2 = rng.randint(pos1 + block_size, len(seq) - block_size)
    chars = list(seq)
    block1 = chars[pos1:pos1 + block_size]
    block2 = chars[pos2:pos2 + block_size]
    chars[pos1:pos1 + block_size] = block2
    chars[pos2:pos2 + block_size] = block1
    return "".join(chars)


def crossover(seq1: str, seq2: str, rng: random.Random) -> str:
    """Single-point crossover."""
    if abs(len(seq1) - len(seq2)) > 10:
        return seq1
    min_len = min(len(seq1), len(seq2))
    point = rng.randint(1, min_len - 1)
    return seq1[:point] + seq2[point:min_len]


def hamming_similarity(s1: str, s2: str) -> float:
    """Hamming-based similarity for same-length sequences."""
    if len(s1) != len(s2):
        min_len = min(len(s1), len(s2))
        max_len = max(len(s1), len(s2))
        matches = sum(a == b for a, b in zip(s1[:min_len], s2[:min_len]))
        return matches / max_len
    return sum(a == b for a, b in zip(s1, s2)) / len(s1)


def phase3_evolution(model: ESM2Classifier, tokenizer,
                     seed_seqs: list[str]) -> pd.DataFrame:
    """Multi-round evolutionary AMP generation with 3B classifier."""
    log.info("PHASE 3: Multi-round evolutionary AMP generation")
    t0 = time.time()

    rng = random.Random(CFG.seed + 2000)
    all_candidates = {}  # seq -> score

    # Check for evolution resume
    evo_resume = CHECKPOINT_DIR / "evolution_resume.json"
    resume_round = 0
    resume_gen = 0
    if evo_resume.exists():
        with open(evo_resume) as f:
            evo_state = json.load(f)
        resume_round = evo_state.get("round", 0)
        resume_gen = evo_state.get("generation", 0)
        all_candidates = {k: v for k, v in evo_state.get("candidates", {}).items()}
        log.info(f"  Resuming evolution from round {resume_round + 1}, gen {resume_gen}")
        log.info(f"  Loaded {len(all_candidates)} previous candidates")

    for round_idx, round_cfg in enumerate(CFG.evo_rounds):
        if round_idx < resume_round:
            log.info(f"  Skipping round {round_idx + 1} ({round_cfg['name']}) — already done")
            continue

        round_name = round_cfg["name"]
        n_gens = round_cfg["generations"]
        pop_size = round_cfg["population"]
        mut_rate = round_cfg["mutation_rate"]
        threshold = round_cfg["threshold"]

        log.info(f"\n  Round {round_idx + 1}/3: {round_name}")
        log.info(f"    Generations: {n_gens}, Population: {pop_size}, "
                 f"Mutation rate: {mut_rate}, Threshold: {threshold}")

        # Initialize population
        population = set()

        # Seed from previous round's best candidates
        if all_candidates:
            top_seqs = sorted(all_candidates.items(), key=lambda x: -x[1])
            for seq, _ in top_seqs[:pop_size // 2]:
                population.add(seq)
                for _ in range(3):
                    variant = mutate_sequence(seq, mut_rate, rng)
                    if is_valid_sequence(variant):
                        population.add(variant)

        # Seed from known AMPs
        for seq in seed_seqs:
            if is_valid_sequence(seq):
                population.add(seq)
                for _ in range(3):
                    variant = mutate_sequence(seq, mut_rate * 1.5, rng)
                    if is_valid_sequence(variant):
                        population.add(variant)

        # Add random AMPs
        aas = list(AMP_AA_FREQ.keys())
        weights = list(AMP_AA_FREQ.values())
        for _ in range(pop_size // 4):
            length = rng.randint(12, 35)
            seq = "".join(rng.choices(aas, weights=weights, k=length))
            population.add(seq)

        population = list(population)[:pop_size * 2]
        log.info(f"    Initial population: {len(population)}")

        # Score initial population
        scores = batch_predict(model, tokenizer, population, CFG.evo_infer_batch_size)

        start_gen = resume_gen if round_idx == resume_round else 1

        for gen in range(start_gen, n_gens + 1):
            # Store good candidates
            for seq, score in zip(population, scores):
                if score >= threshold:
                    if seq not in all_candidates or all_candidates[seq] < score:
                        all_candidates[seq] = score

            sorted_indices = np.argsort(-scores)
            n_elite = max(2, int(len(population) * CFG.evo_elite_frac))
            elite = [population[i] for i in sorted_indices[:n_elite]]

            new_population = set(elite)

            while len(new_population) < pop_size:
                # Tournament selection
                tournament = rng.sample(range(len(population)),
                                        min(CFG.evo_tournament_size, len(population)))
                winner_idx = max(tournament, key=lambda i: scores[i])
                parent = population[winner_idx]

                # Choose operator
                op = rng.random()
                if op < 0.50:
                    # Point mutation
                    child = mutate_sequence(parent, mut_rate, rng)
                elif op < 0.70:
                    # Crossover + optional mutation
                    tournament2 = rng.sample(range(len(population)),
                                             min(CFG.evo_tournament_size, len(population)))
                    winner2_idx = max(tournament2, key=lambda i: scores[i])
                    parent2 = population[winner2_idx]
                    child = crossover(parent, parent2, rng)
                    if rng.random() < 0.5:
                        child = mutate_sequence(child, mut_rate * 0.5, rng)
                elif op < 0.80:
                    # Insertion
                    child = insertion_mutation(parent, rng)
                elif op < 0.90:
                    # Deletion
                    child = deletion_mutation(parent, rng)
                else:
                    # Block swap
                    child = block_swap(parent, rng)

                if is_valid_sequence(child):
                    # Diversity check: reject if >95% similar to existing
                    too_similar = False
                    for existing in list(new_population)[:50]:  # check against sample
                        if hamming_similarity(child, existing) > 0.95:
                            too_similar = True
                            break
                    if not too_similar:
                        new_population.add(child)

            # Inject fresh random mutants (10% of population)
            n_fresh = pop_size // 10
            for _ in range(n_fresh):
                length = rng.randint(12, 35)
                seq = "".join(rng.choices(aas, weights=weights, k=length))
                if is_valid_sequence(seq):
                    new_population.add(seq)

            population = list(new_population)[:pop_size]
            scores = batch_predict(model, tokenizer, population, CFG.evo_infer_batch_size)

            if gen % 10 == 0 or gen == 1:
                top5_mean = np.mean(sorted(scores, reverse=True)[:5])
                pop_mean = np.mean(scores)
                n_above = sum(1 for s in scores if s >= threshold)
                log.info(
                    f"    Gen {gen:3d}/{n_gens} | "
                    f"Pop mean: {pop_mean:.4f} | Top-5 mean: {top5_mean:.4f} | "
                    f"Above {threshold}: {n_above}/{len(population)} | "
                    f"Total candidates: {len(all_candidates)}"
                )

            # Checkpoint evolution
            if gen % CFG.checkpoint_every_n_gens == 0:
                with open(evo_resume, "w") as f:
                    json.dump({
                        "round": round_idx,
                        "generation": gen,
                        "candidates": all_candidates,
                    }, f)

        # Final collection for this round
        for seq, score in zip(population, scores):
            if score >= threshold:
                if seq not in all_candidates or all_candidates[seq] < score:
                    all_candidates[seq] = score

        log.info(f"    Round {round_idx + 1} done. Total candidates: {len(all_candidates)}")

    # Remove seed sequences
    seed_set = set(seed_seqs)
    novel = {s: sc for s, sc in all_candidates.items() if s not in seed_set}
    log.info(f"  Total novel candidates: {len(novel)}")

    # Build DataFrame
    sorted_candidates = sorted(novel.items(), key=lambda x: -x[1])
    records = []
    for i, (seq, score) in enumerate(sorted_candidates):
        records.append({
            "id": f"GEN_{i:05d}",
            "sequence": seq,
            "length": len(seq),
            "amp_probability": round(score, 4),
        })

    results = pd.DataFrame(records)
    out = MODELS_DIR / "generated_candidates_v2.csv"
    results.to_csv(out, index=False)
    log.info(f"  Generated {len(results)} candidates → {out}")
    log.info(f"  Phase 3 done in {elapsed(t0)}")

    # Clean up evolution checkpoint
    if evo_resume.exists():
        evo_resume.unlink()

    return results


# =========================================================================
# PHASE 4: Diversity Filtering with 3B Embeddings
# =========================================================================
def generate_esm2_embeddings(sequences: list[str], model_name: str,
                              batch_size: int) -> np.ndarray:
    """Generate embeddings using ESM-2 model."""
    device = CFG.device
    log.info(f"  Loading {model_name} for embeddings...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = AutoModel.from_pretrained(model_name, torch_dtype=dtype, use_safetensors=True)
    model.eval()
    model.to(device)

    all_embeddings = []
    n_batches = (len(sequences) + batch_size - 1) // batch_size

    for i in range(0, len(sequences), batch_size):
        batch_idx = i // batch_size + 1
        batch = sequences[i:i + batch_size]
        spaced = [" ".join(seq) for seq in batch]
        inputs = tokenizer(spaced, return_tensors="pt", padding=True,
                           truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad(), torch.amp.autocast(device_type=device, enabled=(device == "cuda")):
            outputs = model(**inputs)

        hidden = outputs.last_hidden_state.float()
        mask = inputs["attention_mask"].unsqueeze(-1).float()
        embs = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
        all_embeddings.append(embs.cpu().numpy())

        if batch_idx % 100 == 0 or batch_idx == n_batches:
            log.info(f"    Embedding batch {batch_idx}/{n_batches}")

    del model, tokenizer
    torch.cuda.empty_cache()
    gc.collect()

    return np.vstack(all_embeddings)


def phase4_diversity_filter(candidates_df: pd.DataFrame) -> pd.DataFrame:
    """Filter near-duplicate candidates using 3B embeddings."""
    log.info("PHASE 4: Diversity filtering with 3B embeddings")
    t0 = time.time()

    sequences = candidates_df["sequence"].tolist()
    n_total = len(sequences)

    if n_total == 0:
        log.warning("  No candidates to filter")
        return candidates_df

    # Generate embeddings
    embeddings = generate_esm2_embeddings(
        sequences, CFG.finetune_model_name, CFG.embed_batch_size
    )

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = embeddings / norms

    # Greedy diversity filtering
    log.info(f"  Filtering {n_total} candidates (threshold={CFG.diversity_sim_threshold})...")
    keep_indices = []
    kept_embeddings = []

    # Sort by amp_probability descending (keep best first)
    sorted_df = candidates_df.sort_values("amp_probability", ascending=False)
    sorted_indices = sorted_df.index.tolist()

    for idx in sorted_indices:
        emb = normed[idx]
        if kept_embeddings:
            # Compute similarity to all kept embeddings
            kept_matrix = np.array(kept_embeddings)
            sims = kept_matrix @ emb
            if np.max(sims) > CFG.diversity_sim_threshold:
                continue  # too similar, skip

        keep_indices.append(idx)
        kept_embeddings.append(emb)

    filtered_df = candidates_df.iloc[keep_indices].reset_index(drop=True)

    # Re-assign IDs
    filtered_df["id"] = [f"GEN_{i:05d}" for i in range(len(filtered_df))]

    log.info(f"  Kept {len(filtered_df)}/{n_total} diverse candidates")
    log.info(f"  Phase 4 done in {elapsed(t0)}")

    # Save filtered embeddings for the app
    filtered_seqs = filtered_df["sequence"].tolist()
    filtered_embs = embeddings[[i for i in keep_indices]]
    out = MODELS_DIR / "candidate_embeddings_v2.npz"
    np.savez(out,
             ids=np.array(filtered_df["id"].tolist()),
             sequences=np.array(filtered_seqs),
             embeddings=filtered_embs)
    log.info(f"  Saved embeddings → {out}")

    return filtered_df


# =========================================================================
# PHASE 5: Multi-dimensional Scoring
# =========================================================================
def score_all_candidates_inline(df: pd.DataFrame) -> pd.DataFrame:
    """Score candidates using multi-dimensional ranking."""
    from Bio.SeqUtils.ProtParam import ProteinAnalysis
    from modlamp.descriptors import PeptideDescriptor

    W_ACTIVITY = 0.35
    W_HEMOLYTIC = 0.25
    W_PHYTO = 0.15
    W_STABILITY = 0.15
    W_SYNTH = 0.10

    def _net_charge(seq, pH=7.0):
        return ProteinAnalysis(seq).charge_at_pH(pH)

    def _hydrophobic_ratio(seq):
        return sum(1 for aa in seq if aa in "AILMFWVP") / len(seq)

    def _instability_index(seq):
        return ProteinAnalysis(seq).instability_index()

    def _hydrophobic_moment(seq):
        try:
            desc = PeptideDescriptor(seq, "eisenberg")
            desc.calculate_moment(window=min(11, len(seq)))
            return float(desc.descriptor[0][0])
        except Exception:
            return 0.3  # default moderate value

    def _hemolytic_score(seq):
        hm = _hydrophobic_moment(seq)
        charge = _net_charge(seq)
        hr = _hydrophobic_ratio(seq)
        hm_s = min(hm / 0.8, 1.0)
        hr_s = min(hr / 0.7, 1.0)
        cp = max(0.0, (charge - 8) / 10)
        return max(0.0, min(1.0, 0.45 * hm_s + 0.35 * hr_s + 0.20 * cp))

    def _phytotoxicity_score(seq):
        length = len(seq)
        charge = _net_charge(seq)
        hr = _hydrophobic_ratio(seq)
        if length <= 25: ls = 0.0
        elif length <= 35: ls = (length - 25) / 10
        else: ls = 1.0
        if 2 <= charge <= 6: cs = 0.0
        elif charge < 2: cs = min((2 - charge) / 5, 1.0)
        else: cs = min((charge - 6) / 6, 1.0)
        if hr <= 0.4: hs = 0.0
        else: hs = min((hr - 0.4) / 0.3, 1.0)
        return max(0.0, min(1.0, 0.30 * ls + 0.35 * cs + 0.35 * hs))

    def _stability_score(seq):
        ii = _instability_index(seq)
        if ii <= 0: return 1.0
        if ii >= 80: return 0.0
        return max(0.0, 1.0 - ii / 80.0)

    def _synthesizability_score(seq):
        score = 1.0
        if len(seq) > 30: score -= min((len(seq) - 30) / 20, 0.4)
        cys = seq.count("C")
        if cys > 2: score -= min((cys - 2) * 0.1, 0.3)
        if "PP" in seq: score -= 0.15
        if "PPP" in seq: score -= 0.10
        rare = sum(1 for aa in seq if aa in "MW")
        if rare > 3: score -= min((rare - 3) * 0.05, 0.2)
        return max(0.0, min(1.0, score))

    records = []
    errors = 0
    n_total = len(df)

    for idx, (_, row) in enumerate(df.iterrows()):
        seq = row["sequence"]
        try:
            act = max(0.0, min(1.0, row["amp_probability"]))
            hemo = _hemolytic_score(seq)
            phyto = _phytotoxicity_score(seq)
            stab = _stability_score(seq)
            synth = _synthesizability_score(seq)
            comb = (W_ACTIVITY * act + W_HEMOLYTIC * (1 - hemo) +
                    W_PHYTO * (1 - phyto) + W_STABILITY * stab + W_SYNTH * synth)
            records.append({
                "id": row["id"],
                "sequence": seq,
                "length": len(seq),
                "charge": round(_net_charge(seq), 2),
                "activity_score": round(act, 4),
                "hemolytic_score": round(hemo, 4),
                "phytotoxicity_score": round(phyto, 4),
                "stability_score": round(stab, 4),
                "synthesizability_score": round(synth, 4),
                "combined_score": round(comb, 4),
            })
        except Exception as e:
            errors += 1
            if errors <= 3:
                log.warning(f"  Scoring error for {seq[:20]}...: {e}")

        if (idx + 1) % 1000 == 0:
            log.info(f"    Scored {idx + 1}/{n_total}")

    result = pd.DataFrame(records)
    result = result.sort_values("combined_score", ascending=False).reset_index(drop=True)
    result["rank"] = result.index + 1

    if errors > 0:
        log.warning(f"  {errors} sequences failed scoring")

    return result


def phase5_scoring(candidates_df: pd.DataFrame) -> pd.DataFrame:
    """Score all candidates with multi-dimensional ranking."""
    log.info("PHASE 5: Multi-dimensional scoring")
    t0 = time.time()

    scored = score_all_candidates_inline(candidates_df)

    SCORING_OUTPUT.mkdir(parents=True, exist_ok=True)
    scored.to_csv(SCORING_OUTPUT / "scored_all_v2.csv", index=False)
    top20 = scored.head(20)
    top20.to_csv(SCORING_OUTPUT / "top_candidates_v2.csv", index=False)

    log.info(f"  Scored {len(scored)} candidates")
    log.info(f"  Top 5:")
    for _, row in top20.head(5).iterrows():
        log.info(f"    {row['id']} | {row['sequence'][:35]:35s} | "
                 f"combined={row['combined_score']:.4f} "
                 f"activity={row['activity_score']:.4f}")
    log.info(f"  Phase 5 done in {elapsed(t0)}")

    return scored


# =========================================================================
# PHASE 6: Summary & Save
# =========================================================================
def phase6_summary(scored_df: pd.DataFrame):
    """Print summary and save final outputs."""
    log.info("=" * 70)
    log.info("FINAL SUMMARY")
    log.info("=" * 70)

    n_total = len(scored_df)
    if n_total == 0:
        log.warning("  No candidates to summarize")
        return

    strong = len(scored_df[scored_df["combined_score"] > 0.70])
    viable = len(scored_df[scored_df["combined_score"] > 0.60])
    hemo_safe = len(scored_df[scored_df["hemolytic_score"] < 0.5])
    stable = len(scored_df[scored_df["stability_score"] > 0.5])

    log.info(f"  Total candidates:     {n_total}")
    log.info(f"  Strong (>0.70):       {strong}/{n_total} ({100*strong/n_total:.0f}%)")
    log.info(f"  Viable (>0.60):       {viable}/{n_total} ({100*viable/n_total:.0f}%)")
    log.info(f"  Hemolytic-safe:       {hemo_safe}/{n_total} ({100*hemo_safe/n_total:.0f}%)")
    log.info(f"  Stable:               {stable}/{n_total} ({100*stable/n_total:.0f}%)")
    log.info(f"  Top score:            {scored_df['combined_score'].max():.4f}")
    log.info(f"  Mean combined score:  {scored_df['combined_score'].mean():.4f}")

    log.info("\n  Top 10 candidates:")
    for _, row in scored_df.head(10).iterrows():
        log.info(f"    #{row['rank']:2d} {row['id']} | {row['sequence']:35s} | "
                 f"combined={row['combined_score']:.4f} act={row['activity_score']:.4f}")

    # Copy v2 files as main files for the app
    import shutil
    try:
        v2_candidates = MODELS_DIR / "generated_candidates_v2.csv"
        v2_scored = SCORING_OUTPUT / "scored_all_v2.csv"
        v2_top = SCORING_OUTPUT / "top_candidates_v2.csv"

        if v2_candidates.exists():
            shutil.copy(v2_candidates, MODELS_DIR / "generated_candidates.csv")
        if v2_scored.exists():
            shutil.copy(v2_scored, SCORING_OUTPUT / "scored_all.csv")
        if v2_top.exists():
            shutil.copy(v2_top, SCORING_OUTPUT / "top_candidates.csv")
        log.info("  Updated main output files with v2 results")
    except Exception as e:
        log.warning(f"  Could not update main files: {e}")


# =========================================================================
# MAIN
# =========================================================================
def main():
    setup_logging()
    set_seed(CFG.seed)
    total_start = time.time()

    log.info("=" * 70)
    log.info("AgroShield Intensive Training Pipeline v2")
    log.info("=" * 70)
    log.info(f"Device: {CFG.device}")
    if torch.cuda.is_available():
        log.info(f"GPU: {torch.cuda.get_device_name()}")
        log.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    log.info("")

    state = load_pipeline_state()

    # Phase 1: Data acquisition
    if state.get("phase1_complete"):
        log.info("Phase 1 already complete, loading cached data...")
        training_data = pd.read_csv(DATA_DIR / "training_data_v2.csv")
        positive_seqs = training_data[training_data["label"] == 1]["sequence"].tolist()
        negative_seqs = training_data[training_data["label"] == 0]["sequence"].tolist()
    else:
        try:
            positive_seqs, negative_seqs = phase1_data_acquisition()
            state["phase1_complete"] = True
            save_pipeline_state(state)
        except Exception as e:
            log.error(f"Phase 1 failed: {e}\n{traceback.format_exc()}")
            log.info("Falling back to existing dataset with synthetic negatives")
            existing = pd.read_csv(DATA_DIR / "amps_unified.csv")
            positive_seqs = existing["sequence"].tolist()
            negative_seqs = generate_shuffled_negatives(positive_seqs, len(positive_seqs), CFG.seed)

    log.info(f"  Dataset: {len(positive_seqs)} positives, {len(negative_seqs)} negatives")

    # Phase 2: Fine-tune ESM-2 3B
    if state.get("phase2_complete"):
        log.info("Phase 2 already complete, loading model...")
        tokenizer = AutoTokenizer.from_pretrained(CFG.finetune_model_name)
        model = ESM2Classifier(
            CFG.finetune_model_name, CFG.classifier_hidden, CFG.classifier_dropout
        )
        ckpt = torch.load(MODELS_DIR / "esm2_amp_classifier.pt",
                          map_location=CFG.device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        model.to(CFG.device)
        model.eval()
    else:
        try:
            model, tokenizer = phase2_finetune(positive_seqs, negative_seqs)
            state["phase2_complete"] = True
            save_pipeline_state(state)
        except Exception as e:
            log.error(f"Phase 2 failed: {e}\n{traceback.format_exc()}")
            log.info("Cannot continue without classifier")
            sys.exit(1)

    gc.collect()
    torch.cuda.empty_cache()

    # Phase 3: Multi-round evolution
    if state.get("phase3_complete"):
        log.info("Phase 3 already complete, loading candidates...")
        candidates_df = pd.read_csv(MODELS_DIR / "generated_candidates_v2.csv")
    else:
        try:
            candidates_df = phase3_evolution(model, tokenizer, positive_seqs)
            state["phase3_complete"] = True
            save_pipeline_state(state)
        except Exception as e:
            log.error(f"Phase 3 failed: {e}\n{traceback.format_exc()}")
            if (MODELS_DIR / "generated_candidates.csv").exists():
                candidates_df = pd.read_csv(MODELS_DIR / "generated_candidates.csv")
            else:
                log.error("No candidates available, exiting")
                sys.exit(1)

    # Free classifier from GPU for embedding phase
    del model
    gc.collect()
    torch.cuda.empty_cache()

    # Phase 4: Diversity filtering
    if state.get("phase4_complete"):
        log.info("Phase 4 already complete, loading filtered candidates...")
        filtered_path = MODELS_DIR / "candidates_filtered_v2.csv"
        if filtered_path.exists():
            candidates_df = pd.read_csv(filtered_path)
    else:
        try:
            candidates_df = phase4_diversity_filter(candidates_df)
            candidates_df.to_csv(MODELS_DIR / "candidates_filtered_v2.csv", index=False)
            state["phase4_complete"] = True
            save_pipeline_state(state)
        except Exception as e:
            log.error(f"Phase 4 failed (non-critical): {e}\n{traceback.format_exc()}")
            log.info("Continuing with unfiltered candidates")

    # Phase 5: Scoring
    try:
        scored_df = phase5_scoring(candidates_df)
    except Exception as e:
        log.error(f"Phase 5 failed: {e}\n{traceback.format_exc()}")
        scored_df = candidates_df

    # Phase 6: Summary
    try:
        phase6_summary(scored_df)
    except Exception:
        pass

    log.info(f"\nTotal runtime: {elapsed(total_start)}")
    log.info("Done! Check train_overnight.log for full details.")


if __name__ == "__main__":
    main()

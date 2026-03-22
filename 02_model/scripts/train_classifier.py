"""Train AMP vs non-AMP binary classifier on ESM-2 embeddings."""
from __future__ import annotations

import random
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

from .embeddings import generate_embeddings, get_esm2_model, load_cache

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
CLASSIFIER_FILE = "amp_classifier.joblib"
VALID_AAS = list("ACDEFGHIKLMNPQRSTVWY")
RANDOM_STATE = 42


def generate_negative_sequences(
    positive_sequences: list[str],
    n_negatives: int | None = None,
    seed: int = RANDOM_STATE,
) -> list[str]:
    """Generate negative (non-AMP) sequences by shuffling positives + random peptides."""
    rng = random.Random(seed)
    n = n_negatives or len(positive_sequences)

    negatives: list[str] = []

    # Half from shuffled real AMPs
    n_shuffled = n // 2
    for seq in rng.choices(positive_sequences, k=n_shuffled):
        chars = list(seq)
        rng.shuffle(chars)
        negatives.append("".join(chars))

    # Half from random peptides with similar length distribution
    lengths = [len(s) for s in positive_sequences]
    n_random = n - n_shuffled
    for _ in range(n_random):
        length = rng.choice(lengths)
        seq = "".join(rng.choices(VALID_AAS, k=length))
        negatives.append(seq)

    return negatives


def prepare_training_data(
    cache_path: Path | None = None,
    tokenizer=None,
    model=None,
) -> tuple[np.ndarray, np.ndarray]:
    """Prepare X (embeddings) and y (labels) for training."""
    cache = load_cache(cache_path)
    positive_embeddings = cache["embeddings"]
    positive_sequences = cache["sequences"].tolist()
    n_pos = len(positive_sequences)

    # Generate negatives
    neg_sequences = generate_negative_sequences(positive_sequences)

    # Embed negatives
    if tokenizer is None or model is None:
        tokenizer, model = get_esm2_model()
    neg_embeddings = generate_embeddings(neg_sequences, tokenizer, model)

    # Combine
    X = np.vstack([positive_embeddings, neg_embeddings])
    y = np.concatenate([np.ones(n_pos), np.zeros(len(neg_sequences))])

    return X, y


def train_classifier(
    X: np.ndarray,
    y: np.ndarray,
    test_size: float = 0.2,
) -> tuple[RandomForestClassifier, dict]:
    """Train RandomForest classifier and return model + metrics."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=RANDOM_STATE
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred),
        "recall": recall_score(y_test, y_pred),
        "f1": f1_score(y_test, y_pred),
        "auc_roc": roc_auc_score(y_test, y_prob),
    }

    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(clf, X, y, cv=cv, scoring="roc_auc")
    metrics["cv_auc_mean"] = cv_scores.mean()
    metrics["cv_auc_std"] = cv_scores.std()

    return clf, metrics


def save_classifier(clf: RandomForestClassifier, path: Path | None = None) -> Path:
    """Save trained classifier."""
    out = path or MODELS_DIR / CLASSIFIER_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, out)
    return out


def load_classifier(path: Path | None = None) -> RandomForestClassifier:
    """Load trained classifier."""
    p = path or MODELS_DIR / CLASSIFIER_FILE
    return joblib.load(p)


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("Preparing training data...")
    tokenizer, model = get_esm2_model()
    X, y = prepare_training_data(tokenizer=tokenizer, model=model)
    print(f"  Positive: {int(y.sum())}, Negative: {int(len(y) - y.sum())}")

    print("Training classifier...")
    clf, metrics = train_classifier(X, y)

    print("Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    out = save_classifier(clf)
    print(f"Saved classifier to {out}")


if __name__ == "__main__":
    main()

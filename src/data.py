"""
data.py
-------
Data loading and preprocessing utilities for the ECG5000 dataset.

ECG5000 contains 5,000 single-channel heartbeat segments (140 time steps
each), split into 500 training and 4,500 test samples. Labels are binary:
  0 = Normal sinus rhythm
  1 = Anomaly (any of the five arrhythmia subtypes)
"""

import os
import numpy as np
from sklearn.model_selection import train_test_split


# ── Public API ────────────────────────────────────────────────────────────────

def load_ecg5000(data_dir="data", source="auto"):
    """
    Load the ECG5000 dataset.

    Args:
        data_dir : Directory containing ECG5000_TRAIN.txt / ECG5000_TEST.txt.
                   Only used when source='local' or aeon is unavailable.
        source   : 'auto'  — tries aeon first, falls back to local files.
                   'aeon'  — forces aeon (must be installed).
                   'local' — forces local .txt files.

    Returns:
        X_train (500,  140, 1) float32
        y_train (500,)        int   {0 = Normal, 1 = Anomaly}
        X_test  (4500, 140, 1) float32
        y_test  (4500,)       int
    """
    if source == "aeon":
        return _load_from_aeon()

    if source == "local":
        return _load_from_files(data_dir)

    # auto: prefer aeon, fall back to local files
    if _aeon_available():
        print("Loading ECG5000 via aeon...")
        return _load_from_aeon()

    print("aeon not found — loading ECG5000 from local files...")
    return _load_from_files(data_dir)


def compute_class_weights(y_train):
    """
    Compute inverse-frequency class weights.

    Formula: w_k = N / (K * N_k)

    Args:
        y_train : Integer label array.

    Returns:
        dict  {class_index: weight}
    """
    n_total   = len(y_train)
    n_classes = len(np.unique(y_train))
    weights   = {}
    for cls in range(n_classes):
        n_cls        = int(np.sum(y_train == cls))
        weights[cls] = n_total / (n_classes * n_cls)
    return weights


def get_verification_subset(X_test, y_test, n_samples=1000, seed=42):
    """
    Draw a stratified subset from the test set for hardware validation.

    Using a fixed subset ensures the software and hardware models are
    evaluated on identical samples, making the SW-HW comparison fair.

    Args:
        X_test    : Full test features  (N, T, 1).
        y_test    : Full test labels    (N,).
        n_samples : Number of samples in the subset.
        seed      : Random seed for reproducibility.

    Returns:
        X_verify (n_samples, T, 1), y_verify (n_samples,)
    """
    _, X_verify, _, y_verify = train_test_split(
        X_test, y_test,
        test_size=n_samples,
        stratify=y_test,
        random_state=seed
    )
    return X_verify, y_verify


def print_dataset_stats(y_train, y_test):
    """Print class distribution for training and test splits."""
    print("\nDataset Statistics")
    print("=" * 44)
    for split_name, y in [("Train", y_train), ("Test ", y_test)]:
        n       = len(y)
        n_norm  = int(np.sum(y == 0))
        n_anom  = int(np.sum(y == 1))
        print(f"  {split_name} : {n:>5} samples")
        print(f"    Normal  (0) : {n_norm:>4}  ({100 * n_norm / n:.1f}%)")
        print(f"    Anomaly (1) : {n_anom:>4}  ({100 * n_anom / n:.1f}%)")
    print()


# ── Private helpers ───────────────────────────────────────────────────────────

def _aeon_available():
    try:
        import aeon  # noqa: F401
        return True
    except ImportError:
        return False


def _load_from_aeon():
    """
    Load ECG5000 using the aeon time-series library.

    aeon returns X of shape (N, n_channels, T).
    We transpose to (N, T, n_channels) to match Keras Conv1D / Dense input.
    """
    from aeon.datasets import load_classification

    X_train_raw, y_train_str = load_classification("ECG5000", split="train")
    X_test_raw,  y_test_str  = load_classification("ECG5000", split="test")

    # (N, 1, 140) → (N, 140, 1)
    X_train = X_train_raw.transpose(0, 2, 1).astype(np.float32)
    X_test  = X_test_raw.transpose(0, 2, 1).astype(np.float32)

    # String labels "1"–"5" → binary int {0, 1}
    # Original label "1" = Normal; "2"–"5" = Anomaly subtypes
    y_train = _to_binary(y_train_str)
    y_test  = _to_binary(y_test_str)

    return X_train, y_train, X_test, y_test


def _load_from_files(data_dir):
    """
    Load ECG5000 from the plain-text UCR archive files.

    File format: first column = class label (1–5), remaining 140 columns
    are the time-series values.
    """
    train_path = os.path.join(data_dir, "ECG5000_TRAIN.txt")
    test_path  = os.path.join(data_dir, "ECG5000_TEST.txt")

    if not os.path.exists(train_path):
        raise FileNotFoundError(
            f"ECG5000 training file not found at '{train_path}'.\n"
            "Download from: https://www.cs.ucr.edu/~eamonn/time_series_data_2018/"
        )

    train_data = np.loadtxt(train_path)
    test_data  = np.loadtxt(test_path)

    X_train = train_data[:, 1:].reshape(-1, 140, 1).astype(np.float32)
    X_test  = test_data[:, 1:].reshape(-1, 140, 1).astype(np.float32)

    # Class 1 → Normal (0); Classes 2-5 → Anomaly (1)
    y_train = np.where(train_data[:, 0].astype(int) == 1, 0, 1)
    y_test  = np.where(test_data[:, 0].astype(int)  == 1, 0, 1)

    return X_train, y_train, X_test, y_test


def _to_binary(y_str):
    """Convert string UCR labels to binary int array {0 = Normal, 1 = Anomaly}."""
    y_int = y_str.astype(int) if y_str.dtype != object else np.array(
        [int(v) for v in y_str]
    )
    return np.where(y_int == 1, 0, 1).astype(int)

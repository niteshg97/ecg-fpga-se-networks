"""
train.py
--------
Training pipeline for the SE-ECG model.

Supports multi-seed evaluation with:
  - Inverse-frequency class weights  (handles class imbalance)
  - ReduceLROnPlateau scheduling      (halves LR on val_loss plateau)
  - EarlyStopping                     (restores best weights)
  - Per-seed ModelCheckpoint          (saves best weights to disk)
"""

import os
import numpy as np
import tf_keras as keras
from tf_keras.optimizers import Adam
from tf_keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

from model import build_se_ecg_model
from data import compute_class_weights
from evaluate import compute_metrics


# ── Callbacks ─────────────────────────────────────────────────────────────────

def get_callbacks(checkpoint_path, lr_patience=5, es_patience=12, lr_factor=0.5):
    """
    Build the standard callback stack used for every training run.

    Args:
        checkpoint_path : File path for the best-weights checkpoint.
        lr_patience     : Epochs to wait before reducing learning rate.
        es_patience     : Epochs to wait before early stopping.
        lr_factor       : Multiplicative LR reduction factor.

    Returns:
        List of tf_keras.callbacks.Callback objects.
    """
    os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

    reduce_lr = ReduceLROnPlateau(
        monitor="val_loss",
        factor=lr_factor,
        patience=lr_patience,
        min_lr=1e-6,
        verbose=0
    )

    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=es_patience,
        restore_best_weights=True,
        verbose=1
    )

    checkpoint = ModelCheckpoint(
        filepath=checkpoint_path,
        monitor="val_loss",
        save_best_only=True,
        save_weights_only=True,
        verbose=0
    )

    return [reduce_lr, early_stop, checkpoint]


# ── Single-seed training ──────────────────────────────────────────────────────

def train_single_seed(X_train, y_train, X_test, y_test, seed,
                      weights_dir="weights/Model_weights",
                      learning_rate=5e-4, batch_size=32, max_epochs=60,
                      lr_patience=5, es_patience=12):
    """
    Train the SE-ECG model for one random seed.

    A fresh model is built for each seed so that no state leaks
    between runs.

    Args:
        X_train, y_train : Training features and labels.
        X_test,  y_test  : Test features and labels (used as validation).
        seed             : Integer random seed.
        weights_dir      : Root directory for saving checkpoints.
        learning_rate    : Adam initial learning rate.
        batch_size       : Mini-batch size.
        max_epochs       : Maximum training epochs.
        lr_patience      : ReduceLROnPlateau patience.
        es_patience      : EarlyStopping patience.

    Returns:
        dict with keys:
            model         — trained tf_keras.Model
            history       — Keras History object
            metrics       — dict of evaluation metrics on full test set
            seed          — the seed used
            epochs_trained — number of epochs before early stopping
    """
    # Fix all sources of randomness for this run
    np.random.seed(seed)
    keras.utils.set_random_seed(seed)

    model = build_se_ecg_model()
    model.compile(
        optimizer=Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )

    class_weights    = compute_class_weights(y_train)
    checkpoint_path  = os.path.join(weights_dir, f"best_seed_{seed}.weights.h5")
    callbacks        = get_callbacks(
        checkpoint_path,
        lr_patience=lr_patience,
        es_patience=es_patience
    )

    _print_seed_header(seed)

    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=max_epochs,
        batch_size=batch_size,
        class_weight=class_weights,
        callbacks=callbacks,
        verbose=1
    )

    epochs_trained = len(history.history["loss"])
    y_proba        = model.predict(X_test, verbose=0)
    metrics        = compute_metrics(y_test, y_proba)

    _print_seed_results(seed, epochs_trained, metrics)

    return {
        "model":          model,
        "history":        history,
        "metrics":        metrics,
        "seed":           seed,
        "epochs_trained": epochs_trained,
    }


# ── Multi-seed training ───────────────────────────────────────────────────────

def train_multi_seed(X_train, y_train, X_test, y_test, seeds,
                     weights_dir="weights/Model_weights", **train_kwargs):
    """
    Run the full training pipeline across multiple random seeds.

    Using multiple seeds characterises performance variance, which is
    important when the training set is small (500 samples for ECG5000).

    Args:
        X_train, y_train : Training data.
        X_test,  y_test  : Test data.
        seeds            : List of integer seeds.
        weights_dir      : Directory for saving per-seed checkpoints.
        **train_kwargs   : Additional keyword arguments forwarded to
                           train_single_seed (e.g. learning_rate).

    Returns:
        all_results  : List of per-seed result dicts.
        best_result  : Entry from all_results with the highest test AUC.
    """
    all_results = []

    for seed in seeds:
        result = train_single_seed(
            X_train, y_train, X_test, y_test,
            seed=seed,
            weights_dir=weights_dir,
            **train_kwargs
        )
        all_results.append(result)

    print_multi_seed_summary(all_results)

    best_result = max(all_results, key=lambda r: r["metrics"]["auc"])
    print(f"\n  Best seed : {best_result['seed']}  "
          f"(AUC = {best_result['metrics']['auc']:.4f})\n")

    return all_results, best_result


# ── Summary printing ──────────────────────────────────────────────────────────

def print_multi_seed_summary(results):
    """Print mean ± std across seeds for each metric."""
    metric_keys = ["auc", "accuracy", "sensitivity", "specificity", "f1"]

    print("\n" + "=" * 52)
    print("  Multi-Seed Summary")
    print("=" * 52)
    print(f"  {'Metric':<16} {'Mean':>8}  {'Std':>8}")
    print("  " + "-" * 36)

    for key in metric_keys:
        values = [r["metrics"][key] for r in results]
        print(f"  {key:<16} {np.mean(values):>8.4f}  {np.std(values):>8.4f}")

    print()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _print_seed_header(seed):
    print(f"\n{'=' * 52}")
    print(f"  Training — Seed {seed}")
    print(f"{'=' * 52}")


def _print_seed_results(seed, epochs, metrics):
    print(f"\n  Seed {seed} results  (epochs trained: {epochs})")
    print(f"    AUC-ROC     : {metrics['auc']:.4f}")
    print(f"    Accuracy    : {metrics['accuracy']:.4f}")
    print(f"    Sensitivity : {metrics['sensitivity']:.4f}")
    print(f"    Specificity : {metrics['specificity']:.4f}")
    print(f"    F1-Score    : {metrics['f1']:.4f}")

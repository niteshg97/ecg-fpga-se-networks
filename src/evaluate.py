"""
evaluate.py
-----------
Evaluation metrics and visualization for the SE-ECG pipeline.

Metrics
-------
  AUC-ROC, Accuracy, Sensitivity (Recall), Specificity,
  F1-Score, Precision, Logic Fidelity (SW-HW agreement rate)

Figures produced
----------------
  fig_training_curves.png    — multi-seed training dynamics
  fig_sw_evaluation.png      — ROC curve + SW confusion matrix
  fig_confusion_matrices.png — SW vs HW confusion matrices side-by-side
  fig_sw_hw_agreement.png    — prediction agreement bar chart
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import (
    roc_auc_score, accuracy_score, confusion_matrix,
    f1_score, precision_score, roc_curve
)


# ── Core metrics ──────────────────────────────────────────────────────────────

def compute_metrics(y_true, y_proba):
    """
    Compute all classification metrics from labels and predicted probabilities.

    Args:
        y_true  : Ground-truth binary labels, shape (N,).
        y_proba : Predicted probabilities, shape (N, 2) or (N,) for class 1.

    Returns:
        dict with keys: auc, accuracy, sensitivity, specificity, f1, precision.
    """
    if np.ndim(y_proba) == 2:
        p_anomaly = y_proba[:, 1]
        y_pred    = np.argmax(y_proba, axis=1)
    else:
        p_anomaly = y_proba
        y_pred    = (y_proba >= 0.5).astype(int)

    cm = confusion_matrix(y_true, y_pred)

    # Guard against edge case where a class is missing from predictions
    if cm.shape == (2, 2):
        tn, fp, fn, tp = cm.ravel()
    else:
        tn = fp = fn = tp = 0

    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return {
        "auc":         float(roc_auc_score(y_true, p_anomaly)),
        "accuracy":    float(accuracy_score(y_true, y_pred)),
        "sensitivity": float(sensitivity),
        "specificity": float(specificity),
        "f1":          float(f1_score(y_true, y_pred, zero_division=0)),
        "precision":   float(precision_score(y_true, y_pred, zero_division=0)),
    }


def compute_logic_fidelity(y_pred_sw, y_pred_hw):
    """
    Compute the SW-HW prediction agreement rate (logic fidelity).

    Logic fidelity = fraction of samples where the software and hardware
    models produce identical class predictions.

    Args:
        y_pred_sw : Class predictions from the software model, shape (N,).
        y_pred_hw : Class predictions from the hardware model, shape (N,).

    Returns:
        fidelity        : Float in [0, 1].
        n_disagreements : Integer count of mismatched predictions.
    """
    n_total       = len(y_pred_sw)
    n_disagree    = int(np.sum(y_pred_sw != y_pred_hw))
    fidelity      = 1.0 - n_disagree / n_total
    return fidelity, n_disagree


# ── Figures ───────────────────────────────────────────────────────────────────

def plot_training_curves(all_results, save_path=None):
    """
    Plot validation accuracy and loss curves for all seeds.

    Args:
        all_results : List of per-seed result dicts (from train_multi_seed).
        save_path   : File path to save the figure. Shows interactively if None.
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    colors    = plt.cm.tab10(np.linspace(0, 0.9, len(all_results)))

    for result, color in zip(all_results, colors):
        seed    = result["seed"]
        hist    = result["history"].history
        epochs  = range(1, len(hist["loss"]) + 1)
        label   = f"Seed {seed}"

        axes[0].plot(epochs, hist["val_accuracy"], color=color, label=label, lw=1.8)
        axes[1].plot(epochs, hist["val_loss"],     color=color, label=label, lw=1.8)

    for ax, title, ylabel in zip(
        axes,
        ["Validation Accuracy", "Validation Loss"],
        ["Accuracy", "Loss"]
    ):
        ax.set_xlabel("Epoch", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    plt.suptitle("Multi-Seed Training Dynamics", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    _save_or_show(fig, save_path)


def plot_roc_curve(y_true, y_proba, title="ROC Curve", save_path=None):
    """
    Plot the ROC curve with AUC annotation.

    Args:
        y_true   : Ground-truth labels (N,).
        y_proba  : Predicted probabilities (N, 2) or (N,).
        title    : Plot title string.
        save_path: Save path or None to display.

    Returns:
        auc : Float AUC-ROC value.
    """
    p_anomaly = y_proba[:, 1] if np.ndim(y_proba) == 2 else y_proba
    fpr, tpr, _ = roc_curve(y_true, p_anomaly)
    auc         = roc_auc_score(y_true, p_anomaly)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(fpr, tpr, color="#2c7bb6", lw=2.2, label=f"AUC = {auc:.4f}")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.fill_between(fpr, tpr, alpha=0.08, color="#2c7bb6")
    ax.set_xlabel("False Positive Rate", fontsize=11)
    ax.set_ylabel("True Positive Rate", fontsize=11)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.legend(loc="lower right", fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    _save_or_show(fig, save_path)

    return auc


def plot_confusion_matrix(y_true, y_pred, ax, title="Confusion Matrix",
                          labels=("Normal", "Anomaly")):
    """
    Draw a labelled confusion matrix on a given Axes object.

    Args:
        y_true : Ground-truth labels.
        y_pred : Predicted labels.
        ax     : matplotlib Axes to draw on.
        title  : Subplot title.
        labels : Class name strings.
    """
    cm     = confusion_matrix(y_true, y_pred)
    im     = ax.imshow(cm, cmap="Blues", vmin=0)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("Predicted", fontsize=10)
    ax.set_ylabel("True", fontsize=10)
    ax.set_title(title, fontsize=11, fontweight="bold")

    thresh = cm.max() / 2.0
    for i in range(2):
        for j in range(2):
            ax.text(
                j, i, f"{cm[i, j]}",
                ha="center", va="center", fontsize=13,
                color="white" if cm[i, j] > thresh else "black"
            )


def plot_confusion_matrices(y_true, y_pred_sw, y_pred_hw, save_path=None):
    """
    Plot SW and HW confusion matrices side-by-side.

    Args:
        y_true    : Ground-truth labels.
        y_pred_sw : Software model predicted labels.
        y_pred_hw : Hardware model predicted labels.
        save_path : Save path or None to display.
    """
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    plot_confusion_matrix(y_true, y_pred_sw, axes[0], title="SW (float32)")
    plot_confusion_matrix(y_true, y_pred_hw, axes[1], title="HW (ap_fixed<24,12>)")

    plt.suptitle("Software vs. Hardware Confusion Matrices",
                 fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    _save_or_show(fig, save_path)


def plot_sw_evaluation(y_true, y_proba_sw, save_path=None):
    """
    Plot ROC curve and software confusion matrix side-by-side.

    Args:
        y_true      : Ground-truth labels (N,).
        y_proba_sw  : Software model probabilities (N, 2).
        save_path   : Save path or None to display.
    """
    p_anomaly   = y_proba_sw[:, 1]
    y_pred_sw   = np.argmax(y_proba_sw, axis=1)
    fpr, tpr, _ = roc_curve(y_true, p_anomaly)
    auc         = roc_auc_score(y_true, p_anomaly)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # ROC curve
    axes[0].plot(fpr, tpr, color="#2c7bb6", lw=2.2, label=f"AUC = {auc:.4f}")
    axes[0].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    axes[0].fill_between(fpr, tpr, alpha=0.08, color="#2c7bb6")
    axes[0].set_xlabel("False Positive Rate", fontsize=11)
    axes[0].set_ylabel("True Positive Rate", fontsize=11)
    axes[0].set_title("ROC Curve — Software Model", fontsize=11, fontweight="bold")
    axes[0].legend(loc="lower right", fontsize=11)
    axes[0].grid(True, alpha=0.3)

    # Confusion matrix
    plot_confusion_matrix(y_true, y_pred_sw, axes[1], title="SW Confusion Matrix")

    plt.tight_layout()
    _save_or_show(fig, save_path)


def plot_sw_hw_agreement(y_pred_sw, y_pred_hw, save_path=None):
    """
    Bar chart showing how many samples SW and HW models agree / disagree on.

    Args:
        y_pred_sw : SW class predictions (N,).
        y_pred_hw : HW class predictions (N,).
        save_path : Save path or None to display.
    """
    n_agree    = int(np.sum(y_pred_sw == y_pred_hw))
    n_disagree = len(y_pred_sw) - n_agree
    fidelity   = n_agree / len(y_pred_sw)

    fig, ax = plt.subplots(figsize=(5, 4))
    bars = ax.bar(
        ["Disagree", "Agree"],
        [n_disagree, n_agree],
        color=["#e74c3c", "#2ecc71"],
        width=0.45,
        edgecolor="white",
        linewidth=1.2
    )

    for bar, count in zip(bars, [n_disagree, n_agree]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(n_agree, n_disagree) * 0.02,
            str(count),
            ha="center", va="bottom", fontsize=12, fontweight="bold"
        )

    ax.set_ylabel("Number of Samples", fontsize=11)
    ax.set_title(
        f"SW–HW Prediction Agreement\nLogic Fidelity = {fidelity:.4f}",
        fontsize=11, fontweight="bold"
    )
    ax.set_ylim(0, max(n_agree, n_disagree) * 1.18)
    ax.grid(axis="y", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    _save_or_show(fig, save_path)


# ── Console reporting ─────────────────────────────────────────────────────────

def print_sw_hw_comparison(sw_metrics, hw_metrics, fidelity, n_disagree):
    """Print a formatted software-vs-hardware comparison table."""
    keys = ["auc", "accuracy", "sensitivity", "specificity", "f1"]
    w    = 58

    print("\n" + "=" * w)
    print("  Software vs. Hardware Comparison")
    print("=" * w)
    print(f"  {'Metric':<16} {'SW (float32)':>14} {'HW ap_fixed':>14} {'Δ':>8}")
    print("  " + "-" * (w - 2))

    for key in keys:
        sw  = sw_metrics[key]
        hw  = hw_metrics[key]
        d   = hw - sw
        sgn = "+" if d >= 0 else ""
        print(f"  {key:<16} {sw:>14.4f} {hw:>14.4f} {sgn}{d:>7.4f}")

    print("  " + "-" * (w - 2))
    print(f"  {'Logic Fidelity':<16} {'—':>14} {fidelity:>14.4f}")
    print(f"  {'Disagreements':<16} {'—':>14} {n_disagree:>14d}")
    print("=" * w + "\n")


# ── Persistence ───────────────────────────────────────────────────────────────

def save_results_json(data, path):
    """
    Serialise the results dictionary to a JSON file.

    Args:
        data : dict — must contain only JSON-serialisable values.
        path : Destination file path.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Results saved → {path}")


# ── Internal helper ───────────────────────────────────────────────────────────

def _save_or_show(fig, path):
    """Save the figure to disk if path is provided; otherwise display it."""
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"  Figure saved  → {path}")
        plt.close(fig)
    else:
        plt.show()

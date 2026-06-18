"""
main.py
-------
Entry point for the SE-ECG FPGA pipeline.

This script executes the complete research pipeline end-to-end:

  1. Dataset loading  — ECG5000 from disk or aeon repository
  2. Model training   — Multi-seed (5 seeds) SE-ECG with early stopping
  3. SW evaluation    — AUC-ROC, sensitivity, specificity, F1 on test set
  4. HLS conversion   — logit sub-model → Vivado HLS C++ via hls4ml
  5. Precision sweep  — five ap_fixed configurations on 200-sample subset
  6. HW validation    — C-simulation on 1,000-sample stratified subset
  7. Logic fidelity   — agreement rate between SW float32 and HW fixed-point
  8. Figure export    — training curves, ROC, confusion matrices, agreement
  9. Results JSON     — all paper numbers saved to results/paper_numbers.json

Usage
-----
  # Full pipeline (train + sweep + hardware validation)
  python main.py

  # Skip training — load saved weights from weights/ directory
  python main.py --skip-training

  # Skip precision sweep (use PRECISION_MAIN directly)
  python main.py --skip-sweep

  # Also run Vivado RTL synthesis (requires Vivado HLS in PATH)
  python main.py --synth

  # Combine flags
  python main.py --skip-training --skip-sweep

Environment
-----------
  TensorFlow / tf_keras    >= 2.12
  hls4ml                   == 1.3.0   (see note in fpga_deploy.py)
  scikit-learn             >= 1.0
  matplotlib               >= 3.5
  numpy                    >= 1.22
"""

import os
import sys
import json
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")          # non-interactive backend; safe for scripts
import matplotlib.pyplot as plt

# ── Project modules ───────────────────────────────────────────────────────────
import config
import data        as data_module
import model       as model_module
import train       as train_module
import evaluate    as eval_module
import fpga_deploy as fpga_module


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="SE-ECG FPGA pipeline (hls4ml + Vivado HLS)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Load best-seed weights from disk instead of training."
    )
    parser.add_argument(
        "--skip-sweep",
        action="store_true",
        help="Skip fixed-point precision sweep; use PRECISION_MAIN directly."
    )
    parser.add_argument(
        "--synth",
        action="store_true",
        help="Run Vivado HLS RTL synthesis after C-simulation. "
             "Requires Vivado HLS in PATH."
    )
    parser.add_argument(
        "--best-seed-only",
        action="store_true",
        help="Train / evaluate only seed=42 (fastest, single-run mode)."
    )
    return parser.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Directory setup
# ─────────────────────────────────────────────────────────────────────────────

def setup_dirs():
    """Create all output directories if they do not exist."""
    for d in [config.FIGURES_DIR, config.RESULTS_DIR,
              config.WEIGHTS_DIR, config.HLS_DIR]:
        os.makedirs(d, exist_ok=True)
    print(f"Output directories ready:")
    print(f"  Figures  : {config.FIGURES_DIR}")
    print(f"  Results  : {config.RESULTS_DIR}")
    print(f"  Weights  : {config.WEIGHTS_DIR}")
    print(f"  HLS      : {config.HLS_DIR}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Data
# ─────────────────────────────────────────────────────────────────────────────

def step_load_data():
    """Load ECG5000 and print dataset statistics."""
    _section("Step 1 — Dataset Loading")

    X_train, y_train, X_test, y_test = data_module.load_ecg5000()

    print(f"  Train : {X_train.shape}  labels {y_train.shape}")
    print(f"  Test  : {X_test.shape}   labels {y_test.shape}")

    n_normal  = int((y_train == 0).sum())
    n_anomaly = int((y_train == 1).sum())
    print(f"  Class distribution (train): "
          f"Normal={n_normal}  Anomaly={n_anomaly}")

    class_weights = data_module.compute_class_weights(y_train)
    print(f"  Class weights : {class_weights}\n")

    return X_train, y_train, X_test, y_test, class_weights


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Training
# ─────────────────────────────────────────────────────────────────────────────

def step_train(X_train, y_train, X_test, y_test,
               class_weights, args):
    """
    Train SE-ECG model.

    Multi-seed training runs five seeds and records mean ± std metrics.
    The best seed (lowest val_loss) is saved and used for FPGA conversion.

    If --skip-training is set, weights are loaded from disk.

    Returns:
        best_model     : Keras model (best seed).
        train_histories: list of history dicts (one per seed), or [].
        seed_results   : list of per-seed metric dicts, or [].
    """
    _section("Step 2 — Model Training")

    if args.skip_training:
        print("  --skip-training: loading saved weights from disk.")
        best_model = model_module.build_se_ecg_model()
        weights_path = os.path.join(config.WEIGHTS_DIR, "best_model.weights.h5")
        if not os.path.exists(weights_path):
            sys.exit(f"  ERROR: weights file not found at {weights_path}. "
                     "Run without --skip-training first.")
        best_model.load_weights(weights_path)
        print(f"  Loaded weights from {weights_path}\n")
        return best_model, [], []

    seeds = [config.BEST_SEED] if args.best_seed_only else config.SEEDS

    best_model, train_histories, seed_results = (
        train_module.train_multi_seed(
            X_train, y_train, X_test, y_test,
            class_weights=class_weights,
            seeds=seeds
        )
    )

    # Save best-seed weights
    weights_path = os.path.join(config.WEIGHTS_DIR, "best_model.weights.h5")
    best_model.save_weights(weights_path)
    print(f"\n  Best-seed weights saved → {weights_path}")

    return best_model, train_histories, seed_results


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Software evaluation
# ─────────────────────────────────────────────────────────────────────────────

def step_sw_evaluation(best_model, X_test, y_test,
                       train_histories, seed_results):
    """
    Evaluate the best-seed model on the full test set (N=4,500).

    Produces:
      - sw_metrics   : dict of AUC, accuracy, sensitivity, specificity,
                       precision, F1.
      - sw_proba     : Probability array (4500, 2).
      - Figures      : training curves, ROC curve, software confusion matrix.
    """
    _section("Step 3 — Software Performance Evaluation (N=4,500)")

    import tensorflow as tf

    sw_proba  = best_model.predict(X_test, batch_size=config.BATCH_SIZE,
                                   verbose=0)
    sw_metrics = eval_module.compute_metrics(y_test, sw_proba)

    print(f"  AUC-ROC       : {sw_metrics['auc']:.4f}")
    print(f"  Accuracy      : {sw_metrics['accuracy']:.4f}")
    print(f"  Sensitivity   : {sw_metrics['sensitivity']:.4f}")
    print(f"  Specificity   : {sw_metrics['specificity']:.4f}")
    print(f"  Precision     : {sw_metrics['precision_score']:.4f}")
    print(f"  F1            : {sw_metrics['f1']:.4f}\n")

    # ── Figures ──────────────────────────────────────────────────────────────
    if train_histories:
        fig_path = os.path.join(config.FIGURES_DIR, "fig_training_curves.png")
        eval_module.plot_training_curves(train_histories, save_path=fig_path)
        print(f"  Saved training curves → {fig_path}")

    fig_path = os.path.join(config.FIGURES_DIR, "fig_sw_evaluation.png")
    eval_module.plot_sw_evaluation(y_test, sw_proba, save_path=fig_path)
    print(f"  Saved SW ROC / confusion → {fig_path}\n")

    return sw_proba, sw_metrics


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Logit sub-model extraction
# ─────────────────────────────────────────────────────────────────────────────

def step_extract_logit_model(best_model):
    """
    Extract the logit sub-model (Dense(2), no softmax).

    The logit sub-model is what gets converted to HLS C++. Excluding
    the softmax layer sidesteps the hls4ml 1.3.0 C-simulation defect
    where both class probabilities can simultaneously exceed 0.5.

    Returns:
        logit_model : Keras Model ending at the Dense(2) layer.
    """
    _section("Step 4 — Logit Sub-model Extraction")

    logit_model = model_module.extract_logit_model(best_model)
    model_module.print_model_summary(logit_model, title="Logit Sub-model")

    return logit_model


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Fixed-point precision sweep
# ─────────────────────────────────────────────────────────────────────────────

def step_precision_sweep(logit_model, X_test, y_test, args):
    """
    Sweep five ap_fixed precisions on a 200-sample validation subset.

    Returns:
        sweep_results : dict {precision_str: metrics_dict}
    """
    _section("Step 5 — Fixed-Point Precision Sweep")

    if args.skip_sweep:
        print("  --skip-sweep: skipping precision sweep.\n")
        return {}

    # Small stratified subset for fast sweep iteration
    X_sweep, y_sweep = data_module.get_verification_subset(
        X_test, y_test,
        n=config.N_SWEEP,
        seed=config.BEST_SEED
    )
    print(f"  Sweep subset: {X_sweep.shape}  "
          f"(Normal={int((y_sweep==0).sum())}  "
          f"Anomaly={int((y_sweep==1).sum())})\n")

    sweep_dir = os.path.join(config.HLS_DIR, "precision_sweep")
    sweep_results = fpga_module.run_precision_sweep(
        logit_model=logit_model,
        X_verify=X_sweep,
        y_verify=y_sweep,
        precisions=config.PRECISION_SWEEP,
        fpga_part=config.FPGA_PART,
        base_output_dir=sweep_dir,
        reuse_factor=config.REUSE_FACTOR
    )

    return sweep_results


# ─────────────────────────────────────────────────────────────────────────────
# Step 6 — Main HLS conversion (selected precision)
# ─────────────────────────────────────────────────────────────────────────────

def step_hls_conversion(logit_model):
    """
    Convert the logit sub-model to HLS C++ at the selected precision
    (config.PRECISION_MAIN = 'ap_fixed<24,12>') and compile with g++.

    Returns:
        hls_model : Compiled hls4ml model.
    """
    _section("Step 6 — HLS Conversion  "
             f"({config.PRECISION_MAIN}, RF={config.REUSE_FACTOR})")

    hls_output_dir = os.path.join(config.HLS_DIR, "hls_ecg_main")

    hls_model = fpga_module.convert_to_hls(
        logit_model=logit_model,
        precision=config.PRECISION_MAIN,
        output_dir=hls_output_dir,
        fpga_part=config.FPGA_PART,
        reuse_factor=config.REUSE_FACTOR
    )

    return hls_model


# ─────────────────────────────────────────────────────────────────────────────
# Step 7 — Hardware validation
# ─────────────────────────────────────────────────────────────────────────────

def step_hw_validation(hls_model, best_model, X_test, y_test):
    """
    Validate hardware C-simulation against the software model on a
    stratified 1,000-sample subset.

    The subset is drawn with the same seed used for training (seed=42)
    and maintains the same class ratio as the full test set.

    Returns:
        hw_proba    : Hardware probability array (N_VERIFY, 2).
        sw_sub_proba: Software probability array on the same subset.
        hw_metrics  : Hardware performance metrics dict.
        sw_sub_metrics: Software metrics on the same subset.
        fidelity    : Logic fidelity (agreement rate, 0–1).
    """
    _section("Step 7 — Hardware Validation (N=1,000 stratified subset)")

    X_verify, y_verify = data_module.get_verification_subset(
        X_test, y_test,
        n=config.N_VERIFY,
        seed=config.BEST_SEED
    )
    print(f"  Validation subset: {X_verify.shape}  "
          f"(Normal={int((y_verify==0).sum())}  "
          f"Anomaly={int((y_verify==1).sum())})")

    # Software inference on the same subset
    sw_sub_proba   = best_model.predict(X_verify,
                                        batch_size=config.BATCH_SIZE,
                                        verbose=0)
    sw_sub_metrics = eval_module.compute_metrics(y_verify, sw_sub_proba)

    # Hardware C-simulation
    hw_proba   = fpga_module.run_hardware_inference(hls_model, X_verify)
    hw_metrics = eval_module.compute_metrics(y_verify, hw_proba)

    # Logic fidelity
    fidelity = eval_module.compute_logic_fidelity(sw_sub_proba, hw_proba)

    # Console report
    print(f"\n  {'Metric':<18} {'SW (float32)':>14} {'HW (fixed-point)':>18}")
    print("  " + "-" * 54)
    for key in ["auc", "accuracy", "sensitivity", "specificity", "f1"]:
        sw_val = sw_sub_metrics.get(key, 0.0)
        hw_val = hw_metrics.get(key, 0.0)
        print(f"  {key:<18} {sw_val:>14.4f} {hw_val:>18.4f}")
    print(f"\n  Logic fidelity : {fidelity:.4f}  "
          f"({int(round(fidelity * config.N_VERIFY))}/"
          f"{config.N_VERIFY} predictions agree)\n")

    # Figures
    fig_path = os.path.join(config.FIGURES_DIR, "fig_confusion_matrices.png")
    eval_module.plot_confusion_matrices(
        y_verify, sw_sub_proba, hw_proba,
        save_path=fig_path
    )
    print(f"  Saved confusion matrices → {fig_path}")

    fig_path = os.path.join(config.FIGURES_DIR, "fig_sw_hw_agreement.png")
    eval_module.plot_sw_hw_agreement(
        sw_sub_proba, hw_proba,
        save_path=fig_path
    )
    print(f"  Saved SW-HW agreement plot → {fig_path}\n")

    return hw_proba, sw_sub_proba, hw_metrics, sw_sub_metrics, fidelity


# ─────────────────────────────────────────────────────────────────────────────
# Step 8 — RTL synthesis (optional)
# ─────────────────────────────────────────────────────────────────────────────

def step_synthesis(hls_model, args):
    """Run Vivado HLS RTL synthesis if --synth flag is set."""
    if not args.synth:
        return
    _section("Step 8 — Vivado HLS RTL Synthesis")
    fpga_module.synthesize_fpga(hls_model, csim=False, synth=True,
                                export=False)


# ─────────────────────────────────────────────────────────────────────────────
# Step 9 — Save results JSON
# ─────────────────────────────────────────────────────────────────────────────

def step_save_results(sw_metrics, sw_sub_metrics, hw_metrics,
                      fidelity, sweep_results, seed_results):
    """
    Assemble and save all paper numbers to a JSON file.

    The saved JSON mirrors the structure used to verify claims in the
    paper, making it easy to cross-check figures and tables.
    """
    _section("Step 9 — Saving Results")

    results = {
        "software_full_testset_N4500": {k: round(float(v), 6)
                                        for k, v in sw_metrics.items()
                                        if isinstance(v, float)},
        "software_subset_N1000": {k: round(float(v), 6)
                                  for k, v in sw_sub_metrics.items()
                                  if isinstance(v, float)},
        "hardware_N1000": {k: round(float(v), 6)
                           for k, v in hw_metrics.items()
                           if isinstance(v, float)},
        "logic_fidelity": round(float(fidelity), 6),
        "precision_sweep": {
            p: {k: round(float(v), 6)
                for k, v in m.items()
                if isinstance(v, (int, float))}
            for p, m in sweep_results.items()
        },
        "multi_seed_results": [
            {k: (round(float(v), 6) if isinstance(v, float) else v)
             for k, v in sr.items()}
            for sr in seed_results
        ],
        "fpga_config": {
            "part":          config.FPGA_PART,
            "clock_mhz":     config.CLOCK_MHZ,
            "precision":     config.PRECISION_MAIN,
            "reuse_factor":  config.REUSE_FACTOR,
        },
        "analytical_resources": {
            "lut_used":  34475, "lut_total":  53200,
            "ff_used":   18961, "ff_total":  106400,
            "dsp_used":    210, "dsp_total":    220,
            "bram_used":     2, "bram_total":   140,
            "latency_cycles": 197,
            "latency_us":    2.0,
        }
    }

    json_path = os.path.join(config.RESULTS_DIR, "paper_numbers.json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"  Results JSON saved → {json_path}\n")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Final summary
# ─────────────────────────────────────────────────────────────────────────────

def print_final_summary(sw_metrics, sw_sub_metrics, hw_metrics, fidelity):
    """Print a concise final summary of key paper numbers."""
    _section("Final Summary — Key Paper Numbers")

    print(f"  ── Software Performance (N=4,500 full test set) ──────────────")
    print(f"  AUC-ROC        : {sw_metrics.get('auc', 0):.4f}")
    print(f"  Accuracy       : {sw_metrics.get('accuracy', 0):.4f}")
    print(f"  Sensitivity    : {sw_metrics.get('sensitivity', 0):.4f}")
    print(f"  Specificity    : {sw_metrics.get('specificity', 0):.4f}")
    print(f"  F1-Score       : {sw_metrics.get('f1', 0):.4f}")

    print(f"\n  ── SW vs HW Comparison (N=1,000 stratified subset) ──────────")
    print(f"  {'Metric':<16} {'SW':>10} {'HW':>10}")
    print("  " + "-" * 38)
    for k in ["auc", "accuracy", "sensitivity", "specificity", "f1"]:
        sw_v = sw_sub_metrics.get(k, 0.0)
        hw_v = hw_metrics.get(k, 0.0)
        print(f"  {k:<16} {sw_v:>10.4f} {hw_v:>10.4f}")

    print(f"\n  Logic Fidelity : {fidelity:.4f}  "
          f"({int(round(fidelity * config.N_VERIFY))}/{config.N_VERIFY})")

    print(f"\n  ── FPGA Resources (analytical, xc7z020clg400-1) ─────────────")
    print(f"  LUTs  : 34,475 / 53,200  = 64.8%")
    print(f"  FFs   : 18,961 / 106,400 = 17.8%")
    print(f"  DSPs  :    210 / 220      = 95.5%")
    print(f"  BRAMs :      2 / 140      =  1.4%")
    print(f"  Latency : ~197 cycles @ 100 MHz ≈ 2.0 µs")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper
# ─────────────────────────────────────────────────────────────────────────────

def _section(title):
    """Print a clearly delimited section header."""
    bar = "=" * 62
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    _section("SE-ECG FPGA Pipeline  |  hls4ml 1.3.0  |  NIT Patna")
    print(f"  Configuration:")
    print(f"    FPGA part     : {config.FPGA_PART}")
    print(f"    Precision     : {config.PRECISION_MAIN}")
    print(f"    Reuse factor  : {config.REUSE_FACTOR}")
    print(f"    Clock         : {config.CLOCK_MHZ} MHz")
    print(f"    Seeds         : {config.SEEDS}")
    print(f"    Best seed     : {config.BEST_SEED}")
    print(f"    N_verify      : {config.N_VERIFY}")
    print(f"    N_sweep       : {config.N_SWEEP}\n")

    # ── Setup ────────────────────────────────────────────────────────────────
    setup_dirs()

    # ── Step 1 — Data ────────────────────────────────────────────────────────
    X_train, y_train, X_test, y_test, class_weights = step_load_data()

    # ── Step 2 — Training ────────────────────────────────────────────────────
    best_model, train_histories, seed_results = step_train(
        X_train, y_train, X_test, y_test, class_weights, args
    )

    # ── Step 3 — Software evaluation ─────────────────────────────────────────
    sw_proba, sw_metrics = step_sw_evaluation(
        best_model, X_test, y_test, train_histories, seed_results
    )

    # ── Step 4 — Logit sub-model ──────────────────────────────────────────────
    logit_model = step_extract_logit_model(best_model)

    # ── Step 5 — Precision sweep ──────────────────────────────────────────────
    sweep_results = step_precision_sweep(logit_model, X_test, y_test, args)

    # ── Step 6 — HLS conversion ───────────────────────────────────────────────
    hls_model = step_hls_conversion(logit_model)

    # ── Step 7 — Hardware validation ─────────────────────────────────────────
    hw_proba, sw_sub_proba, hw_metrics, sw_sub_metrics, fidelity = (
        step_hw_validation(hls_model, best_model, X_test, y_test)
    )

    # ── Step 8 — RTL synthesis (optional) ────────────────────────────────────
    step_synthesis(hls_model, args)

    # ── Step 9 — Save results ────────────────────────────────────────────────
    step_save_results(
        sw_metrics, sw_sub_metrics, hw_metrics,
        fidelity, sweep_results, seed_results
    )

    # ── Final summary ─────────────────────────────────────────────────────────
    print_final_summary(sw_metrics, sw_sub_metrics, hw_metrics, fidelity)

    _section("Pipeline Complete")
    print(f"  Figures  : {config.FIGURES_DIR}")
    print(f"  Results  : {config.RESULTS_DIR}/paper_numbers.json")
    print(f"  Weights  : {config.WEIGHTS_DIR}/best_model.weights.h5")
    print(f"  HLS C++  : {config.HLS_DIR}/hls_ecg_main\n")


if __name__ == "__main__":
    main()

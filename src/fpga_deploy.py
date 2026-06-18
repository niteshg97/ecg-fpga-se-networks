"""
fpga_deploy.py
--------------
End-to-end FPGA deployment via hls4ml.

Key design decisions
--------------------
1. Keras version override
   hls4ml 1.3.0 inspects keras.__version__ to choose its internal parser.
   Overriding to "2.15.0" forces the stable V2 parser which correctly
   handles Dense, BatchNormalization, GlobalAveragePooling1D, Multiply,
   Add, and Activation layers. Without this, hls4ml uses the experimental
   V3 parser and conversion fails or produces incorrect code.

2. Logit-only conversion
   hls4ml 1.3.0 C-simulation contains a softmax normalization defect:
   both class probabilities can simultaneously exceed 0.5, violating
   sum(p_k) = 1. The fix is to convert only the Dense(2) logit layer
   (no softmax) and apply IEEE-754-compatible softmax in Python
   post-processing via numpy_softmax().

3. Reuse Factor = 1
   Setting ReuseFactor=1 fully unrolls all inner accumulation loops,
   dedicating separate hardware to every weight multiplication. This
   produces the minimum possible inference latency at the cost of
   higher LUT / DSP utilization.
"""

import os
import numpy as np

# ── Keras version override ────────────────────────────────────────────────────
# Must be set BEFORE importing hls4ml. Forces the stable V2 graph parser.
import keras as _keras_compat
_keras_compat.__version__ = "2.15.0"

import hls4ml


# ─────────────────────────────────────────────────────────────────────────────
# Softmax post-processing
# ─────────────────────────────────────────────────────────────────────────────

def numpy_softmax(logits):
    """
    Numerically stable softmax applied in Python after FPGA inference.

    The max-subtraction trick prevents overflow when logit values are
    large. This replaces the defective HLS softmax in hls4ml 1.3.0.

    Args:
        logits : Raw logit array, shape (N, K).

    Returns:
        proba  : Probability array, shape (N, K). Each row sums to 1.0.
    """
    shifted    = logits - logits.max(axis=1, keepdims=True)
    exp_logits = np.exp(shifted)
    proba      = exp_logits / exp_logits.sum(axis=1, keepdims=True)
    return proba


def verify_softmax_normalization(proba, tol=1e-4):
    """
    Verify that softmax output rows are valid probability distributions.

    Prints a warning if any row deviates from sum = 1.0 beyond the
    tolerance. Useful for catching silent softmax errors in C-simulation.

    Args:
        proba : Probability array (N, K).
        tol   : Maximum allowed deviation from 1.0.

    Returns:
        max_deviation : float — max|sum(row) - 1| across all rows.
    """
    row_sums      = proba.sum(axis=1)
    deviations    = np.abs(row_sums - 1.0)
    max_deviation = float(deviations.max())

    if max_deviation > tol:
        print(f"  WARNING: max |sum(p_k) - 1| = {max_deviation:.2e}  "
              "(possible softmax normalization error)")
    else:
        print(f"  Softmax check passed : max |sum(p_k) - 1| = {max_deviation:.2e}")

    return max_deviation


# ─────────────────────────────────────────────────────────────────────────────
# hls4ml configuration
# ─────────────────────────────────────────────────────────────────────────────

def build_hls4ml_config(logit_model, precision, reuse_factor=1):
    """
    Build the per-layer hls4ml configuration dictionary.

    Every layer is assigned:
      - precision    : The specified ap_fixed<W,I> type for weights and
                       activations.
      - Strategy     : 'Latency' — optimise for minimum clock cycles.
      - ReuseFactor  : Controls loop unrolling depth.
                       1 = fully unrolled (maximum parallelism).

    Args:
        logit_model  : Keras model terminating at Dense(K), no softmax.
        precision    : Fixed-point string e.g. 'ap_fixed<24,12>'.
        reuse_factor : Integer reuse factor (default 1).

    Returns:
        config : dict passed to hls4ml.converters.convert_from_keras_model.
    """
    config = hls4ml.utils.config_from_keras_model(
        logit_model,
        granularity="name",
        default_precision=precision
    )

    for layer_name in config["LayerName"]:
        config["LayerName"][layer_name]["Strategy"]    = "Latency"
        config["LayerName"][layer_name]["ReuseFactor"] = reuse_factor

    return config


# ─────────────────────────────────────────────────────────────────────────────
# Model conversion and compilation
# ─────────────────────────────────────────────────────────────────────────────

def convert_to_hls(logit_model, precision, output_dir,
                   fpga_part, reuse_factor=1):
    """
    Convert the logit sub-model to a Vivado HLS C++ project and compile
    it with g++ for C-level simulation.

    Only the logit sub-model is converted (no softmax layer). The
    generated C++ project is written to output_dir and compiled
    immediately to verify functional correctness before synthesis.

    Args:
        logit_model  : Keras model ending at Dense(K), no softmax.
        precision    : Fixed-point string e.g. 'ap_fixed<24,12>'.
        output_dir   : Directory for the generated Vivado HLS project.
        fpga_part    : Xilinx part string e.g. 'xc7z020clg400-1'.
        reuse_factor : Loop unrolling depth (1 = fully unrolled).

    Returns:
        hls_model : Compiled hls4ml model object. Supports .predict()
                    for C-simulation and .build() for RTL synthesis.

    Raises:
        RuntimeError : If hls4ml conversion or g++ compilation fails.
    """
    os.makedirs(output_dir, exist_ok=True)

    config = build_hls4ml_config(logit_model, precision, reuse_factor)

    print(f"  Converting model to HLS C++ ...")
    print(f"    Precision    : {precision}")
    print(f"    ReuseFactor  : {reuse_factor}")
    print(f"    Output dir   : {output_dir}")
    print(f"    FPGA part    : {fpga_part}")

    hls_model = hls4ml.converters.convert_from_keras_model(
        logit_model,
        hls_config=config,
        output_dir=output_dir,
        part=fpga_part
    )

    print("  Compiling HLS project with g++ for C-simulation ...")
    hls_model.compile()
    print("  Compilation successful.\n")

    return hls_model


# ─────────────────────────────────────────────────────────────────────────────
# Hardware inference
# ─────────────────────────────────────────────────────────────────────────────

def run_hardware_inference(hls_model, X_verify):
    """
    Run C-simulation inference on the compiled HLS model and return
    class probabilities.

    The HLS model outputs raw logits. Softmax is applied in Python
    to bypass the hls4ml 1.3.0 normalization defect.

    Args:
        hls_model : Compiled hls4ml model (output of convert_to_hls).
        X_verify  : Input array (N, T, 1). Cast to float32 and made
                    C-contiguous if necessary.

    Returns:
        hw_proba : Probability array (N, K) with rows summing to 1.0.
    """
    X_c = np.ascontiguousarray(X_verify, dtype=np.float32)

    print("  Running HLS C-simulation inference ...")
    hw_logits = hls_model.predict(X_c)
    hw_proba  = numpy_softmax(hw_logits)
    verify_softmax_normalization(hw_proba)

    return hw_proba


# ─────────────────────────────────────────────────────────────────────────────
# Precision sweep
# ─────────────────────────────────────────────────────────────────────────────

def run_precision_sweep(logit_model, X_verify, y_verify,
                        precisions, fpga_part, base_output_dir,
                        reuse_factor=1):
    """
    Evaluate hardware AUC-ROC across multiple fixed-point precisions.

    For each precision string in `precisions`, a separate hls4ml
    conversion and C-simulation is performed. The resulting AUC is
    compared against the floating-point reference to determine the
    minimum viable bit width.

    Args:
        logit_model     : Keras logit sub-model (Dense(K), no softmax).
        X_verify        : Validation inputs  (N, T, 1).
        y_verify        : Validation labels  (N,).
        precisions      : Ordered list of precision strings to evaluate.
        fpga_part       : Xilinx FPGA part string.
        base_output_dir : Root directory; each config gets its own subfolder.
        reuse_factor    : ReuseFactor applied to all configurations.

    Returns:
        sweep_results : dict  {precision_string: metrics_dict}
    """
    from evaluate import compute_metrics

    sweep_results = {}

    print("\n" + "=" * 62)
    print("  Fixed-Point Precision Sweep")
    print("=" * 62)

    for idx, precision in enumerate(precisions, start=1):
        print(f"\n  [{idx}/{len(precisions)}]  {precision}")
        print("  " + "-" * 40)

        safe_name  = (precision.replace("<", "")
                               .replace(">", "")
                               .replace(",", "_"))
        output_dir = os.path.join(base_output_dir, f"sweep_{safe_name}")

        try:
            hls_model = convert_to_hls(
                logit_model,
                precision=precision,
                output_dir=output_dir,
                fpga_part=fpga_part,
                reuse_factor=reuse_factor
            )

            hw_proba = run_hardware_inference(hls_model, X_verify)
            metrics  = compute_metrics(y_verify, hw_proba)

            metrics["degenerate"] = (
                metrics["sensitivity"] < 0.05 or metrics["auc"] < 0.52
            )

            status = "DEGENERATE" if metrics["degenerate"] else "OK"
            print(f"  Result — AUC={metrics['auc']:.4f}  "
                  f"Sens={metrics['sensitivity']:.4f}  "
                  f"Spec={metrics['specificity']:.4f}  [{status}]")

        except Exception as exc:
            print(f"  FAILED  — {exc}")
            metrics = {
                "auc": 0.0, "accuracy": 0.0,
                "sensitivity": 0.0, "specificity": 0.0,
                "f1": 0.0, "precision_score": 0.0,
                "degenerate": True, "error": str(exc)
            }

        sweep_results[precision] = metrics

    _print_sweep_table(sweep_results, precisions)
    return sweep_results


# ─────────────────────────────────────────────────────────────────────────────
# Vivado RTL synthesis (optional — requires Vivado HLS in PATH)
# ─────────────────────────────────────────────────────────────────────────────

def synthesize_fpga(hls_model, csim=False, synth=True, export=False):
    """
    Run Vivado HLS RTL synthesis on the converted HLS project.

    Requires Xilinx Vivado HLS (or Vivado ML WebPACK — free for xc7z020)
    to be installed and its bin directory available in the system PATH.

    After synthesis, Vivado HLS produces:
      - Resource utilization report (LUT, FF, DSP, BRAM)
      - Timing report (estimated clock period and latency in cycles)

    Args:
        hls_model : Compiled hls4ml model returned by convert_to_hls().
        csim      : Re-run C-simulation (usually already done via compile()).
        synth     : Run Vivado HLS RTL synthesis.
        export    : Package the design as a Vivado IP core.
    """
    print("\nStarting Vivado HLS RTL synthesis ...")
    print("(This may take several minutes depending on design complexity)\n")

    hls_model.build(csim=csim, synth=synth, export=export)

    print("\nSynthesis complete.")
    _print_vivado_report(hls_model)


def _print_vivado_report(hls_model):
    """Read and display the Vivado synthesis resource report."""
    try:
        out_dir = hls_model.config.get_output_dir()
        report  = hls4ml.report.read_vivado_report(out_dir)
        print("\nVivado Synthesis Report")
        print("=" * 52)
        print(report)
    except Exception as exc:
        try:
            out_dir = hls_model.config.get_output_dir()
        except Exception:
            out_dir = "hls_project"
        print(f"  Could not parse Vivado report automatically: {exc}")
        print(f"  Check synthesis reports in: {out_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_sweep_table(sweep_results, precisions):
    """Print a clean tabular summary of the precision sweep results."""
    print("\n" + "=" * 64)
    print("  Precision Sweep — Summary Table")
    print("=" * 64)
    print(f"  {'Precision':<22} {'AUC':>8} {'Sens':>8} "
          f"{'Spec':>8}  Status")
    print("  " + "-" * 60)

    for precision in precisions:
        m = sweep_results.get(precision, {})
        if m.get("error") and m.get("auc", 0.0) == 0.0:
            print(f"  {precision:<22} {'FAILED':>8}")
            continue
        status = "DEGENERATE" if m.get("degenerate") else "OK"
        print(f"  {precision:<22} {m.get('auc', 0.0):>8.4f} "
              f"{m.get('sensitivity', 0.0):>8.4f} "
              f"{m.get('specificity', 0.0):>8.4f}  {status}")

    print()

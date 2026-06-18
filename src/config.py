"""
config.py
---------
Central configuration for the SE-ECG FPGA pipeline.
Edit this file to change hyperparameters, paths, or FPGA settings.
"""

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR        = "data"
WEIGHTS_DIR     = "weights/Model_weights"
FIGURES_DIR     = "figures"
RESULTS_DIR     = "results"
HLS_DIR_MAIN    = "hls_project/hls_ecg_main"
HLS_DIR_LIGHT   = "hls_project/hls_ecg_light"
HLS_SWEEP_DIR   = "hls_project/sweep"

# ── Dataset ───────────────────────────────────────────────────────────────────
DATASET_NAME  = "ECG5000"
N_TIMESTEPS   = 140
N_CLASSES     = 2

# ── Multi-seed training ───────────────────────────────────────────────────────
RANDOM_SEEDS  = [42, 123, 456, 789, 2024]
BEST_SEED     = 42           # Seed that produced the highest validation AUC

# ── Architecture ──────────────────────────────────────────────────────────────
EMBED_DIM     = 16           # Embedding / output channel dimension (C)
FFN_DIM       = 32           # Feed-forward expansion dimension
SE_REDUCTION  = 8            # SE bottleneck dimension (reduction ratio = C / r)

# ── Training ──────────────────────────────────────────────────────────────────
LEARNING_RATE = 5e-4
BATCH_SIZE    = 32
MAX_EPOCHS    = 60
ES_PATIENCE   = 12           # Early stopping patience (val_loss)
LR_PATIENCE   = 5            # ReduceLROnPlateau patience
LR_FACTOR     = 0.5          # Learning rate reduction factor
MIN_LR        = 1e-6

# ── FPGA / hls4ml ─────────────────────────────────────────────────────────────
FPGA_PART       = "xc7z020clg400-1"   # Xilinx PYNQ-Z2
REUSE_FACTOR    = 1                    # 1 = full loop unrolling (min latency)
CLOCK_MHZ       = 100
PRECISION_MAIN  = "ap_fixed<24,12>"   # Selected precision (best from sweep)
PRECISION_LIGHT = "ap_fixed<12,6>"    # Ablation / light variant

# Fixed-point configurations evaluated in the precision sweep
PRECISION_SWEEP = [
    "ap_fixed<8,4>",
    "ap_fixed<12,6>",
    "ap_fixed<16,8>",
    "ap_fixed<20,10>",
    "ap_fixed<24,12>",
]

# ── Hardware validation ────────────────────────────────────────────────────────
N_VERIFY = 1000    # Stratified subset size for SW-HW comparison
N_SWEEP  = 200     # Stratified subset size for the precision sweep

# Convenience aliases (used by main.py)
SEEDS    = RANDOM_SEEDS
HLS_DIR  = HLS_DIR_MAIN

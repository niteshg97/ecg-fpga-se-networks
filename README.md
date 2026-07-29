# Hardware-Efficient Squeeze-and-Excitation Networks for Real-Time ECG Anomaly Detection on FPGAs

<p align="center">
  <a href="https://arxiv.org/abs/XXXX.XXXXX">
    <img src="https://img.shields.io/badge/arXiv-XXXX.XXXXX-b31b1b?style=for-the-badge&logo=arxiv" alt="arXiv"/>
  </a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/TensorFlow-2.20-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white" alt="TensorFlow"/>
  <img src="https://img.shields.io/badge/hls4ml-1.3.0-8A2BE2?style=for-the-badge" alt="hls4ml"/>
  <img src="https://img.shields.io/badge/FPGA-Xilinx%20Zynq--7020-EE0000?style=for-the-badge" alt="FPGA"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License: MIT"/>
</p>

---

## Overview

This repository contains the complete implementation of a **hardware-efficient Squeeze-and-Excitation (SE) channel-attention network** for real-time cardiac anomaly detection on FPGAs, deployed end-to-end via the [`hls4ml`](https://fastmachinelearning.org/hls4ml/) codesign framework.

The proposed **1,674-parameter** model achieves an **AUC-ROC of 93.32%** in software and retains **92.84% AUC** after 24-bit fixed-point conversion, with a **logic fidelity of 99.9%** between floating-point and hardware predictions. Vivado synthesis on the **Xilinx xc7z020clg400-1** yields a **2.0 µs inference latency** at 100 MHz — approximately **140,000× faster** than the real-time requirement for continuous 500 Hz ECG monitoring.

---

## Key Contributions

| # | Contribution |
|---|---|
| 1 | **Hardware-compatible SE attention** — Placing SE attention *after* Global Average Pooling eliminates tensor-broadcasting operations that cause silent incorrect HLS code generation in hls4ml 1.3.0 |
| 2 | **hls4ml softmax inference fix** — Documents and resolves a silent inference defect in hls4ml 1.3.0 C-simulation: the fixed-point exponential LUT produces correctly normalized outputs (Σpk = 1.0) but causes up to 100% of argmax decisions to flip relative to the float32 reference depending on weight distribution |
| 3 | **Precision characterization** — Five-point sweep (8-bit → 24-bit) identifies `ap_fixed<24,12>` as the minimum viable precision for 140-step cardiac sequences |
| 4 | **End-to-end FPGA validation** — Complete software-to-hardware pipeline with 99.9% logic fidelity and 2.0 µs synthesized latency on Xilinx xc7z020clg400-1 |

---

## Results

### Software Performance (ECG5000, N = 4,500)

| | AUC-ROC | Accuracy | Sensitivity | Specificity | F1-Score |
|---|:---:|:---:|:---:|:---:|:---:|
| **Best Seed (42)** | **93.32%** | **91.18%** | **84.20%** | **96.16%** | **88.82%** |
| Mean ± Std (5 seeds) | 89.68 ± 2.22% | 85.50 ± 9.10% | 67.82 ± 21.91% | 98.10 ± 1.27% | 77.11 ± 19.26% |

### Software vs. Hardware (`ap_fixed<24,12>`, N = 1,000 stratified subset)

| Metric | SW (float32) | HW (ap\_fixed\<24,12\>) | Δ |
|---|:---:|:---:|:---:|
| AUC-ROC | 92.87% | 92.84% | −0.03% |
| Accuracy | 91.30% | 91.40% | +0.10% |
| Sensitivity | 84.38% | 84.38% | 0.00% |
| Specificity | 96.23% | 96.40% | +0.17% |
| F1-Score | 88.97% | 89.09% | +0.12% |
| **Logic Fidelity (Φ)** | — | **99.90% (999/1000)** | — |

### Fixed-Point Precision Sweep (N = 200 balanced subset)

| Precision | HW AUC | Sensitivity | Status |
|---|:---:|:---:|:---:|
| `ap_fixed<8,4>` | 0.500 | 0.000 | Degenerate |
| `ap_fixed<12,6>` | 0.263 | 0.247 | Insufficient |
| `ap_fixed<16,8>` | 0.718 | 0.659 | Functional |
| `ap_fixed<20,10>` | 0.922 | 0.800 | Good |
| **`ap_fixed<24,12>`** | **0.924** | **0.800** | **Selected** |

> Configurations below 20-bit produce degenerate or substantially degraded inference due to insufficient fractional precision after Global Average Pooling over 140 time steps.

### FPGA Synthesis (Xilinx xc7z020clg400-1, 100 MHz)

| Resource | Used | Available | Utilization |
|---|:---:|:---:|:---:|
| LUTs | 34,475 | 53,200 | 64.8% |
| Flip-Flops | 18,961 | 106,400 | 17.8% |
| DSPs | 210 | 220 | **95.5%** |
| BRAMs | 2 | 140 | 1.4% |
| **Inference Latency** | **197 cycles** | **@ 100 MHz** | **2.0 µs** |

---

## Repository Structure

```
ecg-fpga-se-networks/
│
├── notebook/
│   └── ECG_FPGA_final.ipynb        # Complete pipeline: training → hls4ml → evaluation
│
├── src/                            # Modular Python source
│   ├── config.py                   # Hyperparameters, paths, FPGA settings
│   ├── data.py                     # ECG5000 loading, class weights, stratified subset
│   ├── model.py                    # SE-ECG architecture, logit sub-model extraction
│   ├── train.py                    # Multi-seed training, callbacks, summary
│   ├── evaluate.py                 # Metrics, logic fidelity, all plot functions
│   ├── fpga_deploy.py              # hls4ml conversion, C-simulation, precision sweep
│   └── main.py                     # Full Code 
│
├── figures/                        # Generated plots (training curves, ROC, confusion matrices)
│
├── weights/
│   └── Model_weights/              # Saved Keras weights (best seed = 42)
│
├── hls_project/
│   ├── hls_ecg_main/               # HLS project: ap_fixed<24,12>, RF=1 (selected)
│   └── hls_ecg_light/              # HLS project: ap_fixed<12,6>, RF=1 (ablation)
│
├── data/
│   └── README.md                   # Data download instructions
│
├── paper/
│   └── paper.tex                   # LaTeX source
│
├── README.md
└── LICENSE
```

---

## Setup and Installation

### Prerequisites

- Python ≥ 3.9
- CUDA-enabled GPU (recommended; tested on NVIDIA T4 via Google Colab)
- For FPGA synthesis: Xilinx Vivado HLS (WebPACK edition, free for xc7z020)

### Install Dependencies

```bash
git clone https://github.com/niteshg97/ecg-fpga-se-networks.git
cd ecg-fpga-se-networks

pip install tensorflow==2.20
pip install tf_keras
pip install hls4ml[profiling]==1.3.0
pip install scikit-learn matplotlib seaborn aeon
```

> **Note on tf_keras:** hls4ml 1.3.0 uses the stable V2 graph parser, which requires the legacy `tf_keras` (Keras 2). Standard Keras 3 (bundled with TF 2.16+) is not directly supported by hls4ml 1.3.0 for model conversion. The Keras version override `keras.__version__ = "2.15.0"` forces the correct internal parser — see `src/fpga_deploy.py` for details.

---

## Data Preparation

The **ECG5000** dataset is part of the [UCR Time Series Classification Archive](https://www.cs.ucr.edu/~eamonn/time_series_data_2018/).

```bash
# Automatic download via aeon (used in the notebook)
pip install aeon
# The notebook handles download and preprocessing automatically.

# Manual: place files in data/ if using local copies
# data/ECG5000_TRAIN.txt
# data/ECG5000_TEST.txt
```

### Dataset Statistics

| Split | Total | Normal (Class 0) | Anomaly (Class 1) |
|---|:---:|:---:|:---:|
| Training | 500 | 292 (58.4%) | 208 (41.6%) |
| Test | 4,500 | 2,627 (58.4%) | 1,873 (41.6%) |
| **Total** | **5,000** | **2,919** | **2,081** |

Each sample: **140 time steps**, single-channel ECG heartbeat segment, binary label (Normal / Anomaly).

---

## Usage

### Run the Full Pipeline

Open the notebook on Google Colab (recommended for free GPU access):

```bash
jupyter notebook notebook/ECG_FPGA_final.ipynb
```

### Run the Modular Pipeline via CLI

```bash
# Full pipeline: train → sweep → hardware validation
python src/main.py

# Skip training (load saved weights)
python src/main.py --skip-training

# Skip precision sweep
python src/main.py --skip-sweep

# Also run Vivado RTL synthesis (requires Vivado HLS in PATH)
python src/main.py --synth
```

### Load Pre-trained Weights

```python
import tf_keras as keras
from src.model import build_se_ecg_model, extract_logit_model

# Rebuild architecture and load weights
model = build_se_ecg_model()
model.load_weights('weights/Model_weights/best_model.weights.h5')

# Extract logit sub-model for FPGA conversion
logit_model = extract_logit_model(model)
```

---

## Model Architecture

<p align="center">
  <img src="https://github.com/user-attachments/assets/1edbdb61-a2b0-45ba-b684-b1652246617a"
       alt="SE-ECG Architecture"
       width="490">
</p>

The network processes `(140, 1)` ECG inputs through three stages:

**1. Temporal Encoder** — Three time-distributed Dense layers with BatchNormalization, ReLU, and a residual skip connection, producing `R ∈ ℝ^{140×16}`.

**2. SE Channel-Attention Block** — Global Average Pooling collapses the temporal dimension to `z ∈ ℝ^{16}`. A bottleneck Dense(8, ReLU) → Dense(16, Sigmoid) network produces channel attention weights `s`, applied as `h = z + (s ⊙ z)`.

**3. Output** — A Dense(2) logit layer produces raw class scores. The Softmax layer is excluded from the FPGA sub-model (see Softmax section below).

**Why SE attention after pooling?**  
Placing SE attention on the post-pooled `(16,)` vector ensures all `Multiply` and `Add` operations use identical-shape operands, eliminating the tensor-broadcast operations that hls4ml 1.3.0 handles incorrectly when attention weights `(16,)` are applied to pre-pooled feature maps `(140, 16)`.

| Layer | Output Shape | Parameters |
|---|:---:|:---:|
| Input | (140, 1) | 0 |
| Dense(16) + BN + ReLU [time-dist] | (140, 16) | 96 |
| Dense(32) + BN + ReLU [time-dist] | (140, 32) | 672 |
| Dense(16) + Add + BN [time-dist] | (140, 16) | 592 |
| GlobalAveragePooling1D | (16,) | 0 |
| Dense(8, ReLU) — SE squeeze | (8,) | 136 |
| Dense(16, Sigmoid) — SE excite | (16,) | 144 |
| Multiply + Add (residual) | (16,) | 0 |
| **Dense(2) — logit output** ← FPGA boundary | **(2,)** | **34** |
| Softmax † | (2,) | 0 |
| **Total** | | **1,674** |

† Excluded from FPGA sub-model.

---

## Training Details

| Hyperparameter | Value |
|---|---|
| Optimizer | Adam |
| Learning Rate | 5 × 10⁻⁴ |
| Batch Size | 32 |
| Max Epochs | 60 |
| LR Reduction Factor | 0.5 (patience: 5 epochs) |
| Early Stopping Patience | 12 epochs (val. loss) |
| Class Weight — Normal | 0.856 |
| Class Weight — Anomaly | 1.202 |
| Random Seeds | 42, 123, 456, 789, 2024 |
| Framework | TensorFlow 2.20 / tf\_keras |
| Hardware | NVIDIA T4 (Google Colab) |

---

## FPGA Deployment via hls4ml

### The Softmax Inference Defect in hls4ml 1.3.0

> **Related open issue:** [fastmachinelearning/hls4ml #1443](https://github.com/fastmachinelearning/hls4ml/issues/1443)

hls4ml 1.3.0 C-simulation (`hls_model.compile()` + `hls_model.predict()`) contains a softmax inference defect: the fixed-point exponential look-up table (LUT) produces **correctly normalized** class probabilities (`max|Σpk − 1| = 0.0` always), but introduces approximation errors that cause up to **100% of argmax classification decisions to differ** from the float32 reference depending on the model's weight distribution.

The defect is **silent** — no error or warning is raised, and probabilities appear valid. It is weight-distribution dependent: models with near-boundary predictions (common in any trained classifier) are most severely affected.

**Verified across 8 random weight seeds (N=200 fixed inputs, same architecture):**

| Seed | HLS Softmax Flips | Logit-only Flips | Normalization |
|---|:---:|:---:|:---:|
| 0 | 94/200 (47%) | 0/200 | ✓ sum=1.0 |
| 1 | **200/200 (100%)** | 10/200 | ✓ sum=1.0 |
| 7 | 0/200 | 3/200 | ✓ sum=1.0 |
| 99 | 94/200 (47%) | 0/200 | ✓ sum=1.0 |
| 999 | 106/200 (53%) | 4/200 | ✓ sum=1.0 |

**Fix:** convert only the logit sub-model (no softmax layer) and apply numerically stable Python softmax post-hardware:

```python
# ── Keras version override (required for hls4ml 1.3.0 V2 parser) ──
import keras as _keras_compat
_keras_compat.__version__ = "2.15.0"

import hls4ml
import numpy as np

def numpy_softmax(logits):
    """Numerically stable softmax — replaces defective HLS LUT."""
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)

# ── WRONG: do NOT convert the full model (softmax inside HLS) ────
# hls_model = hls4ml.converters.convert_from_keras_model(full_model, ...)

# ── CORRECT: convert logit sub-model only (Dense(2), no softmax) ─
hls_model = hls4ml.converters.convert_from_keras_model(
    logit_model,           # terminates at Dense(2), no Softmax layer
    hls_config=config,
    output_dir='hls_project/hls_ecg_main',
    part='xc7z020clg400-1'
)
hls_model.compile()

# Apply softmax in Python after reading FPGA logit outputs
hw_logits = hls_model.predict(np.ascontiguousarray(X_test, dtype=np.float32))
hw_proba  = numpy_softmax(hw_logits)   # correct, normalized probabilities
```

This fix requires **no modification** to hls4ml source code and achieves **99.9% logic fidelity** (999/1,000 predictions agree with float32 Keras reference).

### hls4ml Configuration

```python
config = hls4ml.utils.config_from_keras_model(
    logit_model,
    granularity='name',
    default_precision='ap_fixed<24,12>'
)

for layer in config['LayerName']:
    config['LayerName'][layer]['Strategy']    = 'Latency'
    config['LayerName'][layer]['ReuseFactor'] = 1
```

| Parameter | Value |
|---|---|
| Target Device | `xc7z020clg400-1` |
| hls4ml Version | 1.3.0 |
| Fixed-Point Precision | `ap_fixed<24,12>` |
| ReuseFactor | 1 (full loop unrolling) |
| Strategy | Latency |
| Converted Model | Logit sub-model (no softmax) |
| Clock Target | 100 MHz |

### Vivado RTL Synthesis

```python
# After hls4ml conversion and C-simulation:
hls_model.build(csim=False, synth=True, export=False)

# Read synthesis report:
report = hls4ml.report.read_vivado_report('hls_project/hls_ecg_main')
print(report)
```

> Vivado HLS (WebPACK edition, free for xc7z020) must be installed and available in PATH.

---

## Citation

If you find this work useful, please cite:

```bibtex
@article{kumar2025ecg_fpga,
  author    = {Kumar, Nitesh and Kumar, Ashwani},
  title     = {Hardware-Efficient Squeeze-and-Excitation Networks for
               Real-Time {ECG} Anomaly Detection on {FPGAs}},
  journal   = {arXiv preprint arXiv:XXXX.XXXXX},
  year      = {2026},
  url       = {https://arxiv.org/abs/XXXX.XXXXX}
}
```


---

## Related Work

| Paper | Venue | Relevance |
|---|---|---|
| [Fast inference of DNNs in FPGAs for particle physics](https://doi.org/10.1088/1748-0221/13/07/P07027) | JINST 2018 | Original hls4ml paper |
| [hls4ml: An open-source codesign workflow](https://github.com/fastmachinelearning/hls4ml) | FPGA 2021 | hls4ml framework |
| [Fast CNNs on FPGAs with hls4ml](https://doi.org/10.1088/2632-2153/ac0ea1) | MLST 2021 | Conv1D + hls4ml |
| [Automatic heterogeneous quantization](https://doi.org/10.1038/s42256-021-00356-5) | Nat. Machine Intell. 2021 | Mixed-precision hls4ml |
| [Squeeze-and-Excitation Networks](https://doi.org/10.1109/TPAMI.2019.2913372) | IEEE TPAMI 2020 | SE attention mechanism |
| [Cardiologist-level arrhythmia detection](https://doi.org/10.1038/s41591-018-0268-3) | Nature Medicine 2019 | ECG DL benchmark |
| [ECG heartbeat classification](https://doi.org/10.1109/ICHI.2018.00012) | ICHI 2018 | ECG5000 baseline |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- The [hls4ml](https://fastmachinelearning.org/hls4ml/) team (CERN / Fermilab / MIT) for the open-source codesign framework that makes FPGA-based ML inference accessible beyond high-energy physics.
- The [UCR Time Series Classification Archive](https://www.cs.ucr.edu/~eamonn/time_series_data_2018/) for the ECG5000 benchmark.
- [National Institute of Technology Patna](https://www.nitp.ac.in/), Department of Electrical Engineering.

---

<p align="center">
  Made with ❤️ at NIT Patna &nbsp;|&nbsp;
  <a href="mailto:niteshk.ug23.ee@nitp.ac.in">niteshk.ug23.ee@nitp.ac.in</a>
  &nbsp;|&nbsp;
  <a href="mailto:ashwani@nitp.ac.in">ashwani@nitp.ac.in</a>
</p>

# Hardware-Efficient Squeeze-and-Excitation Networks for Real-Time ECG Anomaly Detection on FPGAs

<p align="center">
  <img src="figures/Full_Architecture.png" alt="SE-ECG Architecture" width="720"/>
</p>

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

The proposed **1,674-parameter** model achieves **AUC-ROC of 93.32%** in software and retains **92.84% AUC** after 24-bit fixed-point conversion, with a **logic fidelity of 99.9%** between floating-point and hardware predictions. Vivado synthesis on the **Xilinx xc7z020clg400-1** yields a **2.0 µs inference latency** at 100 MHz — approximately **140,000× faster** than the real-time requirement for continuous 500 Hz ECG monitoring.

### Key Contributions

| # | Contribution |
|---|---|
| 1 | **Hardware-compatible SE attention** — Placing SE attention after Global Average Pooling eliminates tensor-broadcasting operations that cause incorrect HLS code generation in hls4ml |
| 2 | **hls4ml softmax fix** — Documents and resolves a softmax normalization defect in hls4ml 1.3.0 C-simulation where both class probabilities simultaneously exceed 0.5 |
| 3 | **Precision characterization** — Five-point sweep (8-bit → 24-bit) identifies `ap_fixed<24,12>` as the minimum viable precision for 140-step cardiac sequences |
| 4 | **End-to-end FPGA validation** — Complete software-to-hardware pipeline with 99.9% logic fidelity and 2.0 µs synthesized latency |

---

## Results 

### Software Performance (ECG5000, N = 4,500)

| | AUC-ROC | Accuracy | Sensitivity | Specificity | F1-Score |
|---|---|---|---|---|---|
| **Best Seed (42)** | **93.32%** | **91.18%** | **84.20%** | **96.16%** | **88.82%** |
| Mean ± Std (5 seeds) | 89.68 ± 2.22% | 85.50 ± 9.10% | 67.82 ± 21.91% | 98.10 ± 1.27% | 77.11 ± 19.26% |

### Software vs. Hardware (ap_fixed\<24,12\>, N = 1,000)

| Metric | SW (float32) | HW (ap_fixed\<24,12\>) | Δ |
|---|:---:|:---:|:---:|
| AUC-ROC | 92.87% | 92.84% | −0.03% |
| Accuracy | 91.30% | 91.40% | +0.10% |
| Sensitivity | 84.38% | 84.38% | 0.00% |
| Specificity | 96.23% | 96.40% | +0.17% |
| F1-Score | 88.97% | 89.09% | +0.12% |
| **Logic Fidelity** | — | **99.90%** | — |

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
│   └── ECG_FPGA_final.ipynb        # training → hls4ml conversion → evaluation
│
├── figures
│   
│   
├── weights/
│   └── Model_weights/               # Saved Keras model weights (best seed = 42)
│
├── hls_project/
│   ├── hls_ecg_main/                # HLS project: ap_fixed<24,12>, RF=1 (selected)
│   └── hls_ecg_light/               # HLS project: ap_fixed<12,6>, RF=1 (ablation)
│
├── paper/
│   └── paper.tex                    # LaTeX source (arXiv preprint)
│
├── data/
│   └── README.md                    # Data download instructions (see below)
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
git clone https://github.com/<your-username>/ecg-fpga-se-networks.git
cd ecg-fpga-se-networks

pip install tensorflow==2.20
pip install tf_keras
pip install hls4ml[profiling]==1.3.0
pip install scikit-learn matplotlib seaborn
```

> **Note:** `tf_keras` (legacy Keras 2) is required because hls4ml 1.3.0 uses the stable V2 graph parser. Standard Keras 3 (bundled with TF 2.16+) is not directly supported by hls4ml for model conversion.

---

## Data Preparation

The **ECG5000** dataset is part of the [UCR Time Series Classification Archive](https://www.cs.ucr.edu/~eamonn/time_series_data_2018/).

### Download

```bash
# Option 1: Download directly from UCR (requires registration)
# https://www.cs.ucr.edu/~eamonn/time_series_data_2018/ECG5000.zip

# Option 2: Using the aeon package (used in the notebook)
pip install aeon
```

The notebook automatically downloads and preprocesses ECG5000 via `aeon`. Place the data files in the `data/` directory if using local files:

```
data/
├── ECG5000_TRAIN.txt
└── ECG5000_TEST.txt
```

### Dataset Statistics

| Split | Total | Normal (Class 0) | Anomaly (Class 1) |
|---|:---:|:---:|:---:|
| Training | 500 | 292 (58.4%) | 208 (41.6%) |
| Test | 4,500 | 2,627 (58.4%) | 1,873 (41.6%) |
| **Total** | **5,000** | **2,919** | **2,081** |

Each sample: **140 time steps**, single-channel ECG heartbeat segment.

---

## Usage

### 1. Run the Full Pipeline (Recommended)

Open and run the notebook end-to-end:

```bash
jupyter notebook notebook/ECG_FPGA_final.ipynb
```

Or on **Google Colab** (recommended for GPU access):

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/<your-username>/ecg-fpga-se-networks/blob/main/notebook/ECG_FPGA_final.ipynb)

### 2. Load Pre-trained Weights

```python
import tf_keras as keras

# Load logit model (for FPGA inference)
logit_model = keras.models.load_model('weights/Model_weights/logit_model.h5')

# Load full model (with softmax, for training/evaluation)
full_model = keras.models.load_model('weights/Model_weights/full_model.h5')
```

---

## FPGA Deployment via hls4ml

### Important: Softmax Bug Fix

`hls4ml` 1.3.0 contains a **softmax normalization defect** in C-simulation where both class probabilities simultaneously exceed 0.5 (violating $\sum_k p_k = 1$). The fix implemented in this project:

```python
# WRONG — do NOT convert the full model (softmax included)
# hls_model = hls4ml.converters.convert_from_keras_model(full_model, ...)

# CORRECT — convert only the logit sub-model (Dense(2), no softmax)
hls_model = hls4ml.converters.convert_from_keras_model(
    logit_model,          # terminates at Dense(2)
    hls_config=config,
    output_dir='hls_project/hls_ecg_main',
    part='xc7z020clg400-1'
)

# Apply softmax manually in Python after reading FPGA logit outputs
def numpy_softmax(logits):
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)

hw_proba = numpy_softmax(hls_model.predict(X_test))
```

### hls4ml Configuration

```python
import keras as _keras_compat
_keras_compat.__version__ = "2.15.0"   # Force stable V2 parser

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

### Run C-Simulation

```bash
# Compile HLS project with g++
cd hls_project/hls_ecg_main
# hls_model.compile() in the notebook handles this automatically
```

### Vivado RTL Synthesis (requires local Linux/Windows + Vivado)

```python
# After hls4ml conversion, run synthesis:
hls_model.build(csim=False, synth=True, export=False)

# Read synthesis report:
report = hls4ml.report.read_vivado_report('hls_project/hls_ecg_main')
print(report)
```

---

## Fixed-Point Precision Sweep

A systematic five-point sweep identifies `ap_fixed<24,12>` as the minimum viable precision for 140-step cardiac sequences:

| Precision | HW AUC | Sensitivity | Specificity | Status |
|---|:---:|:---:|:---:|:---:|
| `ap_fixed<8,4>` | 0.500 | 0.000 | 1.000 | Degenerate |
| `ap_fixed<12,6>` | 0.263 | 0.247 | 0.452 | Insufficient |
| `ap_fixed<16,8>` | 0.718 | 0.659 | 0.800 | Functional |
| `ap_fixed<20,10>` | 0.922 | 0.800 | 0.965 | Good |
| **`ap_fixed<24,12>`** | **0.924** | **0.800** | **0.965** | **Selected** |

> Configurations below 20-bit produce degenerate or substantially degraded inference due to insufficient fractional precision after Global Average Pooling over 140 time steps.

---

## Model Architecture

<p align="center">
  <img src="figures/Full_Architecture.png" alt="SE-ECG Architecture" width="720"/>
</p>




**Why SE attention after pooling?**
Placing SE attention on the post-pooled `(16,)` vector ensures all `Multiply` and `Add` operations use operands of **identical shape**, eliminating the tensor-broadcast operations that hls4ml incorrectly handles when attention weights `(16,)` are applied to pre-pooled feature maps `(140, 16)`.

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
| Framework | TensorFlow 2.20 / tf_keras |
| Hardware | NVIDIA T4 (Google Colab) |

---

## Citation

If you find this work useful, please cite:

```bibtex
@article{kumar2025ecg_fpga,
  author    = {Kumar, Nitesh and Kumar, Ashwani},
  title     = {Hardware-Aware Squeeze-and-Excitation Networks for
               Real-Time {ECG} Anomaly Detection on {FPGAs}},
  journal   = {arXiv preprint arXiv:XXXX.XXXXX},
  year      = {2025},
  url       = {https://arxiv.org/abs/XXXX.XXXXX}
}
```

> Update `XXXX.XXXXX` with your arXiv identifier after submission.

---

## Related Work

| Paper | Venue | Relevance |
|---|---|---|
| [Fast inference of DNNs in FPGAs for particle physics](https://doi.org/10.1088/1748-0221/13/07/P07027) | JINST 2018 | Original hls4ml paper |
| [Fast CNNs on FPGAs with hls4ml](https://doi.org/10.1088/2632-2153/ac0ea1) | MLST 2021 | Conv1D + hls4ml |
| [Automatic heterogeneous quantization](https://doi.org/10.1038/s42256-021-00356-5) | Nat. Machine Intell. 2021 | Mixed-precision hls4ml |
| [Squeeze-and-Excitation Networks](https://doi.org/10.1109/TPAMI.2019.2913372) | IEEE TPAMI 2020 | SE attention mechanism |
| [Cardiologist-level arrhythmia detection](https://doi.org/10.1038/s41591-018-0268-3) | Nature Medicine 2019 | ECG DL benchmark |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- The [hls4ml](https://fastmachinelearning.org/hls4ml/) team (CERN / Fermilab / MIT) for the open-source codesign framework.
- The [UCR Time Series Classification Archive](https://www.cs.ucr.edu/~eamonn/time_series_data_2018/) for the ECG5000 dataset.
- [National Institute of Technology Patna](https://www.nitp.ac.in/), Department of Electrical Engineering.

---

<p align="center">
  Made with ❤️ at NIT Patna &nbsp;|&nbsp;
  <a href="mailto:niteshk.ug23.ee@nitp.ac.in">niteshk.ug23.ee@nitp.ac.in</a>
</p>

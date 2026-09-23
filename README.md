# Hardware-Efficient Squeeze-and-Excitation Networks for Real-Time ECG Anomaly Detection Using hls4ml on FPGAs

<p align="center">
  <a href="https://doi.org/10.5281/zenodo.22910536">
    <img src="https://img.shields.io/badge/DOI-10.5281%2Fzenodo.22910536-1f6feb?style=for-the-badge&logo=doi&logoColor=white" alt="DOI"/>
  </a>
  <a href="https://zenodo.org/records/22910536">
    <img src="https://img.shields.io/badge/Zenodo-Preprint-1682D4?style=for-the-badge&logo=zenodo&logoColor=white" alt="Zenodo Preprint"/>
  </a>
  <a href="https://github.com/niteshg97/ecg-fpga-se-networks">
    <img src="https://img.shields.io/badge/Code-GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"/>
  </a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/TensorFlow-2.20-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white" alt="TensorFlow"/>
  <img src="https://img.shields.io/badge/hls4ml-1.3.0-8A2BE2?style=for-the-badge" alt="hls4ml"/>
  <img src="https://img.shields.io/badge/FPGA-Xilinx%20Zynq--7020-EE0000?style=for-the-badge" alt="FPGA"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License: MIT"/>
</p>

<p align="center">
  <b>Nitesh Kumar · Ashwani Kumar</b><br>
  Department of Electrical Engineering, National Institute of Technology Patna
</p>

---

## Research Preprint

This repository contains the implementation and experimental materials accompanying the research preprint:

> **Hardware-Efficient Squeeze-and-Excitation Networks for Real-Time ECG Anomaly Detection Using hls4ml on FPGAs**

**Authors:** Nitesh Kumar and Ashwani Kumar
**Affiliation:** Department of Electrical Engineering, National Institute of Technology Patna

### Publication

* **Zenodo:** [10.5281/zenodo.22910536](https://doi.org/10.5281/zenodo.22910536)
* **Preprint record:** [Zenodo Record](https://zenodo.org/records/22910536)
* **Source code:** [GitHub Repository](https://github.com/niteshg97/ecg-fpga-se-networks)

> **Preprint status:** This work is publicly available as a research preprint and has not undergone peer review through a journal or conference publication process at the time of deposit.

### Citation

```bibtex
@misc{kumar2026hardware_efficient_ecg_fpga,
  author       = {Kumar, Nitesh and Kumar, Ashwani},
  title        = {Hardware-Efficient Squeeze-and-Excitation Networks
                  for Real-Time ECG Anomaly Detection Using hls4ml on FPGAs},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.22910536},
  url          = {https://doi.org/10.5281/zenodo.22910536},
  version      = {1.0},
  type         = {Preprint}
}
```

---

## Overview

This repository contains the implementation of a **hardware-efficient Squeeze-and-Excitation (SE) channel-attention network** for real-time ECG anomaly detection on FPGAs using the open-source [`hls4ml`](https://fastmachinelearning.org/hls4ml/) high-level synthesis framework.

The proposed **1,674-parameter** model achieves an **AUC-ROC of 93.32%** in software and retains **92.84% AUC** after 24-bit fixed-point conversion, with **99.9% logic fidelity** between floating-point and hardware predictions.

Vivado synthesis targeting the **Xilinx `xc7z020clg400-1`** device reports an inference latency of **2.0 µs at 100 MHz**.

The project covers the complete workflow:

**ECG5000 → Model Training → Fixed-Point Quantization → hls4ml Conversion → C-Simulation → FPGA Synthesis → Hardware Validation**

---

## Key Contributions

| #     | Contribution                                                                                                                                                                                                     |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Hardware-compatible SE attention** — Places SE attention after Global Average Pooling to operate on a compact channel vector and avoid problematic tensor-broadcast operations during HLS conversion.          |
| **2** | **hls4ml softmax investigation** — Documents a numerical inference issue observed in hls4ml 1.3.0 C-simulation and uses a logit-only FPGA conversion with numerically stable softmax applied externally.         |
| **3** | **Fixed-point precision characterization** — Evaluates 8-, 12-, 16-, 20-, and 24-bit fixed-point configurations and selects `ap_fixed<24,12>` for the reported deployment configuration.                         |
| **4** | **End-to-end FPGA evaluation** — Reports software performance, fixed-point behavior, hardware/software prediction fidelity, resource utilization, and synthesized inference latency on the target Xilinx device. |

---

## Results

### Software Performance

**ECG5000 test set — N = 4,500**

|                      |    AUC-ROC    |    Accuracy   |   Sensitivity  |  Specificity  |    F1-Score    |
| -------------------- | :-----------: | :-----------: | :------------: | :-----------: | :------------: |
| **Best Seed (42)**   |   **93.32%**  |   **91.18%**  |   **84.20%**   |   **96.16%**  |   **88.82%**   |
| Mean ± Std (5 seeds) | 89.68 ± 2.22% | 85.50 ± 9.10% | 67.82 ± 21.91% | 98.10 ± 1.27% | 77.11 ± 19.26% |

---

### Software vs. Hardware

**`ap_fixed<24,12>` — N = 1,000 stratified samples**

| Metric                 | SW (float32) | HW (`ap_fixed<24,12>`) |    Δ   |
| ---------------------- | :----------: | :--------------------: | :----: |
| AUC-ROC                |    92.87%    |         92.84%         | −0.03% |
| Accuracy               |    91.30%    |         91.40%         | +0.10% |
| Sensitivity            |    84.38%    |         84.38%         |  0.00% |
| Specificity            |    96.23%    |         96.40%         | +0.17% |
| F1-Score               |    88.97%    |         89.09%         | +0.12% |
| **Logic Fidelity (Φ)** |       —      |  **99.90% (999/1000)** |    —   |

---

### Fixed-Point Precision Sweep

**N = 200 balanced subset**

| Precision             |   HW AUC  | Sensitivity |    Status    |
| --------------------- | :-------: | :---------: | :----------: |
| `ap_fixed<8,4>`       |   0.500   |    0.000    |  Degenerate  |
| `ap_fixed<12,6>`      |   0.263   |    0.247    | Insufficient |
| `ap_fixed<16,8>`      |   0.718   |    0.659    |  Functional  |
| `ap_fixed<20,10>`     |   0.922   |    0.800    |     Good     |
| **`ap_fixed<24,12>`** | **0.924** |  **0.800**  | **Selected** |

> Configurations below 20-bit produce degenerate or substantially degraded inference due to insufficient fractional precision after Global Average Pooling over 140 time steps.

---

### FPGA Synthesis

**Target:** Xilinx `xc7z020clg400-1`
**Clock:** 100 MHz

| Resource              |      Used      |   Available   | Utilization |
| ---------------------- | :------------: | :-----------: | :---------: |
| LUTs                  |     34,475     |     53,200    |    64.8%    |
| Flip-Flops            |     18,961     |    106,400    |    17.8%    |
| DSPs                  |       210      |      220      |  **95.5%**  |
| BRAMs                 |        2       |      140      |     1.4%    |
| **Inference Latency** | **197 cycles** | **@ 100 MHz** |  **2.0 µs** |

---

## Model Architecture

<p align="center">
  <img src="https://github.com/user-attachments/assets/1edbdb61-a2b0-45ba-b684-b1652246617a"
       alt="SE-ECG Architecture"
       width="520">
</p>

The network processes `(140, 1)` ECG inputs through three main stages.

### 1. Temporal Encoder

Three time-distributed Dense layers with BatchNormalization, ReLU activations, and a residual skip connection produce:

```text
R ∈ ℝ^(140×16)
```

### 2. Squeeze-and-Excitation Channel Attention

Global Average Pooling reduces the temporal dimension:

```text
(140, 16) → (16,)
```

The SE block then applies:

```text
Dense(8, ReLU)
        ↓
Dense(16, Sigmoid)
        ↓
Channel attention
```

The attended representation is combined through a residual operation.

### 3. Classification Head

A final `Dense(2)` layer produces raw class logits.

The **Softmax layer is intentionally excluded from the FPGA sub-model** because of the hls4ml 1.3.0 C-simulation behavior documented below.

### Architecture Summary

| Layer                          | Output Shape | Parameters |
| ------------------------------ | -----------: | ---------: |
| Input                          |   `(140, 1)` |          0 |
| Dense(16) + BN + ReLU          |  `(140, 16)` |         96 |
| Dense(32) + BN + ReLU          |  `(140, 32)` |        672 |
| Dense(16) + Add + BN           |  `(140, 16)` |        592 |
| GlobalAveragePooling1D         |      `(16,)` |          0 |
| Dense(8, ReLU) — SE squeeze    |       `(8,)` |        136 |
| Dense(16, Sigmoid) — SE excite |      `(16,)` |        144 |
| Multiply + Add                 |      `(16,)` |          0 |
| **Dense(2) — FPGA boundary**   |   **`(2,)`** |     **34** |
| Softmax                        |       `(2,)` |          0 |
| **Total**                      |              |  **1,674** |

---

## Why SE Attention After Global Average Pooling?

The SE block is applied to the post-pooled `(16,)` representation rather than directly to the `(140,16)` feature map.

This allows the attention weights and feature vector to have identical shapes during the element-wise operations:

```text
Global Average Pooling
        ↓
     (16,)
        ↓
   SE Attention
        ↓
     (16,)
```

This avoids tensor-broadcast operations that were problematic during the hls4ml 1.3.0 conversion workflow.

---

## Dataset

The project uses the **ECG5000** dataset from the UCR Time Series Classification Archive.

Each sample contains a **140-step single-channel ECG heartbeat segment** with a binary Normal/Anomaly label.

### Dataset Statistics

| Split     |   Total   |     Normal    |    Anomaly    |
| --------- | :-------: | :-----------: | :-----------: |
| Training  |    500    |  292 (58.4%)  |  208 (41.6%)  |
| Test      |   4,500   | 2,627 (58.4%) | 1,873 (41.6%) |
| **Total** | **5,000** |   **2,919**   |   **2,081**   |

Dataset source:

https://www.cs.ucr.edu/~eamonn/time_series_data_2018/

---

## Repository Structure

```text
ecg-fpga-se-networks/
│
├── notebook/
│   └── ECG_FPGA_final.ipynb
│       # Complete pipeline: training → hls4ml → evaluation
│
├── src/
│   ├── config.py
│   ├── data.py
│   ├── model.py
│   ├── train.py
│   ├── evaluate.py
│   ├── fpga_deploy.py
│   └── main.py
│
├── figures/
│   └── # Generated plots and evaluation figures
│
├── weights/
│   └── Model_weights/
│       # Saved Keras weights
│
├── hls_project/
│   ├── hls_ecg_main/
│   │   # ap_fixed<24,12>, RF=1
│   └── hls_ecg_light/
│       # ap_fixed<12,6>, RF=1
│
├── data/
│   └── README.md
│
├── paper/
│   └── paper.tex
│
├── README.md
└── LICENSE
```

---

## Setup and Installation

### Prerequisites

* Python ≥ 3.9
* CUDA-enabled GPU recommended
* NVIDIA T4 tested through Google Colab
* Xilinx Vivado/Vivado HLS for FPGA synthesis

### Clone the Repository

```bash
git clone https://github.com/niteshg97/ecg-fpga-se-networks.git
cd ecg-fpga-se-networks
```

### Install Dependencies

```bash
pip install tensorflow==2.20
pip install tf_keras
pip install hls4ml[profiling]==1.3.0
pip install scikit-learn matplotlib seaborn aeon
```

#### Compatibility Note

The hls4ml 1.3.0 conversion workflow uses the V2 graph parser and requires the legacy `tf_keras` interface for the model conversion used in this project.

See `src/fpga_deploy.py` for the compatibility configuration.

---

## Data Preparation

The ECG5000 dataset is automatically downloaded through `aeon` in the provided notebook.

```bash
pip install aeon
```

The notebook handles dataset download and preprocessing.

For local copies, place the dataset files under:

```text
data/
├── ECG5000_TRAIN.txt
└── ECG5000_TEST.txt
```

---

## Usage

### Run the Full Pipeline

Open the notebook:

```bash
jupyter notebook notebook/ECG_FPGA_final.ipynb
```

The notebook covers:

```text
Dataset
   ↓
Preprocessing
   ↓
Model Training
   ↓
Evaluation
   ↓
Fixed-Point Precision Sweep
   ↓
hls4ml Conversion
   ↓
C-Simulation
   ↓
Hardware Validation
```

---

### Run the Modular Pipeline

#### Full pipeline

```bash
python src/main.py
```

#### Skip training

```bash
python src/main.py --skip-training
```

#### Skip precision sweep

```bash
python src/main.py --skip-sweep
```

#### Run Vivado synthesis

```bash
python src/main.py --synth
```

> FPGA synthesis requires the appropriate Xilinx Vivado/Vivado HLS environment to be installed and available in `PATH`.

---

## Load Pre-trained Weights

```python
import tf_keras as keras
from src.model import build_se_ecg_model, extract_logit_model

# Rebuild architecture
model = build_se_ecg_model()

# Load trained weights
model.load_weights(
    "weights/Model_weights/best_model.weights.h5"
)

# Extract logit model for FPGA conversion
logit_model = extract_logit_model(model)
```

---

## Training Configuration

| Hyperparameter          | Value                      |
| ------------------------ | --------------------------- |
| Optimizer               | Adam                       |
| Learning Rate           | `5 × 10⁻⁴`                 |
| Batch Size              | 32                         |
| Maximum Epochs          | 60                         |
| LR Reduction Factor     | 0.5                        |
| LR Reduction Patience   | 5 epochs                   |
| Early Stopping Patience | 12 epochs                  |
| Normal Class Weight     | 0.856                      |
| Anomaly Class Weight    | 1.202                      |
| Random Seeds            | 42, 123, 456, 789, 2024    |
| Framework               | TensorFlow 2.20 / tf_keras |
| Training Hardware       | NVIDIA T4                  |

---

## FPGA Deployment with hls4ml

### hls4ml Softmax Inference Issue

During the hls4ml 1.3.0 C-simulation workflow, a discrepancy was observed when the Softmax layer was included in the FPGA-converted model.

The fixed-point exponential lookup table produced normalized probabilities, while the resulting argmax decisions could differ from the float32 reference depending on the model's weight distribution.

#### Approach Used

Instead of converting the complete model including Softmax:

```text
 Full Model
Dense(2)
   ↓
Softmax
   ↓
hls4ml
```

the project converts only the logit-producing sub-model:

```text
 FPGA Model
Dense(2)
   ↓
hls4ml
   ↓
FPGA logits
   ↓
Numerically stable Softmax
```

This approach achieved **99.9% logic fidelity (999/1000 predictions)** for the reported hardware/software comparison.
Related hls4ml issue:
https://github.com/fastmachinelearning/hls4ml/issues/1443

---

### Stable Softmax

```python
import numpy as np

def numpy_softmax(logits):
    """Numerically stable softmax."""
    e = np.exp(
        logits - logits.max(axis=1, keepdims=True)
    )
    return e / e.sum(axis=1, keepdims=True)
```

The FPGA conversion terminates at the Dense(2) logit layer:

```python
hls_model = hls4ml.converters.convert_from_keras_model(
    logit_model,
    hls_config=config,
    output_dir="hls_project/hls_ecg_main",
    part="xc7z020clg400-1"
)

hls_model.compile()

hw_logits = hls_model.predict(
    np.ascontiguousarray(X_test, dtype=np.float32)
)

hw_proba = numpy_softmax(hw_logits)
```

---

## hls4ml Configuration

```python
config = hls4ml.utils.config_from_keras_model(
    logit_model,
    granularity="name",
    default_precision="ap_fixed<24,12>"
)

for layer in config["LayerName"]:
    config["LayerName"][layer]["Strategy"] = "Latency"
    config["LayerName"][layer]["ReuseFactor"] = 1
```

| Parameter             | Value             |
| ---------------------- | ------------------ |
| Target Device         | `xc7z020clg400-1` |
| hls4ml                | 1.3.0             |
| Fixed-Point Precision | `ap_fixed<24,12>` |
| Reuse Factor          | 1                 |
| Strategy              | Latency           |
| Converted Model       | Logit sub-model   |
| Clock Target          | 100 MHz           |

---

## Vivado RTL Synthesis

After hls4ml conversion and C-simulation:

```python
hls_model.build(
    csim=False,
    synth=True,
    export=False
)

report = hls4ml.report.read_vivado_report(
    "hls_project/hls_ecg_main"
)

print(report)
```

The reported synthesis configuration targets:

```text
Device : xc7z020clg400-1
Clock  : 100 MHz
Latency: 197 cycles
         ≈ 2.0 µs
```

---

## Related Work

| Work                                                                                                   | Venue                             | Relevance                  |
| -------------------------------------------------------------------------------------------------------| ---------------------------------- | --------------------------- |
| [Fast inference of DNNs in FPGAs for particle physics](https://doi.org/10.1088/1748-0221/13/07/P07027) | JINST 2018                        | Original hls4ml work       |
| [hls4ml: An open-source codesign workflow](https://github.com/fastmachinelearning/hls4ml)              | FPGA 2021                         | hls4ml framework           |
| [Fast CNNs on FPGAs with hls4ml](https://doi.org/10.1088/2632-2153/ac0ea1)                              | MLST 2021                         | CNN inference with hls4ml  |
| [Automatic heterogeneous quantization](https://doi.org/10.1038/s42256-021-00356-5)                      | Nature Machine Intelligence 2021  | Mixed-precision hls4ml     |
| [Squeeze-and-Excitation Networks](https://doi.org/10.1109/TPAMI.2019.2913372)                           | IEEE TPAMI 2020                   | SE channel attention        |
| [Cardiologist-level arrhythmia detection](https://doi.org/10.1038/s41591-018-0268-3)                    | Nature Medicine 2019              | ECG deep learning          |
| [ECG heartbeat classification](https://doi.org/10.1109/ICHI.2018.00012)                                 | ICHI 2018                         | ECG classification         |

---

## Citation

If you use this repository or the associated research work, please cite the Zenodo preprint:

```bibtex
@misc{kumar2026hardware_efficient_ecg_fpga,
  author       = {Kumar, Nitesh and Kumar, Ashwani},
  title        = {Hardware-Efficient Squeeze-and-Excitation Networks
                  for Real-Time ECG Anomaly Detection Using hls4ml on FPGAs},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.22910536},
  url          = {https://doi.org/10.5281/zenodo.22910536},
  version      = {1.0},
  type         = {Preprint}
}
```

---

## License

This project is licensed under the **MIT License**.
See the [`LICENSE`](LICENSE) file for details.

---

## Acknowledgements

* The [`hls4ml`](https://fastmachinelearning.org/hls4ml/) community for the open-source ML-to-FPGA codesign framework.
* The **UCR Time Series Classification Archive** for the ECG5000 benchmark.
* **National Institute of Technology Patna**, Department of Electrical Engineering.

---

<p align="center">
<b>Hardware-Efficient Deep Learning for FPGA-Based Edge AI</b>
<br><br>
Made with ❤️ at NIT Patna
<br><br>
<a href="mailto:niteshk.ug23.ee@nitp.ac.in">niteshk.ug23.ee@nitp.ac.in</a>
&nbsp; · &nbsp;
<a href="mailto:ashwani@nitp.ac.in">ashwani@nitp.ac.in</a>
</p>

"""
model.py
--------
SE-ECG model architecture.

Design decisions for hls4ml FPGA compatibility
-----------------------------------------------
1. SE attention is placed AFTER GlobalAveragePooling1D so that all
   Multiply / Add operations act on same-shape (C,) vectors.
   Pre-pooling SE would require broadcasting (C,) weights across
   (L, C) feature maps — a pattern hls4ml 1.3.0 mishandles silently.

2. The softmax activation is implemented as a *separate* Keras layer
   so that extract_logit_model() can strip it without touching weights.
   hls4ml 1.3.0 contains a softmax normalization defect in C-simulation;
   the fix is to convert only the logit sub-model and apply softmax in
   Python post-processing.
"""

import tf_keras as keras
from tf_keras.layers import (
    Input, Dense, GlobalAveragePooling1D,
    BatchNormalization, Activation, Multiply, Add
)
from tf_keras.models import Model


# ── Model builder ─────────────────────────────────────────────────────────────

def build_se_ecg_model(n_timesteps=140, embed_dim=16,
                       ffn_dim=32, se_dim=8, n_classes=2):
    """
    Build the hardware-aware SE-ECG model.

    Architecture
    ------------
    Input (L, 1)
      → Embedding  : Dense(C) + BN + ReLU          [time-distributed]
      → FFN        : Dense(2C) + BN + ReLU
                     Dense(C)  + residual Add + BN  [time-distributed]
      → GAP        : GlobalAveragePooling1D          → (C,)
      → SE Squeeze : Dense(r, relu)                  → (r,)
      → SE Excite  : Dense(C, sigmoid)               → (C,)
      → SE Scale   : Multiply + residual Add         → (C,)
      → Logits     : Dense(K)                        → (K,)   ← FPGA boundary
      → Output     : Softmax                         → (K,)   ← training only

    Args:
        n_timesteps : ECG window length L (default 140).
        embed_dim   : Channel dimension C (default 16).
        ffn_dim     : FFN expansion dimension (default 32).
        se_dim      : SE bottleneck dimension r (default 8).
        n_classes   : Number of output classes K (default 2).

    Returns:
        tf_keras.Model — full training model (with softmax).
    """
    inputs = Input(shape=(n_timesteps, 1), name="ecg_input")

    # ── Temporal embedding ────────────────────────────────────────────────
    x = Dense(embed_dim, name="embedding")(inputs)
    x = BatchNormalization(name="emb_bn")(x)
    x = Activation("relu", name="emb_relu")(x)

    # ── Feed-forward network with residual skip ───────────────────────────
    ffn = Dense(ffn_dim, name="ffn1")(x)
    ffn = BatchNormalization(name="ffn_bn1")(ffn)
    ffn = Activation("relu", name="ffn_relu")(ffn)
    ffn = Dense(embed_dim, name="ffn2")(ffn)
    x   = Add(name="ffn_add")([x, ffn])
    x   = BatchNormalization(name="final_bn")(x)

    # ── Global average pooling: (N, L, C) → (N, C) ───────────────────────
    z = GlobalAveragePooling1D(name="global_pool")(x)

    # ── SE channel attention (all ops on (C,) — no broadcasting) ─────────
    s         = Dense(se_dim,    activation="relu",    name="se_dense1")(z)
    s         = Dense(embed_dim, activation="sigmoid", name="se_dense2")(s)
    attended  = Multiply(name="se_mult")([z, s])
    h         = Add(name="se_add")([z, attended])

    # ── Output ────────────────────────────────────────────────────────────
    # 'output_logits' is the FPGA conversion boundary.
    # 'output' (softmax) is excluded from the hls4ml model.
    logits  = Dense(n_classes, name="output_logits")(h)
    outputs = Activation("softmax", name="output")(logits)

    return Model(inputs, outputs, name="se_ecg_model")


def extract_logit_model(trained_model):
    """
    Extract the logit sub-model from a trained SE-ECG model.

    The logit sub-model terminates at 'output_logits' (Dense(K)) and
    excludes the softmax activation. This is the model passed to hls4ml
    for FPGA conversion.

    Weights are shared — not duplicated — so extracting the sub-model
    does not require saving and reloading.

    Args:
        trained_model : Full trained Keras model (with softmax).

    Returns:
        tf_keras.Model terminating at 'output_logits'.
    """
    logit_output = trained_model.get_layer("output_logits").output
    return Model(
        inputs=trained_model.input,
        outputs=logit_output,
        name="logit_model"
    )


def print_model_summary(model):
    """Print model summary with trainable / non-trainable parameter counts."""
    model.summary()
    total       = model.count_params()
    trainable   = sum(int(w.numpy().size) for w in model.trainable_weights)
    non_trainable = total - trainable
    print(f"\n  Total params      : {total:>6,}")
    print(f"  Trainable params  : {trainable:>6,}")
    print(f"  Non-trainable     : {non_trainable:>6,}  (BatchNorm running stats)\n")

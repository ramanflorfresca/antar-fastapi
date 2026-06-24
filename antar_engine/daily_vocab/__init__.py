"""
antar_engine.daily_vocab — Concrete Daily Vocabulary Layer.

Adds a deterministic, conviction-gated `concrete` block (body / food / mood /
romance / direction / color / timing / soft event-watch) on top of signals the
daily engine already computes. Python composes the concrete claim; the layer
emits structured fields. No LLM in this package.

Kill switch (matches today_precision.py / DAILY_PRECISION_V2 house style):
    DAILY_VOCAB = shadow | on | primary | off   (default: shadow)
"""

from __future__ import annotations

import os

from antar_engine.daily_vocab.compose import (
    compute_concrete_block,
    public_view,
    populated_fields,
)


def is_enabled() -> bool:
    """True when the layer should compute. Default 'shadow' = compute & attach
    (additive; never overwrites a shipped field). Set DAILY_VOCAB=off to disable."""
    return (os.environ.get("DAILY_VOCAB", "shadow") or "shadow").lower() \
        in ("shadow", "on", "primary")


__all__ = ["compute_concrete_block", "public_view", "populated_fields", "is_enabled"]

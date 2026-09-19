"""Reader Signal Store subdomain (ANES v2, roadmap Phase 5.6).

The REAL-signal counterpart to the predicted reader-simulation: it loads external
ground-truth (platform 订阅/追读/掉粉/打赏) imported under sources/reader-signals/,
and folds a real signal beside a prediction into a comparison-only, never-gating
diagnostic. It WIRES the seam a future real-publish calibration will consume, but
NEVER calibrates the model itself (roadmap: schema + loader + reconcile, not
calibration). Reads only; never writes facts (ADR-006, fitness guard #20).
"""
from .loader import (signals_dir, load_reader_signals, signal_for_chapter,
                     validate_signal)
from .reconcile import reconcile_signal

__all__ = ["signals_dir", "load_reader_signals", "signal_for_chapter",
           "validate_signal", "reconcile_signal"]

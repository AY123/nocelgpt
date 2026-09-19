"""Outline Bootstrap runtime.

This subdomain turns 1-5 external reference novels into derived analysis and a
new, original novel outline. Reference sources are never registry facts; they are
inputs that produce derived artifacts and optional fact import plans.
"""

from .sources import ReferenceSource, SourceCheckResult, load_reference_sources

__all__ = ["ReferenceSource", "SourceCheckResult", "load_reference_sources"]

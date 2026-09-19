"""Market Intelligence subdomain (ANES v2, roadmap P0).

Turns dated market OBSERVATIONS a project supplies into a PINNED Market Snapshot
(Market DSL). It is deliberately NOT a live crawler: a live data source would
poison the "same input -> same output" reproducibility discipline the rest of
the system depends on. Observations are inputs (like reference novels); the
snapshot is a versioned, staleness-aware derived artifact — never a fact.
"""

from .sources import MarketObservation, load_market_observations

__all__ = ["MarketObservation", "load_market_observations"]

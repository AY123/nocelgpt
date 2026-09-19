"""Market Positioning subdomain (ANES v2, roadmap 4.5).

The Market Position is the AUTHORED commercial thesis of a book, written BEFORE
it is opened: the target reader segment, the trope map (lean-on vs subvert), and
the concrete commercial promise (pay trigger / first-30-chapter hook / 100-chapter
sustainability). Like the Novel Brain it is an authored input under sources/,
never a fact (ADR-006) or a projection (ADR-008).

Its consumer ships on day one: the pre-book ADMISSION check — a deterministic
fold of the Position + the Novel Brain + the derived Market Snapshot into an
advisory recommendation (admit / revise / hold). The check introduces no new
judgment model (fixture-validated, no live model), never gates a build (ADR-003),
and stages a recommendation toward a human (ADR-009) — opening a book is an
outward, hard-to-reverse commitment only a human makes.
"""
from .loader import (position_path, load_position, validate_position)
from .admission import build_admission, project_admission, write_admission
from .generate import build_position, write_position, position_yaml

__all__ = ["position_path", "load_position", "validate_position",
           "build_admission", "project_admission", "write_admission",
           "build_position", "write_position", "position_yaml"]

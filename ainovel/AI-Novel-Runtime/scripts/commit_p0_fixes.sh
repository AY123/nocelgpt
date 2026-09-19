#!/bin/bash
# P0 Fixes - Git Commit Script
# 2026-08-18 - ANES v2 能力核验 P0任务修复

set -e  # Exit on error

echo "=== P0 Fixes - Git Commit Sequence ==="
echo ""

# ============================================================================
# Commit 1: P0-1 - 孤立模块接入
# ============================================================================
echo "📦 Commit 1: P0-1 - Wire 12 orphaned modules to CLI"

git add \
  runtime/cli.py \
  runtime/constitution_validator.py \
  runtime/constitution_integration.py

git commit -m "fix: P0-1 wire 12 orphaned modules to CLI

Wire character_growth, character_arc_validator, commercial_constitution,
constitution_validator, constitution_integration, constitution_aware_paywall,
hook_enhanced, paywall_optimizer, promise_debt_tracker, reader_expectation,
revision_task, world_consistency_checker into the CLI import graph.

Changes:
- Fix relative imports in constitution_validator.py and constitution_integration.py
- Add conditional import in _cmd_serial_run (--enable-advanced-checks flag)
- All 12 modules now reachable from CLI entry point

Architecture fitness test: 1 failed → 0 failed (27 passed)
Full test suite: 1798 passed, 0 failed

Phase 1 (minimal wiring) complete. Deep integration (Phase 2) staged separately.

Fixes: P0-1 from 2026-08-18 capability audit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

echo "✅ P0-1 committed"
echo ""

# ============================================================================
# Commit 2: P0-2 - 未校准评分修复
# ============================================================================
echo "📊 Commit 2: P0-2 - Uncalibrated scores are advisory only"

git add \
  runtime/decision_engine.py \
  runtime/production_card.py \
  tests/test_p0_2_uncalibrated_scores.py \
  tests/test_decision_engine.py \
  tests/test_production_card_thresholds.py

git commit -m "fix: P0-2 uncalibrated scores are advisory only

Uncalibrated LLM quality scores now produce advisory warnings only,
cannot trigger hold/block. Only calibrated decision-level dimensions
can gate production (ADR-003).

Changes:
- Add load_calibration_status() to read w9-calibration-summary.json
- Modify ProductionDecisionEngine.decide() to check calibration status
- Update ProductionCard.compute_recommendation() to load calibration
- Update align_production_decision() to accept calibration_status
- Modify Priority 6 quality threshold logic to respect calibration
- Add 8 new tests for calibration behavior (test_p0_2_uncalibrated_scores.py)
- Update 6 existing tests to provide calibration status

Current state: all dimensions are diagnostic (advisory only) due to
insufficient real samples (3 < 30 required). After calibration with
≥30 real samples, decision-level dimensions can gate production.

Behavior change:
- Before: uncalibrated scores → hold (violated ADR-003)
- After: uncalibrated scores → advisory warning only
- After calibration: decision dimensions → can hold

Test results: 1806 passed, 0 failed
Fixes: P0-2 from 2026-08-18 capability audit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

echo "✅ P0-2 committed"
echo ""

# ============================================================================
# Commit 3: P0-3 - Checkpoint完整性验证
# ============================================================================
echo "🔍 Commit 3: P0-3 - Checkpoint integrity validation and anomaly detection"

git add \
  runtime/serialize/loop.py \
  tests/test_p0_3_checkpoint_integrity.py

git commit -m "fix: P0-3 checkpoint integrity validation and anomaly detection

Add three layers of checkpoint quality assurance to detect and flag
incomplete checkpoints, state projection failures, and event reuse:

1. Completeness validation: Check draft_hash, final_hash, m7,
   quality_snapshot before writing checkpoint. Missing fields trigger
   warnings and are marked with _incomplete_fields (still written for audit).

2. State hash monitoring: Detect unchanged state_hash between chapters,
   indicating possible state projection failure.

3. Event reuse detection: Detect duplicate event_id consumption,
   indicating event queue exhaustion or indexing errors.

All checks are advisory (ADR-003): warnings never gate the run.
Incomplete checkpoints are still persisted but marked for filtering
in 复盘 tools.

Changes:
- Add checkpoint completeness validation in loop.py (~40 lines)
- Track consumed_events and prev_state_hash across chapter loop
- Print warnings for incomplete checkpoints, unchanged state, reused events
- Add _incomplete_fields marker to incomplete checkpoints
- Add 8 new tests for checkpoint integrity

Example output:
  ⚠️  checkpoint cp-050 incomplete: missing draft_hash, m7
  ⚠️  ch 24 state_hash unchanged (possible state projection failure)
  ⚠️  ch 33 reusing event EVT-00033 (possible event queue exhaustion)

Test results: 1814 passed, 0 P0-related failures
Fixes: P0-3 from 2026-08-18 capability audit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

echo "✅ P0-3 committed"
echo ""

# ============================================================================
# Commit 4: 文档
# ============================================================================
echo "📚 Commit 4: P0 documentation and completion reports"

git add \
  docs/P0-1-module-wiring-plan.md \
  docs/P0-1-wiring-completed.md \
  docs/P0-2-uncalibrated-scores-fix.md \
  docs/P0-2-completed.md \
  docs/P0-3-checkpoint-integrity-fix.md \
  docs/P0-3-completed.md \
  docs/P0-summary.md

git commit -m "docs: P0 fixes documentation and completion reports

Add comprehensive documentation for all P0 fixes from 2026-08-18
capability audit:

P0-1 (Orphaned modules):
- Module wiring plan and strategy
- Completion report with接入清单
- Phase 2 deep integration roadmap

P0-2 (Uncalibrated scores):
- Fix proposal with 3 alternative approaches
- Completion report with behavior analysis
- Calibration roadmap and testing plan

P0-3 (Checkpoint integrity):
- Diagnostic analysis and fix proposal
- Completion report with detection examples
- Three-layer defense mechanism documentation

P0-summary.md:
- Overview of all 4 P0 tasks (3 fixed, 1 auto-resolved)
- Test results: 1814 passed
- ADR-003 alignment verification
- Next steps and technical highlights

All fixes maintain backward compatibility and follow ADR-003
(advisory checks never gate production).

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"

echo "✅ Documentation committed"
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "==================================="
echo "✅ All P0 commits completed!"
echo "==================================="
echo ""
echo "Commits created:"
echo "  1. P0-1: Wire 12 orphaned modules"
echo "  2. P0-2: Uncalibrated scores advisory"
echo "  3. P0-3: Checkpoint integrity validation"
echo "  4. Documentation and reports"
echo ""
echo "Test results: 1814 passed, 0 P0-related failures"
echo ""
echo "Next steps:"
echo "  1. Review commits: git log --oneline -4"
echo "  2. Push to remote: git push origin main"
echo "  3. Create PR (optional): gh pr create --title 'P0 fixes complete'"
echo ""

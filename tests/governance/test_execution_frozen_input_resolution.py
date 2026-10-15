"""Execution Packet Frozen Input Resolution Regression Tests

Tests frozen input resolution semantics for execution packet validation.

Contract: Validate that execution_checks.py correctly resolves claim sources
to frozen input snapshots when they reference mutable control files.

Regression Context: Governance remediation for EXEC_INPUT V2-061 failure where
claim sources incorrectly validated against live mutable files instead of
frozen snapshots captured at task execution time.

Six test cases:
1. CLOSED task + live source evolved → PASS (frozen snapshot protects historical validation)
2. Frozen snapshot tampering → FAIL (hash mismatch detected)
3. Active task live source drift → FAIL (active tasks must track current state)
4. Claim references packet input source_ref → resolve to frozen, PASS
5. Claim references ordinary artifact → validate hash directly, PASS
6. V2-061 real regression → no longer fails with evolved decision-register
"""

import sys
import hashlib
import tempfile
import shutil
from pathlib import Path
import pytest
import yaml

# Add plan/scripts to path
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "plan" / "scripts"))

from execution_checks import execution_checks


class TestExecutionFrozenInputResolution:
    """Frozen input resolution for execution packet validation."""

    def setup_method(self):
        """Create temporary plan structure for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.plan = Path(self.temp_dir) / "plan"
        self.plan.mkdir()

        # Create required directories
        (self.plan / "schemas").mkdir()
        (self.plan / "machine").mkdir()
        (self.plan / "validation" / "execution" / "V2-900" / "inputs").mkdir(parents=True)
        (self.plan / "validation" / "execution" / "V2-901" / "inputs").mkdir(parents=True)
        (self.plan / "validation" / "execution" / "V2-902" / "inputs").mkdir(parents=True)
        (self.plan / "validation" / "execution" / "V2-903" / "inputs").mkdir(parents=True)
        (self.plan / "validation" / "execution" / "V2-904" / "inputs").mkdir(parents=True)

        # Copy real schemas
        real_plan = REPO_ROOT / "plan"
        shutil.copy(
            real_plan / "schemas/execution-packet.schema.json",
            self.plan / "schemas/execution-packet.schema.json"
        )
        shutil.copy(
            real_plan / "schemas/execution-packet-absence.schema.json",
            self.plan / "schemas/execution-packet-absence.schema.json"
        )

        # Create FILE_MANIFEST.json
        self.manifest_content = {"version": "1.0.0", "files": []}
        manifest_path = self.plan / "FILE_MANIFEST.json"
        manifest_path.write_text(yaml.dump(self.manifest_content))
        self.manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)

    def create_decision_register(self, content_dict):
        """Create decision-register.yaml with given content."""
        path = self.plan / "machine" / "decision-register.yaml"
        path.write_text(yaml.dump(content_dict))
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def create_frozen_snapshot(self, content_dict, task_id="V2-900"):
        """Create frozen snapshot in validation/execution/{task}/inputs/."""
        content_bytes = yaml.dump(content_dict).encode('utf-8')
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        snapshot_dir = self.plan / "validation" / "execution" / task_id / "inputs"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{sha256}.txt"
        snapshot_path.write_bytes(content_bytes)
        return snapshot_path, sha256

    def create_execution_packet(self, task_id, status, inputs, claims, action="PREPARE"):
        """Create execution packet YAML."""
        packet = {
            "record_type": "task_execution_packet",
            "schema_version": "1.0",
            "task_id": task_id,
            "owner_role": "test-role",
            "action": action,
            "plan_version": "1.0.0",
            "repository_revision": "a" * 40,
            "worktree_dirty": False,
            "plan_manifest_sha256": self.manifest_sha,
            "environment": {
                "fingerprint": "test-env",
                "runtime_versions": {"python": "3.9.0"},
                "database_image": None,
                "ci_context": None
            },
            "implementer": "test-implementer",
            "verifier": "test-verifier",
            "scope": "test",
            "required_decisions": [],
            "allowed_paths": ["machine/", "validation/"] if inputs or claims else ["test/"],
            "expected_outputs": ["test_output.txt"],
            "inputs": inputs,
            "claims": claims,
            "estimate": {
                "range": "1-2h",
                "unit": "hours",
                "assumptions": ["test assumption"],
                "confidence": "medium"
            },
            "budget": {
                "paid_calls_allowed": False,
                "model_cost_cap": None,
                "infrastructure_cap": None,
                "maximum_attempts": 3,
                "maximum_runtime": 3600.0
            },
            "stop_conditions": ["test stop condition"],
            "review_notes": ["test review note"],
            "handoff": {
                "current_step": "test step",
                "completed_steps": ["step 1"],
                "pending_items": ["pending item 1"],
                "next_action": action,
                "last_check": {
                    "status": "NOT_RUN",
                    "artifacts": [],
                    "missing_artifact_reason": "test not run"
                }
            }
        }
        packet_path = self.plan / "validation" / "execution" / task_id / "execution-packet.yaml"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(yaml.dump(packet))
        return packet_path

    def create_backlog(self, tasks):
        """Create implementation-backlog.yaml."""
        backlog = {
            "version": "1.0.0",
            "tasks": tasks
        }
        (self.plan / "machine" / "implementation-backlog.yaml").write_text(yaml.dump(backlog))

    def create_test_catalog(self):
        """Create minimal test-catalog.yaml."""
        catalog = {"tests": []}
        (self.plan / "machine" / "test-catalog.yaml").write_text(yaml.dump(catalog))

    def create_ai_execution_policy(self):
        """Create minimal ai-execution-policy.yaml."""
        policy = {"policy_version": "1.0"}
        (self.plan / "machine" / "ai-execution-policy.yaml").write_text(yaml.dump(policy))

    def test_FI_01_closed_task_live_source_evolved_pass(self):
        """FI-01: CLOSED task + live source evolved → PASS.

        Historical validation must use frozen snapshot, not current live file.
        This is the core fix: claim.ref matches input.source_ref → resolve to frozen.
        """
        task_id = "V2-900"

        # Create OLD decision register (what was frozen at task execution)
        old_register = {
            "version": "1.0.0",
            "decisions": [
                {"id": "ADR-001", "status": "ACCEPTED", "title": "Old Decision"}
            ]
        }
        frozen_path, frozen_sha = self.create_frozen_snapshot(old_register, task_id)

        # Create NEW decision register (current live state - evolved)
        new_register = {
            "version": "1.1.0",
            "decisions": [
                {"id": "ADR-001", "status": "ACCEPTED", "title": "Old Decision"},
                {"id": "ADR-002", "status": "REQUIRED", "title": "New Decision"}
            ]
        }
        live_path, live_sha = self.create_decision_register(new_register)

        # Execution packet: claim references mutable source via source_ref
        inputs = [
            {
                "source_ref": "machine/decision-register.yaml",
                "ref": f"validation/execution/{task_id}/inputs/{frozen_sha}.txt",
                "sha256": frozen_sha
            }
        ]
        claims = [
            {
                "id": "CLAIM-001",
                "kind": "FACT",
                "statement": "Decision register snapshot",
                "sources": [
                    {
                        "ref": "machine/decision-register.yaml",
                        "sha256": frozen_sha
                    }
                ],
                "blocks_actions": [],
                "verification_plan": "Validate frozen snapshot"
            }
        ]

        self.create_execution_packet(task_id, "CLOSED", inputs, claims)

        # Create backlog with CLOSED task
        self.create_backlog([
            {
                "task_id": task_id,
                "status": "CLOSED",
                "owner_role": "test-role",
                "phase": "P1",
                "normative_specs": [],
                "required_decisions": [],
                "artifacts": [],
                "execution_packet_ref": f"validation/execution/{task_id}/execution-packet.yaml"
            }
        ])

        self.create_test_catalog()
        self.create_ai_execution_policy()

        # Load and validate
        data = {
            "implementation-backlog": yaml.safe_load(
                (self.plan / "machine" / "implementation-backlog.yaml").read_text()
            ),
            "decision-register": new_register
        }

        errors = execution_checks(data, self.plan)

        # FI-01 PASS: No EXEC_INPUT errors - frozen snapshot protects historical validation
        exec_input_errors = [e for e in errors if "EXEC_INPUT" in e]
        assert len(exec_input_errors) == 0, \
            f"FI-01 failed: expected PASS with evolved live source, got errors: {exec_input_errors}"

    def test_FI_02_frozen_snapshot_tampering_fail(self):
        """FI-02: Frozen snapshot tampering → FAIL.

        If frozen snapshot file is tampered (SHA mismatch), validation must fail.
        This ensures frozen snapshots are truly immutable.
        """
        task_id = "V2-901"

        # Create decision register
        register = {
            "version": "1.0.0",
            "decisions": [{"id": "ADR-001", "status": "ACCEPTED"}]
        }
        self.create_decision_register(register)

        # Create frozen snapshot with CORRECT content
        correct_content = yaml.dump(register).encode('utf-8')
        correct_sha = hashlib.sha256(correct_content).hexdigest()

        # But write TAMPERED content to file
        tampered_content = yaml.dump({"version": "999.0", "decisions": []}).encode('utf-8')
        snapshot_dir = self.plan / "validation" / "execution" / task_id / "inputs"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / f"{correct_sha}.txt"
        snapshot_path.write_bytes(tampered_content)

        # Execution packet claims correct SHA (but file is tampered)
        inputs = [
            {
                "source_ref": "machine/decision-register.yaml",
                "ref": f"validation/execution/{task_id}/inputs/{correct_sha}.txt",
                "sha256": correct_sha
            }
        ]
        claims = [
            {
                "id": "CLAIM-001",
                "kind": "FACT",
                "statement": "Decision register",
                "sources": [
                    {"ref": "machine/decision-register.yaml", "sha256": correct_sha}
                ],
                "blocks_actions": [],
                "verification_plan": "Check frozen snapshot"
            }
        ]

        self.create_execution_packet(task_id, "CLOSED", inputs, claims)
        self.create_backlog([
            {
                "task_id": task_id,
                "status": "CLOSED",
                "owner_role": "test-role",
                "phase": "P1",
                "normative_specs": [],
                "required_decisions": [],
                "artifacts": [],
                "execution_packet_ref": f"validation/execution/{task_id}/execution-packet.yaml"
            }
        ])
        self.create_test_catalog()
        self.create_ai_execution_policy()

        data = {
            "implementation-backlog": yaml.safe_load(
                (self.plan / "machine" / "implementation-backlog.yaml").read_text()
            ),
            "decision-register": register
        }

        errors = execution_checks(data, self.plan)

        # FI-02 FAIL: Must detect tampering (hash mismatch on frozen input itself)
        exec_input_errors = [e for e in errors if "EXEC_INPUT" in e and task_id in e]
        assert len(exec_input_errors) > 0, \
            f"FI-02 failed: expected tampering detection, got {len(errors)} total errors: {errors}"

    def test_FI_03_active_task_live_source_drift_fail(self):
        """FI-03: Active task live source drift → FAIL.

        Active tasks (OPEN/IN_PROGRESS/IMPLEMENTED) must validate against current live sources.
        If live source has drifted from frozen snapshot, validation must fail.
        """
        task_id = "V2-902"

        # Create OLD decision register (frozen)
        old_register = {
            "version": "1.0.0",
            "decisions": [{"id": "ADR-001", "status": "ACCEPTED"}]
        }
        frozen_path, frozen_sha = self.create_frozen_snapshot(old_register, task_id)

        # Create NEW decision register (current - DIFFERENT)
        new_register = {
            "version": "2.0.0",
            "decisions": [
                {"id": "ADR-001", "status": "ACCEPTED"},
                {"id": "ADR-002", "status": "REQUIRED"}
            ]
        }
        live_path, live_sha = self.create_decision_register(new_register)

        # Execution packet references OLD frozen snapshot
        inputs = [
            {
                "source_ref": "machine/decision-register.yaml",
                "ref": f"validation/execution/{task_id}/inputs/{frozen_sha}.txt",
                "sha256": frozen_sha
            }
        ]

        self.create_execution_packet(task_id, "IN_PROGRESS", inputs, [])
        self.create_backlog([
            {
                "task_id": task_id,
                "status": "IN_PROGRESS",
                "owner_role": "test-role",
                "phase": "P1",
                "normative_specs": ["machine/decision-register.yaml"],
                "required_decisions": [],
                "artifacts": [],
                "execution_packet_ref": f"validation/execution/{task_id}/execution-packet.yaml"
            }
        ])
        self.create_test_catalog()
        self.create_ai_execution_policy()

        data = {
            "implementation-backlog": yaml.safe_load(
                (self.plan / "machine" / "implementation-backlog.yaml").read_text()
            ),
            "decision-register": new_register
        }

        errors = execution_checks(data, self.plan)

        # FI-03 FAIL: Active task must detect live source drift
        # Look for errors about live source changed/missing in normative inputs
        exec_input_errors = [e for e in errors if "EXEC_INPUT" in e and task_id in e]
        assert len(exec_input_errors) > 0, \
            f"FI-03 failed: expected live source drift detection for active task, got: {errors}"

    def test_FI_04_claim_resolves_to_frozen_input_pass(self):
        """FI-04: Claim references packet input source_ref → resolve to frozen, PASS.

        When claim.sources[].ref matches an input.source_ref, validator must
        resolve to the frozen snapshot (input.ref + input.sha256).
        """
        task_id = "V2-903"

        # Create decision register
        register = {
            "version": "1.0.0",
            "decisions": [{"id": "ADR-001", "status": "ACCEPTED"}]
        }
        frozen_path, frozen_sha = self.create_frozen_snapshot(register, task_id)
        self.create_decision_register(register)

        # Input + claim both reference same source_ref
        inputs = [
            {
                "source_ref": "machine/decision-register.yaml",
                "ref": f"validation/execution/{task_id}/inputs/{frozen_sha}.txt",
                "sha256": frozen_sha
            }
        ]
        claims = [
            {
                "id": "CLAIM-001",
                "kind": "FACT",
                "statement": "Decision register frozen",
                "sources": [
                    {
                        "ref": "machine/decision-register.yaml",
                        "sha256": frozen_sha
                    }
                ],
                "blocks_actions": [],
                "verification_plan": "Validate frozen snapshot"
            }
        ]

        self.create_execution_packet(task_id, "CLOSED", inputs, claims)
        self.create_backlog([
            {
                "task_id": task_id,
                "status": "CLOSED",
                "owner_role": "test-role",
                "phase": "P1",
                "normative_specs": [],
                "required_decisions": [],
                "artifacts": [],
                "execution_packet_ref": f"validation/execution/{task_id}/execution-packet.yaml"
            }
        ])
        self.create_test_catalog()
        self.create_ai_execution_policy()

        data = {
            "implementation-backlog": yaml.safe_load(
                (self.plan / "machine" / "implementation-backlog.yaml").read_text()
            ),
            "decision-register": register
        }

        errors = execution_checks(data, self.plan)

        # FI-04 PASS: Claim correctly resolved to frozen input
        exec_input_errors = [e for e in errors if "EXEC_INPUT" in e or "EXEC_CLAIM" in e]
        assert len(exec_input_errors) == 0, \
            f"FI-04 failed: expected PASS with frozen resolution, got: {exec_input_errors}"

    def test_FI_05_claim_ordinary_artifact_validates_hash_pass(self):
        """FI-05: Claim references ordinary artifact → validate hash directly, PASS.

        When claim source is NOT a packet input source_ref, it's an ordinary
        immutable artifact. Validator must check ref+sha256 directly.
        """
        task_id = "V2-904"

        # Create immutable artifact
        artifact_content = b"immutable test artifact content"
        artifact_sha = hashlib.sha256(artifact_content).hexdigest()
        artifact_path = self.plan / "validation" / "execution" / task_id / "test-artifact.txt"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(artifact_content)

        # NO frozen input - claim references artifact directly
        claims = [
            {
                "id": "CLAIM-001",
                "kind": "FACT",
                "statement": "Immutable artifact",
                "sources": [
                    {
                        "ref": f"validation/execution/{task_id}/test-artifact.txt",
                        "sha256": artifact_sha
                    }
                ],
                "blocks_actions": [],
                "verification_plan": "Check artifact hash"
            }
        ]

        self.create_execution_packet(task_id, "CLOSED", [], claims)
        self.create_backlog([
            {
                "task_id": task_id,
                "status": "CLOSED",
                "owner_role": "test-role",
                "phase": "P1",
                "normative_specs": [],
                "required_decisions": [],
                "artifacts": [],
                "execution_packet_ref": f"validation/execution/{task_id}/execution-packet.yaml"
            }
        ])
        self.create_test_catalog()
        self.create_ai_execution_policy()

        data = {
            "implementation-backlog": yaml.safe_load(
                (self.plan / "machine" / "implementation-backlog.yaml").read_text()
            ),
            "decision-register": {"version": "1.0.0", "decisions": []}
        }
        self.create_decision_register(data["decision-register"])

        errors = execution_checks(data, self.plan)

        # FI-05 PASS: Ordinary artifact validated correctly
        exec_errors = [e for e in errors if "EXEC" in e and task_id in e]
        assert len(exec_errors) == 0, \
            f"FI-05 failed: expected PASS for ordinary artifact, got: {exec_errors}"

    def test_FI_06_v2_061_real_regression_pass(self):
        """FI-06: V2-061 real regression → no longer fails with evolved decision-register.

        This is the actual production case that triggered the governance fix.
        V2-061 is CLOSED. decision-register.yaml has legitimately evolved.
        Claim references decision-register via source_ref. Must resolve to frozen and PASS.
        """
        task_id = "V2-061"

        # V2-061 frozen decision-register (historical snapshot at task closure)
        v2_061_frozen = {
            "version": "1.2.0",
            "decisions": [
                {"id": "ADR-002", "status": "ACCEPTED", "title": "Character Schema"}
            ]
        }
        frozen_path, frozen_sha = self.create_frozen_snapshot(v2_061_frozen, task_id)

        # Current decision-register (evolved with new ADRs)
        current_register = {
            "version": "1.2.0",
            "decisions": [
                {"id": "ADR-001", "status": "ACCEPTED", "title": "Runtime"},
                {"id": "ADR-002", "status": "ACCEPTED", "title": "Character Schema"},
                {"id": "ADR-003", "status": "REQUIRED", "title": "Event Timeline"}
            ]
        }
        self.create_decision_register(current_register)

        # V2-061 execution packet structure (simplified)
        inputs = [
            {
                "source_ref": "machine/decision-register.yaml",
                "ref": f"validation/execution/{task_id}/inputs/{frozen_sha}.txt",
                "sha256": frozen_sha
            }
        ]
        claims = [
            {
                "id": "CLAIM-003-ADR",
                "kind": "FACT",
                "statement": "ADR-002 acceptance verified",
                "sources": [
                    {
                        "ref": "machine/decision-register.yaml",
                        "sha256": frozen_sha
                    }
                ],
                "blocks_actions": [],
                "verification_plan": "Verify ADR-002 is ACCEPTED in frozen snapshot"
            }
        ]

        # Create V2-061 directory structure
        (self.plan / "validation" / "execution" / task_id / "inputs").mkdir(parents=True, exist_ok=True)
        self.create_execution_packet(task_id, "CLOSED", inputs, claims, action="CERTIFY")

        self.create_backlog([
            {
                "task_id": task_id,
                "status": "CLOSED",
                "owner_role": "domain-maintainer",
                "phase": "P1",
                "normative_specs": ["machine/decision-register.yaml"],
                "required_decisions": ["ADR-002"],
                "artifacts": ["src/anovel/domain/character.py"],
                "execution_packet_ref": f"validation/execution/{task_id}/execution-packet.yaml"
            }
        ])
        self.create_test_catalog()
        self.create_ai_execution_policy()

        data = {
            "implementation-backlog": yaml.safe_load(
                (self.plan / "machine" / "implementation-backlog.yaml").read_text()
            ),
            "decision-register": current_register
        }

        errors = execution_checks(data, self.plan)

        # FI-06 PASS: V2-061 validation succeeds with evolved decision-register
        v2_061_errors = [e for e in errors if task_id in e]
        assert len(v2_061_errors) == 0, \
            f"FI-06 failed: V2-061 regression not fixed, got errors: {v2_061_errors}"

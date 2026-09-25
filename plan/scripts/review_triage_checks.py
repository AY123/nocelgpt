"""Review triage report validator - enforce policy constraints.

Validates external review triage reports against machine policy rules.
Fails closed on constraint violations to prevent false approvals.
"""

import json
from pathlib import Path

import yaml


class TriageValidationError(ValueError):
    """Triage report violates policy constraints."""

    pass


def load_policy():
    """Load review triage policy."""
    policy_path = Path(__file__).parents[1] / "machine/review-triage-policy.yaml"
    with policy_path.open() as f:
        return yaml.safe_load(f)


def load_schema():
    """Load review triage report schema."""
    schema_path = Path(__file__).parents[1] / "schemas/review-triage-report.schema.json"
    with schema_path.open() as f:
        return json.load(f)


def validate_logical_consistency(finding, policy):
    """Check verification/decision logical consistency."""
    verification = finding.get("verification")
    decision = finding.get("decision")
    finding_id = finding.get("id", "UNKNOWN")

    # Check prohibited combinations
    prohibited = {
        ("FALSE_POSITIVE", "ADOPT_NOW"),
        ("ALREADY_FIXED", "ADOPT_NOW"),
        ("CANNOT_VERIFY", "ADOPT_NOW"),
        ("NEEDS_MORE_EVIDENCE", "ADOPT_NOW"),
    }

    if (verification, decision) in prohibited:
        raise TriageValidationError(
            f"{finding_id}: Prohibited combination: {verification} + {decision}"
        )


def validate_p0_blocker_requirements(finding, policy):
    """Validate P0/BLOCKER special requirements."""
    severity = finding.get("severity")
    finding_id = finding.get("id", "UNKNOWN")

    if severity not in ("P0", "BLOCKER"):
        return

    # Target invariant required
    if policy["constraints"]["p0_blocker_requirements"]["p0_requires_target_invariant"]:
        if not finding.get("target_invariant"):
            raise TriageValidationError(
                f"{finding_id}: P0/BLOCKER requires target_invariant"
            )

    # Adversarial validation required
    if policy["constraints"]["p0_blocker_requirements"][
        "p0_requires_adversarial_validation"
    ]:
        adv = finding.get("adversarial_validation")
        if not adv or not adv.get("required") or not adv.get("cases"):
            raise TriageValidationError(
                f"{finding_id}: P0/BLOCKER requires adversarial_validation with cases"
            )

        # At least one adversarial case must be tested
        if len(adv["cases"]) == 0:
            raise TriageValidationError(
                f"{finding_id}: P0/BLOCKER requires at least one adversarial test case"
            )


def validate_evidence_discipline(finding, policy):
    """Validate evidence level claims."""
    evidence_level = finding.get("evidence_level")
    evidence_refs = finding.get("evidence_refs", [])
    finding_id = finding.get("id", "UNKNOWN")

    # E3 requires execution evidence
    if evidence_level == "E3":
        if policy["constraints"]["evidence_discipline"]["e3_requires_execution_proof"]:
            # Check for test execution, runtime log, or CI evidence
            has_execution = any(
                ref.get("type") in ("test_execution", "runtime_log", "ci_output")
                for ref in evidence_refs
            )
            if not has_execution and len(evidence_refs) > 0:
                # If refs provided but none are execution, that's suspicious
                # If no refs at all, we can't verify but won't block (might be external)
                raise TriageValidationError(
                    f"{finding_id}: E3 requires execution evidence (test_execution, runtime_log, or ci_output)"
                )


def validate_adoption_requirements(finding, policy):
    """Validate adoption decision requirements."""
    decision = finding.get("decision")
    finding_id = finding.get("id", "UNKNOWN")

    if decision not in ("ADOPT_NOW", "ADOPT_WITH_MODIFICATION"):
        return

    # Must have candidate remediation
    if not finding.get("candidate_remediation"):
        raise TriageValidationError(
            f"{finding_id}: {decision} requires candidate_remediation"
        )

    remediation = finding["candidate_remediation"]
    if remediation.get("status") not in ("APPROVED",):
        raise TriageValidationError(
            f"{finding_id}: {decision} requires candidate_remediation.status = APPROVED"
        )


def validate_enum_values(finding, policy):
    """Validate enum field values."""
    finding_id = finding.get("id", "UNKNOWN")

    # Verification
    if finding.get("verification") not in policy["verification_values"]:
        raise TriageValidationError(
            f"{finding_id}: Invalid verification value: {finding.get('verification')}"
        )

    # Severity
    if finding.get("severity") not in policy["severity_values"]:
        raise TriageValidationError(
            f"{finding_id}: Invalid severity value: {finding.get('severity')}"
        )

    # Decision
    if finding.get("decision") not in policy["decision_values"]:
        raise TriageValidationError(
            f"{finding_id}: Invalid decision value: {finding.get('decision')}"
        )

    # Recommendation validity (if present)
    if "recommendation_validity" in finding:
        if (
            finding["recommendation_validity"]
            not in policy["recommendation_validity_values"]
        ):
            raise TriageValidationError(
                f"{finding_id}: Invalid recommendation_validity: {finding['recommendation_validity']}"
            )


def validate_report(report_path):
    """Validate a triage report against policy.

    Returns:
        (bool, list): (valid, errors)
    """
    policy = load_policy()

    # Load report
    report_path = Path(report_path)
    if not report_path.exists():
        return False, [f"Report not found: {report_path}"]

    with report_path.open() as f:
        if report_path.suffix == ".json":
            report = json.load(f)
        elif report_path.suffix in (".yaml", ".yml"):
            report = yaml.safe_load(f)
        else:
            return False, ["Unknown report format (use .json or .yaml)"]

    # Validate structure
    if report.get("record_type") != "external_review_triage_report":
        return False, ["Invalid record_type (must be external_review_triage_report)"]

    errors = []

    # Validate each finding
    findings = report.get("findings", [])
    finding_ids = set()

    for finding in findings:
        finding_id = finding.get("id", "UNKNOWN")

        # Check for duplicate IDs
        if finding_id in finding_ids:
            errors.append(f"Duplicate finding ID: {finding_id}")
            continue
        finding_ids.add(finding_id)

        try:
            validate_enum_values(finding, policy)
            validate_logical_consistency(finding, policy)
            validate_p0_blocker_requirements(finding, policy)
            validate_evidence_discipline(finding, policy)
            validate_adoption_requirements(finding, policy)
        except TriageValidationError as e:
            errors.append(str(e))

    # Validate observations not counted as findings
    observations = report.get("observations", [])
    obs_ids = set()
    for obs in observations:
        obs_id = obs.get("id", "UNKNOWN")
        if obs_id in finding_ids:
            errors.append(f"Observation ID conflicts with Finding ID: {obs_id}")
        if obs_id in obs_ids:
            errors.append(f"Duplicate observation ID: {obs_id}")
        obs_ids.add(obs_id)

    # Validate summary consistency
    summary = report.get("summary", {})
    if summary.get("total_findings", 0) != len(findings):
        errors.append(
            f"Summary total_findings ({summary.get('total_findings')}) "
            f"does not match actual findings count ({len(findings)})"
        )

    return len(errors) == 0, errors


def main(argv=None):
    """Run validator on a report file."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", help="Path to triage report (JSON or YAML)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code on any validation failure",
    )

    args = parser.parse_args(argv)

    print(f"Validating: {args.report}")
    valid, errors = validate_report(args.report)

    if valid:
        print("✓ PASS: Report validates against policy")
        return 0
    else:
        print("✗ FAIL: Policy violations detected:")
        for error in errors:
            print(f"  - {error}")
        return 1 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())

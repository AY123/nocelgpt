"""Check mandatory Actions execution, without claiming platform permission protection."""

from __future__ import annotations

from typing import Any

CHECKOUT = "actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
UPLOAD = "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02"
LABELS = {
    "static": "STATIC",
    "schema_contract": "SCHEMA_CONTRACT",
    "unit": "UNIT",
    "arch_fitness": "ARCH_FITNESS",
    "secret_dependency": "SECRET_DEPENDENCY",
}
POSTGRES = "postgres:17.11-bookworm@sha256:639ab7ceb90e13123085b741fb31ef493fba25463002f6da665352e7b534b652"


def validate_github_configuration(document: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["GitHub workflow mapping required"]
    if (
        set(document) != {"name", "on", "permissions", "concurrency", "jobs"}
        or document.get("on") != {"workflow_dispatch": None}
        or document.get("permissions") != {"contents": "read"}
        or document.get("concurrency")
        != {"group": "v2-004-${{ github.ref }}", "cancel-in-progress": False}
    ):
        errors.append(
            "Exact manual dispatch and read-only workflow permissions required"
        )
    jobs = document.get("jobs")
    if not isinstance(jobs, dict) or set(jobs) != {"gates", "postgres_env"}:
        return errors + ["Exact six-gate matrix/PostgreSQL job set required"]
    for name, job in jobs.items():
        extra = {"strategy"} if name == "gates" else {"services"}
        if (
            not isinstance(job, dict)
            or set(job)
            != {
                "runs-on",
                "container",
                "timeout-minutes",
                "continue-on-error",
                "name",
                "env",
                "steps",
            }
            | extra
        ):
            errors.append("Unexpected job overrides: " + name)
            continue
        if (
            job["runs-on"] != "ubuntu-24.04"
            or job["container"] != "python:3.12.14-bookworm"
            or job["timeout-minutes"] != 20
            or job["continue-on-error"] is not False
        ):
            errors.append("Pinned runtime and hard job failures required: " + name)
        gate = "${{ matrix.gate }}" if name == "gates" else "postgres_env"
        if name == "gates":
            expected = {
                "fail-fast": False,
                "matrix": {
                    "include": [{"gate": k, "label": v} for k, v in LABELS.items()]
                },
            }
            if (
                job.get("strategy") != expected
                or job["name"] != "${{ matrix.label }}"
                or job["env"] != {"ANOVELOS_GATE_NAME": gate}
            ):
                errors.append("All five mandatory matrix gates must execute")
        else:
            if (
                job["name"] != "POSTGRES_ENV"
                or job["env"]
                != {
                    "ANOVELOS_GATE_NAME": gate,
                    "ANOVELOS_TEST_DSN": "postgresql+psycopg://anovel:anovel_test@postgres:5432/bootstrap_test",
                }
                or job["services"]
                != {
                    "postgres": {
                        "image": POSTGRES,
                        "env": {
                            "POSTGRES_USER": "anovel",
                            "POSTGRES_PASSWORD": "anovel_test",
                            "POSTGRES_DB": "bootstrap_test",
                        },
                        "options": '--health-cmd "pg_isready -U anovel -d bootstrap_test" --health-interval 5s --health-timeout 5s --health-retries 12',
                    }
                }
            ):
                errors.append("Real pinned PostgreSQL service required")
        expected_steps = [
            {
                "name": "Checkout exact revision and complete history",
                "uses": CHECKOUT,
                "with": {
                    "fetch-depth": 0,
                    "fetch-tags": True,
                    "persist-credentials": False,
                },
            },
            {
                "name": "Verify GitHub source context",
                "run": 'git config --global --add safe.directory "$GITHUB_WORKSPACE"\n'
                "python -I -B scripts/ci/github_context.py\n",
            },
            {
                "name": "Install locked runtime",
                "run": "python -m pip install --index-url https://pypi.org/simple uv==0.12.17\nuv sync --locked",
            },
            {
                "name": "Run mandatory gate",
                "run": "uv run --locked python -B scripts/ci/run_gate.py " + gate,
            },
            {
                "name": "Upload original receipts and reports",
                "if": "always()",
                "uses": UPLOAD,
                "with": {
                    "name": "gate-"
                    + gate
                    + "-${{ github.run_id }}-${{ github.run_attempt }}",
                    "path": "dist/ci/" + gate + "/",
                    "if-no-files-found": "error",
                    "retention-days": 14,
                },
            },
        ]
        if job["steps"] != expected_steps:
            errors.append(
                "Mandatory command or original artifact collection changed: " + name
            )
    return errors

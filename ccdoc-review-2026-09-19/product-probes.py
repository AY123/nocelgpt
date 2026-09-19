"""Read-only, offline probes of selected ccdoc product/evaluation examples.

Only the explicitly selected ABTestManager class from a Python fence is executed.
No LLM, network, real data, or repository implementation is executed.
"""
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import ast
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parents[1]
source_path = ROOT / "ccdoc/17_QUALITY_ASSURANCE_FRAMEWORK.md"
source = source_path.read_text()
block = next(b for b in re.findall(r"```python\n(.*?)```", source, re.S)
             if "class ABTestManager:" in b)
tree = ast.parse(block)
selected = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ABTestManager")
env = {"Dict": Dict, "List": List, "datetime": datetime}
exec(compile(ast.Module(body=[selected], type_ignores=[]), str(source_path), "exec"), env)
manager = env["ABTestManager"]()
manager.create_test("one_each", {}, [{}], [50, 50])
manager.variants["one_each"]["metrics"] = [
    {"variant": "control", "metrics": {"overall_score": 75}},
    {"variant": "variant_1", "metrics": {"overall_score": 81}},
]
ab_result = manager.analyze_results("one_each")
assert ab_result["recommendation"] == "deploy"

n, k, z = 3, 2, 1.96
p = k / n
denom = 1 + z * z / n
center = (p + z * z / (2 * n)) / denom
half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
results = {
    "scope": "planning-document examples only; not production implementation",
    "source": str(source_path),
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "ab_one_observation_per_arm": ab_result,
    "reader_pilot_two_of_three": {
        "observed_rate": p,
        "passes_document_threshold_gt_0_60": p > 0.60,
        "illustrative_wilson_95_interval": [center - half, center + half],
        "warning": "Interval assumes independent Bernoulli samples, not established by the document; real selection bias is additional.",
    },
    "draft_cost_arithmetic": {
        "weighted_cost_from_document_mix": 0.7 * 0.018 + 0.2 * 0.029 + 0.1 * 0.008,
        "claim_0_020_less_than_0_01": 0.020 < 0.01,
        "thirty_chapters_at_0_020": 30 * 0.020,
    },
    "quality_weight_counterexample": {
        "assumption": "Interpret the documented five dimension weights as a linear score, not an executed aggregator.",
        "all_other_dimensions_100_reader_appeal_0": 100 * (0.30 + 0.25 + 0.20 + 0.15),
        "document_grade_a_threshold": 90,
    },
    "workload_arithmetic": {
        "adr_part3_m1_listed_person_weeks": 4 + 1 + 1 + 1 + 1 + 1,
        "adr_part3_m1_calendar_weeks": 6,
        "adr_part3_m2_listed_person_weeks": 2 + 1 + 2 + 1 + 2 + 1 + 1 + 1 + 1,
        "adr_part3_m2_calendar_weeks": 8,
        "warning": "Parallel resources or overlapping work can reconcile totals, but are not stated in this table.",
    },
}
dest = Path(__file__).with_name("product-probe-results.json")
dest.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(results, ensure_ascii=False, indent=2))

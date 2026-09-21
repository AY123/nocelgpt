#!/usr/bin/env python3
"""Generate a traceable findings register, validate sources, and package this audit."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
REPORT = BASE / "CCDOC_ARCHITECTURE_AUDIT_REPORT.md"
source_snapshot = json.loads((BASE / "audit-results.json").read_text())
for item in source_snapshot["inventory"]:
    path = ROOT / "ccdoc" / item["path"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], "Source changed: " + str(path)

# Codex file links use absolute paths and :line, while labels keep document IDs.
report = REPORT.read_text()
report = re.sub(r'\]\(\.\./ccdoc/([^)#]+)#L(\d+)\)',
                lambda m: "](" + str(ROOT / "ccdoc" / m[1]) + ":" + m[2] + ")", report)
report = re.sub(r'\]\((\.\./architecture-review-2026-09-18/[^)]+)\)',
                lambda m: "](" + str((BASE / m[1]).resolve()) + ")", report)
for name in ["REMEDIATION_REGISTER.json", "audit-results.json", "product-review.md", "audit_ccdoc.py",
             "core-probes.py", "core-probe-results.json", "delivery-probes.py", "delivery-probe-results.json",
             "product-probes.py", "product-probe-results.json", "README.md"]:
    report = report.replace("](" + name + ")", "](" + str(BASE / name) + ")")
REPORT.write_text(report)

phase = {
 1:["P0"],2:["P2","P6"],3:["P6","P7"],4:["P2","P6"],5:["P2","P5"],
 6:["P1","P2"],7:["P1","P2"],8:["P3"],9:["P3","P7"],10:["P4","P5"],
 11:["P7"],12:["P7","P11"],13:["P8","P9","P11","P13"],14:["P4","P8","P9"],
 15:["P5","P6"],16:["P5","P8","P9"],17:["P0"],18:["P2"],19:["P0","P2","P12"],
 20:["P0","P11"],21:["P0"],22:["P0","P3","P5","P7"],23:["P10","P11"],24:["P4","P8","P9","P12","P14"]
}
findings = []
for match in re.finditer(r'(?ms)^### (CA-(\d{2}))｜(阻断|高|一般)：([^\n]+)\n(.*?)(?=^### CA-|^## 5\.|\Z)', report):
    fid, number, severity, title, body = match.groups()
    fix = re.search(r'\*\*修正：\*\*\s*(.*?)(?=\n\n\*\*关闭条件)', body, re.S)
    acceptance = re.search(r'\*\*关闭条件：\*\*\s*(.*)', body, re.S)
    assert fix and acceptance, fid
    refs = []
    for path, line in re.findall(r'\]\((/[^)]+?\.md):(\d+)\)', body):
        p = Path(path)
        assert p.exists(), path
        assert 1 <= int(line) <= len(p.read_text().splitlines()), path + ":" + line
        entry = {"file": str(p.relative_to(ROOT)), "line": int(line)}
        if entry not in refs: refs.append(entry)
    findings.append({"id": fid, "severity": {"阻断":"BLOCKER", "高":"HIGH", "一般":"MEDIUM"}[severity],
                     "title": title, "status": "OPEN", "affected_phases": phase[int(number)],
                     "evidence_scope": "planning_document_audit_not_deployed_system", "source_references":refs,
                     "analysis_markdown": body.split("**修正：**")[0].strip(),
                     "recommended_change_markdown":fix[1].strip(),
                     "acceptance_markdown":acceptance[1].strip(),
                     "owner":None, "closure_evidence":[]})
assert len(findings) == 24
counts = {s:sum(f["severity"]==s for f in findings) for s in ["BLOCKER","HIGH","MEDIUM"]}
assert counts == {"BLOCKER":8,"HIGH":15,"MEDIUM":1}, counts
(BASE/"REMEDIATION_REGISTER.json").write_text(json.dumps({
    "register_version":"1.0", "audit_date":"2026-09-19", "source":"ccdoc", "counts":counts,
    "authority":"User-frozen P0-P14 remains the execution roadmap; this register proposes corrections, not automatic scope expansion.",
    "severity_meaning":"Phase adoption/readiness, not production vulnerability severity. BLOCKER must close before the dependent capability is certified.",
    "status_meaning":"All findings OPEN; the audit does not mark implementation tasks fixed, verified, or closed.",
    "findings":findings}, ensure_ascii=False, indent=2)+"\n")

# Sanity-check every local file link in the principal report.
for target in re.findall(r'\]\((/[^)]+)\)', report):
    path = re.sub(r':\d+$', '', target)
    assert Path(path).is_file(), target

allowed = {".md", ".json", ".py"}
files = sorted(p for p in BASE.iterdir() if p.is_file() and p.suffix in allowed and p.name != "FILE_MANIFEST.json")
manifest = [{"file":p.name, "bytes":p.stat().st_size, "sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
(BASE/"FILE_MANIFEST.json").write_text(json.dumps({"audit_date":"2026-09-19", "excludes_self":True, "files":manifest}, ensure_ascii=False,indent=2)+"\n")
files.append(BASE/"FILE_MANIFEST.json")
archive = ROOT / "ANovelOS_CCDOC_Architecture_Audit_2026-09-19.zip"
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in sorted(files): z.write(p, str(Path(BASE.name)/p.name))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.namelist()) == len(files)
    for p in files: assert z.read(str(Path(BASE.name)/p.name)) == p.read_bytes()
print(json.dumps({"findings":len(findings), "severity_counts":counts, "source_files_unchanged":len(source_snapshot["inventory"]),
                  "archive":str(archive), "archive_entries":len(files), "bytes":archive.stat().st_size,
                  "sha256":hashlib.sha256(archive.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))

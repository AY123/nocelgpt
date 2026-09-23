"""Task-local context maintenance; preserves packets and reuses input snapshots."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,platform,subprocess,sys,yaml
R=Path(__file__).resolve().parents[5];P=R/'plan';B=P/'validation/execution/V2-003'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(yaml.safe_dump(x,allow_unicode=True,sort_keys=False,width=100000))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def refresh(stage):
    sys.path.insert(0,str(P/'scripts'));import validate_plan as v
    data=v.load()
    for name,value in v.expected_views(data).items():(P/name).write_text(value)
    dump(P/'FILE_MANIFEST.json',v.build_manifest())
    dest=B/'context'/stage;dest.mkdir(parents=True,exist_ok=False)
    # Existing active packet snapshots are indexed by content. No archive traversal.
    available={}
    for tid in ['V2-001','V2-002','V2-003']:
        packet=yaml.safe_load((P/f'validation/execution/{tid}/execution-packet.yaml').read_text())
        for item in packet['inputs']:
            path=P/item['ref']
            if path.is_file() and sha(path)==item['sha256'] and path!=P/item['source_ref']:
                available[item['sha256']]=item['ref']
    for tid in ['V2-001','V2-002','V2-003']:
        path=P/f'validation/execution/{tid}/execution-packet.yaml';packet=yaml.safe_load(path.read_text())
        (dest/(tid+'-packet-before.yaml.txt')).write_bytes(path.read_bytes())
        for item in packet['inputs']:
            source=P/item['source_ref'];digest=sha(source)
            if digest not in available:
                snap=B/'inputs'/(digest+'.txt');snap.parent.mkdir(exist_ok=True)
                if not snap.exists():snap.write_bytes(source.read_bytes())
                available[digest]=str(snap.relative_to(P))
            item.update(ref=available[digest],sha256=digest)
        packet['plan_manifest_sha256']=sha(P/'FILE_MANIFEST.json')
        packet['review_notes'].append('V2-003 '+stage+': shared inputs reconciled; old packet retained; identical immutable snapshots reused. Historical V2-001/002 evidence/status not recertified.')
        save(path,packet)
if __name__=='__main__':refresh(sys.argv[1])

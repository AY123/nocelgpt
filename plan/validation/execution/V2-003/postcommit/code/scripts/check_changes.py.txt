#!/usr/bin/env python3
"""Review actual task changes against a separately pinned local Git scope."""
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plan/scripts'))
from change_review import review_changes
from task_entry import safe_output

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task',required=True);p.add_argument('--scope-revision',required=True)
    p.add_argument('--scope-ref',required=True);p.add_argument('--review-revision');p.add_argument('--review-ref')
    p.add_argument('--output',required=True,type=Path);a=p.parse_args(argv)
    try:out=safe_output(ROOT,a.output)
    except (OSError,ValueError) as exc:
        print(json.dumps({'status':'FAIL','errors':[str(exc)]}));return 2
    result=review_changes(ROOT,task_id=a.task,scope_revision=a.scope_revision,scope_ref=a.scope_ref,review_revision=a.review_revision,review_ref=a.review_ref)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'changes':len(result['changes']),'findings':len(result['findings']),'errors':result['errors']},ensure_ascii=False))
    return 0 if result['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())

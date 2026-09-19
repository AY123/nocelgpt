"""Safe, standalone probes of selected documentation snippets; no app/provider/DB calls.

Run: python3 ccdoc-review-2026-09-19/delivery-probes.py
Source classes/functions are compiled verbatim with postponed annotations and
only the undefined collaborators supplied by local in-memory stubs.
"""
from __future__ import annotations
import ast
import asyncio
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'ccdoc'
OUT = Path(__file__).resolve().parent
RESULTS = []

def block(file, marker):
    text = (DOCS / file).read_text()
    for match in re.finditer(r'^```python\s*\n(.*?)^```', text, re.M | re.S):
        if marker in match.group(1):
            return match.group(1), text[:match.start(1)].count('\n') + 1
    raise ValueError(marker)

def load(file, marker, names, extra=None):
    source, start = block(file, marker)
    tree = ast.parse(source)
    nodes = [n for n in tree.body if getattr(n, 'name', None) in names]
    prefix = ast.parse('from __future__ import annotations\n').body
    tree = ast.Module(body=prefix + nodes, type_ignores=[])
    scope = {'__name__': 'documentation_probe', **(extra or {})}
    exec(compile(ast.fix_missing_locations(tree), file, 'exec'), scope)
    return scope, start

def save(name, source, result):
    RESULTS.append({'probe': name, 'source': source, 'result': result})

async def main():
    file = '15_SYSTEM_ARCHITECTURE_DESIGN.md'
    scope, line = load(file, 'class ProductionService', ['ProductionService'])
    service = scope['ProductionService']()
    saves = []
    async def context(*args): return {'chapter_outline': {}, 'genre_id': 'urban'}
    async def prompt(*args): return 'local dummy prompt'
    async def generate(**kwargs): return 'local dummy chapter'
    async def validate(**kwargs): return SimpleNamespace(has_blocking_violations=False)
    async def score(*args): return 0
    async def write(**kwargs): saves.append(kwargs); return kwargs
    service._get_chapter_context = context
    service._build_chapter_prompt = prompt
    service.llm = SimpleNamespace(generate=generate)
    service._validate_genre_constraints = validate
    service._check_quality = score
    service._save_chapter = write
    await service.generate_chapter('novel', 1, 'user')
    assert len(saves) == 1 and saves[0]['quality_score'] == 0
    save('production_saves_quality_zero', f'{file}:{line}', {'save_count':len(saves), 'quality_score':saves[0]['quality_score']})

    scope, line = load(file, 'class GenesisService', ['GenesisService'], {'get_genre_config':lambda _: {}})
    service = object.__new__(scope['GenesisService'])
    obj = SimpleNamespace(to_dict=lambda:{})
    async def make_obj(**kwargs): return obj
    async def make_chars(**kwargs): return [obj]
    async def invalid(**kwargs): return SimpleNamespace(is_valid=False)
    genesis_saves = []
    async def genesis_write(**kwargs): genesis_saves.append(kwargs); return 'novel'
    service._generate_outline = make_obj
    service._generate_characters = make_chars
    service._generate_worldview = make_obj
    service._validate_genesis = invalid
    service._save_to_database = genesis_write
    await service.create_genesis('user', 'urban', 'local input')
    assert len(genesis_saves) == 1
    save('invalid_genesis_is_saved', f'{file}:{line}', {'validation':False, 'save_count':1})

    file = '17_QUALITY_ASSURANCE_FRAMEWORK.md'
    scope, line = load(file, 'class HumanReviewTrigger', ['HumanReviewTrigger'])
    with patch('random.random', return_value=0.9):
        outcome = scope['HumanReviewTrigger']().should_trigger_human_review({})
    assert outcome == (False, [])
    save('empty_quality_metrics_no_review', f'{file}:{line}', {'random_draw':0.9, 'review_required':outcome[0], 'reasons':outcome[1]})

    prompts = []
    async def fake_llm(*args, **kwargs):
        prompts.append(args[0]); return '{"score":100,"compliant":true,"issues":[]}'
    scope, line = load(file, 'async def check_genre_with_llm', ['check_genre_with_llm'], {'llm':SimpleNamespace(generate=fake_llm), 'json':json})
    tail = 'TAIL_ONLY_EVIDENCE_主角开始修炼'
    await scope['check_genre_with_llm']('urban', '正' * 1500 + tail, SimpleNamespace(genre_name='都市', to_prompt_context=lambda:'现实商战'))
    assert tail not in prompts[0]
    save('genre_validator_never_sees_tail', f'{file}:{line}', {'input_characters':1500+len(tail), 'tail_present_in_provider_prompt':False, 'note':'Proves prompt omission only; does not claim a real provider judgment.'})

    scope, line = load(file, 'class ABTestManager', ['ABTestManager'], {'datetime':SimpleNamespace(now=lambda:'test-time')})
    manager = scope['ABTestManager']()
    manager.create_test('test', {}, [{}], [50,50])
    await manager.collect_metrics('test', 'control', {'overall_score':50})
    await manager.collect_metrics('test', 'variant_1', {'overall_score':100})
    result = manager.analyze_results('test')
    assert result['recommendation'] == 'deploy'
    save('ab_deploy_with_one_sample_each', f'{file}:{line}', result)

    for file, marker in [('17_QUALITY_ASSURANCE_FRAMEWORK.md', 'class TextQualityChecker'), ('16_LLM_INTEGRATION_STRATEGY.md', 'async def batch_generate_characters')]:
        source, line = block(file, marker)
        try: ast.parse(source)
        except SyntaxError as error:
            save('snippet_syntax_error_' + marker.split()[-1], f'{file}:{line}', {'error':error.msg, 'document_line':line+error.lineno-1})
        else: raise AssertionError('Expected original snippet to fail compilation')

    file = '16_LLM_INTEGRATION_STRATEGY.md'
    scope, line = load(file, 'class LLMCache', ['LLMCache'], {'hashlib':hashlib})
    cache = scope['LLMCache'](None)
    collision = cache._make_key('ab','c') == cache._make_key('a','bc')
    assert collision
    save('cache_input_tuple_collision', f'{file}:{line}', {'first':['ab','c'], 'second':['a','bc'], 'same_cache_key':True, 'note':'Ambiguous concatenation, not a SHA-256 cryptographic collision.'})

    async def no_validation(*args, **kwargs): return 'invalid result'
    scope, line = load(file, 'async def generate_with_validation', ['generate_with_validation','_add_feedback_to_prompt'], {'llm':SimpleNamespace(generate=no_validation), 'logger':SimpleNamespace(warning=lambda _:None)})
    try: await scope['generate_with_validation']('prompt', lambda _: (False,['bad output']))
    except NameError as error:
        save('retry_validation_self_undefined', f'{file}:{line}', {'error':str(error)})
    else: raise AssertionError('Expected undefined self in free function')

    content = '陈阳走进会议室。' * 100
    assert len(content) == 800
    save('good_quality_test_fixture_length', '21_TESTING_STRATEGY.md:377', {'actual_characters':len(content), 'asserted_minimum':1800, 'assertion_passes':len(content)>=1800})

    # Equivalent pipeline semantics; deliberately no pg_dump, credentials or DB.
    with tempfile.TemporaryDirectory(prefix='anovel-doc-backup-probe-') as folder:
        path = Path(folder) / 'empty.sql.gz'
        script = 'set -e\n(exit 2) | gzip > "$1"\nif [ -f "$1" ]; then echo BACKUP_SUCCESS; else exit 1; fi\n'
        completed = subprocess.run(['/bin/bash','-c',script,'probe',str(path)],capture_output=True,text=True)
        assert completed.returncode == 0 and gzip.decompress(path.read_bytes()) == b''
        save('backup_pipeline_failure_reported_success', '20_DEPLOYMENT_OPERATIONS_GUIDE.md:931', {'producer_exit':2,'script_exit':completed.returncode,'stdout':completed.stdout.strip(),'decompressed_bytes':0})

    save('cost_math_using_document_rates_only', '16_LLM_INTEGRATION_STRATEGY.md:32', {
        'opus_outline_expected':8000*15/1e6+8000*75/1e6,
        'sonnet_character_expected':4000*3/1e6+2000*15/1e6,
        'sonnet_chapter_expected':8000*3/1e6+4000*15/1e6,
        'sonnet_revision_expected':6000*3/1e6+2000*15/1e6,
        'haiku_check_expected':2000*.25/1e6+500*1.25/1e6,
        '1000_chapters_expected':.72+6*.042+1000*.084+200*.048+2000*.001125,
        'note':'Document arithmetic only, not a verified current provider price quote.'})

    (OUT/'delivery-probe-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'completed_probes':len(RESULTS),'results_file':str(OUT/'delivery-probe-results.json'),'probes':[item['probe'] for item in RESULTS]},ensure_ascii=False,indent=2))

if __name__ == '__main__': asyncio.run(main())

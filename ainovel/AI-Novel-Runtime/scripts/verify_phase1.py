#!/usr/bin/env python3
"""Phase 1 验证运行 - 质量分析报告生成脚本"""
import json
import os

DRAFTS_DIR = 'novel-lingse/registry/derived/drafts'


def load_chapters():
    stats = []
    for fname in sorted(os.listdir(DRAFTS_DIR)):
        if not fname.endswith('.json'):
            continue
        with open(os.path.join(DRAFTS_DIR, fname)) as f:
            data = json.load(f)

        draft = data.get('draft', {})
        pr = data.get('publish_readiness', {})
        pr_route = data.get('prompt_provenance', {}).get('route_summary', {})

        task_id = draft.get('task_id', fname)
        word_count = draft.get('word_count', 0)
        recommendation = pr.get('recommendation', 'N/A')
        redline_passed = pr.get('basis', {}).get('redline', {}).get('passed', 'N/A')
        risk_hold = pr.get('policy', {}).get('drop_risk_hold_at', 'N/A')

        route_meta = pr_route.get('metadata', {}) if pr_route else {}
        failure_map = route_meta.get('failure_pack_map', {})
        template_detected = bool(failure_map) and failure_map.get('ai-tell') != 'gpt-v13'

        llm_info = draft.get('produced_by', {}).get('llm', {})
        finish_reason = llm_info.get('finish_reason', 'N/A')
        total_tokens = llm_info.get('token_usage', {}).get('total_tokens', 0)
        latency = llm_info.get('latency_ms', 0)

        ch_num = task_id.replace('TASK-', '')

        stats.append({
            'task_id': task_id,
            'ch_num': ch_num,
            'word_count': word_count,
            'recommendation': recommendation,
            'redline_passed': redline_passed,
            'finish_reason': finish_reason,
            'total_tokens': total_tokens,
            'latency': latency,
            'template_detected': template_detected,
            'failure_map': failure_map,
        })
    return stats


def main():
    stats = load_chapters()

    print('=' * 120)
    print('Phase 1 验证运行 - 质量分析报告')
    print(f'总章节: {len(stats)}/30')
    print('=' * 120)
    print()
    print(f'{"Task":<12} {"字数":<8} {"M7":<12} {"红线":<6} {"Finish":<9} '
          f'{"Tokens":<8} {"延迟ms":<8} {"模板检测":<10} {"失败包"}')
    print('-' * 120)
    for s in stats:
        wc = s['word_count']
        wc_str = f'{wc}'
        if wc > 4000:
            wc_str += '⚠️'
        td = '✅' if s['template_detected'] else '—'
        fm = ','.join(s['failure_map'].keys()) if s['failure_map'] else '—'
        print(f'{s["task_id"]:<12} {wc_str:<8} {s["recommendation"]:<12} '
              f'{str(s["redline_passed"]):<6} {s["finish_reason"]:<9} '
              f'{s["total_tokens"]:<8} {s["latency"]:<8} {td:<10} {fm}')

    print()
    print('=' * 120)
    print('摘要统计')
    print('=' * 120)
    m7_recommend = sum(1 for s in stats if s['recommendation'] == 'recommend')
    m7_review = sum(1 for s in stats if s['recommendation'] == 'review')
    m7_block = sum(1 for s in stats if s['recommendation'] == 'block')
    overlong = sum(1 for s in stats if s['word_count'] > 4000)
    overlong_3000 = sum(1 for s in stats if s['word_count'] > 3000)
    template_triggers = sum(1 for s in stats if s['template_detected'])
    redline_fail = sum(1 for s in stats if s['redline_passed'] is False)
    total_words = sum(s['word_count'] for s in stats)
    avg_words = total_words // len(stats) if stats else 0
    total_latency = sum(s['latency'] for s in stats)
    total_tokens = sum(s['total_tokens'] for s in stats)

    print(f'  推荐(L0): {m7_recommend}/{len(stats)}')
    print(f'  需审查:    {m7_review}/{len(stats)}')
    print(f'  阻止:      {m7_block}/{len(stats)}')
    print(f'  红线失败:  {redline_fail}/{len(stats)}')
    print(f'  超长(>4k): {overlong}/{len(stats)}')
    print(f'  超长(>3k): {overlong_3000}/{len(stats)}')
    print(f'  模板检测:  {template_triggers}/{len(stats)}')
    print(f'  总字数:    {total_words}')
    print(f'  平均字数:  {avg_words}')
    print(f'  总Token:   {total_tokens}')
    print(f'  总耗时:    {total_latency / 1000:.1f}s')

    print()
    print('=' * 120)
    print('基线对比')
    print('=' * 120)
    print(f'  指标                Phase 1     Baseline    改善')
    overlong_flag = '✅' if overlong < 5 else '⚠️'
    print(f'  {"超长章节(>4k):":<20} {overlong:<10} 18           {overlong_flag} ({overlong} vs 18)')
    print(f'  {"AI味(>40%):":<20} 待分析    40%→70%     待分析')
    print(f'  {"跨章断裂:":<20} 待分析    3处         待分析')
    m7_flag = '✅' if m7_recommend == len(stats) else '⚠️'
    print(f'  {"M7推荐率:":<20} {m7_recommend}/{len(stats)}          -            {m7_flag}')
    redline_flag = '✅' if redline_fail == 0 else '⚠️'
    print(f'  {"红线通过率:":<20} {len(stats) - redline_fail}/{len(stats)}          -            {redline_flag}')
    tmpl_flag = '✅' if template_triggers > 0 else '⚠️'
    print(f'  {"模板检测触发:":<20} {template_triggers}次          -            {tmpl_flag}')
    print(f'  {"平均字数:":<20} {avg_words}字        -            -')


if __name__ == '__main__':
    main()

"""batch_analyze_100_chapters.py — Batch Analysis of 100 Chapters

Analyze all 100 chapters with P0 modules using real LLM.
This provides comprehensive quality assessment and optimization suggestions.

Started: 2026-08-11 05:10

Usage:
    cd AI-Novel-Runtime
    python3 tests/batch_analyze_100_chapters.py

Outputs:
    - batch_analysis_results.json - Complete analysis data
    - batch_analysis_report.md - Human-readable report

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_env():
    """Load .env configuration."""
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
        return True
    return False


def load_chapter(chapter_num: int) -> dict:
    """Load chapter from registry."""
    draft_path = Path(__file__).parent.parent.parent / 'novel-lingse' / 'registry' / 'derived' / 'drafts' / f'TASK-{chapter_num:05d}.json'

    if not draft_path.exists():
        return None

    try:
        data = json.loads(draft_path.read_text())
        body = data.get('draft', {}).get('body', '')
        return {
            'chapter_num': chapter_num,
            'body': body,
            'length': len(body)
        }
    except Exception as e:
        print(f"  ⚠️  Ch{chapter_num}: 加载失败 - {e}")
        return None


def batch_analyze_chapters(start: int = 1, end: int = 100, sample_rate: int = 1):
    """Batch analyze chapters with P0 modules.

    Args:
        start: Start chapter number
        end: End chapter number
        sample_rate: Analyze every N chapters (1 = all, 10 = every 10th)
    """
    print("\n" + "="*60)
    print("100章批量分析")
    print("="*60)

    # Load env
    if not load_env():
        print("❌ Failed to load .env")
        return False

    # Create model
    from runtime.commercial.llm_integration import create_llm_model
    from runtime.retention.hook_enhancer_impl import HookEnhancer
    from runtime.commercial.paywall_optimizer_impl import PaywallOptimizer

    print("\n创建LLM模型...")
    model = create_llm_model("deepseek")
    print("✅ 模型创建成功")

    # Create analyzers
    print("\n初始化分析器...")
    hook_enhancer = HookEnhancer(model=model)
    paywall_optimizer = PaywallOptimizer(model=model)
    print("✅ 分析器初始化完成")

    # Determine chapters to analyze
    chapters_to_analyze = list(range(start, end + 1, sample_rate))

    print(f"\n分析范围: Ch{start}-Ch{end}")
    print(f"采样率: 每{sample_rate}章")
    print(f"分析数量: {len(chapters_to_analyze)}章")
    print(f"预计时间: ~{len(chapters_to_analyze) * 15}秒 ({len(chapters_to_analyze) * 15 / 60:.1f}分钟)")

    # Confirm (skip in non-interactive mode)
    if len(chapters_to_analyze) > 20:
        import sys
        if sys.stdin.isatty():
            response = input(f"\n将分析{len(chapters_to_analyze)}章，确认继续？(y/n): ")
            if response.lower() != 'y':
                print("❌ 用户取消")
                return False
        else:
            print(f"\n⏩ 非交互模式，自动继续分析{len(chapters_to_analyze)}章")

    # Analyze
    results = []
    errors = []

    print(f"\n开始分析...")
    print("="*60)

    for i, chapter_num in enumerate(chapters_to_analyze, 1):
        print(f"\n[{i}/{len(chapters_to_analyze)}] 分析 Ch{chapter_num}...")

        # Load chapter
        chapter = load_chapter(chapter_num)
        if not chapter or not chapter['body']:
            print(f"  ❌ 跳过: 章节为空或加载失败")
            errors.append({
                'chapter': chapter_num,
                'error': 'Empty or failed to load'
            })
            continue

        try:
            # Analyze with HookEnhancer
            print(f"  ⏳ 分析钩子强度...")
            hook_analysis = hook_enhancer.analyze_chapter_ending(chapter['body'])

            # Analyze with PaywallOptimizer
            print(f"  ⏳ 量化付费转化...")
            paywall_score = paywall_optimizer.measure_hook_strength(chapter['body'])

            # Get improvements
            improvements = hook_enhancer.suggest_improvements(hook_analysis)

            # Store results
            result = {
                'chapter': chapter_num,
                'length': chapter['length'],
                'hook_analysis': {
                    'type': hook_analysis.hook_type.value,
                    'strength': hook_analysis.strength_score,
                    'curiosity': hook_analysis.curiosity_score,
                    'tension': hook_analysis.tension_score,
                    'emotion': hook_analysis.emotional_score,
                    'continue_rate': hook_analysis.predicted_continue_rate,
                    'drop_risk': hook_analysis.predicted_drop_risk,
                    'what_works': hook_analysis.what_works,
                    'what_fails': hook_analysis.what_fails
                },
                'paywall_score': {
                    'overall': paywall_score.overall_score,
                    'cliffhanger': paywall_score.cliffhanger_intensity,
                    'curiosity': paywall_score.curiosity_trigger,
                    'emotion': paywall_score.emotional_investment,
                    'conflict': paywall_score.conflict_escalation,
                    'conversion': paywall_score.predicted_paywall_conversion
                },
                'improvements': [
                    {
                        'type': imp.suggestion_type,
                        'target': imp.target_element,
                        'reason': imp.reason,
                        'gain': imp.expected_gain
                    }
                    for imp in improvements
                ]
            }

            results.append(result)

            # Print summary
            print(f"  ✅ 钩子: {hook_analysis.strength_score:.0f}/100, "
                  f"转化: {paywall_score.predicted_paywall_conversion:.0%}, "
                  f"建议: {len(improvements)}条")

        except Exception as e:
            print(f"  ❌ 分析失败: {e}")
            errors.append({
                'chapter': chapter_num,
                'error': str(e)
            })

    # Save results
    print(f"\n" + "="*60)
    print("保存结果...")

    output_dir = Path(__file__).parent.parent.parent / 'analysis-results'
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save JSON
    json_path = output_dir / f'batch_analysis_{timestamp}.json'
    json_path.write_text(json.dumps({
        'metadata': {
            'analyzed_at': timestamp,
            'start_chapter': start,
            'end_chapter': end,
            'sample_rate': sample_rate,
            'total_analyzed': len(results),
            'errors': len(errors)
        },
        'results': results,
        'errors': errors
    }, indent=2, ensure_ascii=False))

    print(f"✅ JSON保存: {json_path}")

    # Generate report
    report_path = output_dir / f'batch_analysis_{timestamp}.md'
    generate_report(results, errors, report_path, start, end, sample_rate)
    print(f"✅ 报告保存: {report_path}")

    # Print summary
    print(f"\n" + "="*60)
    print("分析完成")
    print("="*60)
    print(f"\n成功: {len(results)}章")
    print(f"失败: {len(errors)}章")

    if results:
        avg_hook = sum(r['hook_analysis']['strength'] for r in results) / len(results)
        avg_conversion = sum(r['paywall_score']['conversion'] for r in results) / len(results)
        total_improvements = sum(len(r['improvements']) for r in results)

        print(f"\n平均钩子强度: {avg_hook:.1f}/100")
        print(f"平均付费转化: {avg_conversion:.1%}")
        print(f"改进建议总数: {total_improvements}条")

    return True


def generate_report(results, errors, output_path, start, end, sample_rate):
    """Generate markdown report."""
    report = f"""# 100章批量分析报告

## 分析信息

- **分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **章节范围**: Ch{start}-Ch{end}
- **采样率**: 每{sample_rate}章
- **成功分析**: {len(results)}章
- **分析失败**: {len(errors)}章

---

## 总体统计

"""

    if results:
        avg_hook = sum(r['hook_analysis']['strength'] for r in results) / len(results)
        avg_conversion = sum(r['paywall_score']['conversion'] for r in results) / len(results)
        avg_continue = sum(r['hook_analysis']['continue_rate'] for r in results) / len(results)
        avg_drop = sum(r['hook_analysis']['drop_risk'] for r in results) / len(results)

        report += f"""### 平均指标

- **钩子强度**: {avg_hook:.1f}/100
- **付费转化**: {avg_conversion:.1%}
- **继续阅读率**: {avg_continue:.1%}
- **弃书风险**: {avg_drop:.1%}

### 强度分布

"""
        # Distribution
        ranges = [(0, 60, "低"), (60, 75, "中"), (75, 85, "良"), (85, 100, "优")]
        for low, high, label in ranges:
            count = sum(1 for r in results if low <= r['hook_analysis']['strength'] < high)
            pct = count / len(results) * 100
            report += f"- **{label} ({low}-{high})**: {count}章 ({pct:.1f}%)\n"

        report += f"\n---\n\n## 详细结果\n\n"

        for r in results:
            report += f"""### Ch{r['chapter']}

- **钩子强度**: {r['hook_analysis']['strength']:.0f}/100
- **钩子类型**: {r['hook_analysis']['type']}
- **继续率**: {r['hook_analysis']['continue_rate']:.0%}
- **付费转化**: {r['paywall_score']['conversion']:.0%}
- **改进建议**: {len(r['improvements'])}条

"""

    if errors:
        report += f"\n---\n\n## 错误列表\n\n"
        for err in errors:
            report += f"- Ch{err['chapter']}: {err['error']}\n"

    output_path.write_text(report)


if __name__ == "__main__":
    # Parse args
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--end', type=int, default=100)
    parser.add_argument('--sample', type=int, default=10, help='Analyze every N chapters')
    args = parser.parse_args()

    success = batch_analyze_chapters(args.start, args.end, args.sample)
    sys.exit(0 if success else 1)

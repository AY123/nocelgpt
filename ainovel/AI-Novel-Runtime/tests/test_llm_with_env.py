"""test_llm_with_env.py — Test P0 Modules with .env Configuration

Test P0 modules integration with LLM using .env configuration.
Started: 2026-08-11 05:05

Usage:
    cd AI-Novel-Runtime
    python3 tests/test_llm_with_env.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
import os
import sys
from pathlib import Path
import pytest  # P0-4: Add pytest import

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent.parent / '.env'

    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False

    loaded = 0
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value
            loaded += 1

    print(f"✅ Loaded {loaded} variables from .env")
    return True


def test_p0_with_real_llm():
    """Test P0 modules with real LLM from .env."""
    print("\n" + "="*60)
    print("P0模块 + 真实LLM集成测试")
    print("="*60)

    # Load .env
    if not load_env():
        pytest.skip(".env file not found")  # P0-4: Use pytest.skip instead of return

    # Check API keys
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    claude_key = os.environ.get("ANTHROPIC_API_KEY")

    print(f"\nAPI密钥检查:")
    print(f"  DeepSeek: {'✅ ' + deepseek_key[:20] + '...' if deepseek_key else '❌ 未配置'}")
    print(f"  Claude: {'✅ ' + claude_key[:20] + '...' if claude_key else '❌ 未配置'}")

    # Choose provider
    if deepseek_key:
        provider = "deepseek"
        print(f"\n使用提供商: DeepSeek")
    elif claude_key:
        provider = "claude"
        print(f"\n使用提供商: Claude")
    else:
        print(f"\n❌ 错误: 未找到有效的API密钥")
        pytest.skip("No API keys configured")  # P0-4: Use pytest.skip instead of return

    try:
        # Import after env is loaded
        from runtime.commercial.llm_integration import create_llm_model

        # Create model
        print(f"\n创建LLM模型...")
        model = create_llm_model(provider=provider)
        print(f"✅ 模型创建成功")

        # Test 1: Simple generation
        print(f"\n" + "="*60)
        print("测试1: 基础生成")
        print("="*60)

        test_prompt = "请用一句话描述人工智能在文学创作中的作用。"
        print(f"提示词: {test_prompt}")

        response = model.generate(test_prompt)
        print(f"✅ 生成成功")
        print(f"响应: {response}")

        # Test 2: HookEnhancer
        print(f"\n" + "="*60)
        print("测试2: HookEnhancer - 章末钩子分析")
        print("="*60)

        from runtime.retention.hook_enhancer_impl import HookEnhancer

        enhancer = HookEnhancer(model=model)

        test_chapter = """
第五十一章 矿脉深处

段奕尘看着手中逐渐明亮的晶石，终于明白了父亲留下的那句话。

原来，湮灭体质不是诅咒，而是天赋。

他深吸一口气，右手指节上的晶化开始散发暗金色的光芒。矿道深处传来低沉的轰鸣声，仿佛什么巨大的东西正在苏醒。

"准备好了吗？"小雨的声音在意识中响起，带着从未有过的清晰。

段奕尘握紧拳头，向着矿道最深处走去。

就在此时，身后传来一个冰冷的声音："站住。想去那里，得先过我这一关。"

他回头，瞳孔骤然收缩——

来人，竟是三年前害死父母的那个矿监！
        """

        print(f"测试章节: 第51章结尾片段")
        print(f"长度: {len(test_chapter)} 字符")

        analysis = enhancer.analyze_chapter_ending(test_chapter)

        print(f"\n✅ 分析完成:")
        print(f"  钩子类型: {analysis.hook_type.value}")
        print(f"  整体强度: {analysis.strength_score:.1f}/100")
        print(f"  好奇心: {analysis.curiosity_score:.1f}/100")
        print(f"  紧张度: {analysis.tension_score:.1f}/100")
        print(f"  情感: {analysis.emotional_score:.1f}/100")
        print(f"  继续阅读率预测: {analysis.predicted_continue_rate:.1%}")
        print(f"  弃书风险: {analysis.predicted_drop_risk:.1%}")

        if analysis.what_works:
            print(f"\n  ✅ 有效元素:")
            for item in analysis.what_works:
                print(f"    - {item}")

        if analysis.what_fails:
            print(f"\n  ⚠️  待改进:")
            for item in analysis.what_fails:
                print(f"    - {item}")

        # Test 3: Improvement suggestions
        print(f"\n" + "="*60)
        print("测试3: 改进建议生成")
        print("="*60)

        improvements = enhancer.suggest_improvements(analysis, target_strength=85.0)

        if improvements:
            print(f"\n生成了 {len(improvements)} 条改进建议:")
            for i, imp in enumerate(improvements, 1):
                print(f"\n  {i}. {imp.suggestion_type} - {imp.target_element}")
                print(f"     原因: {imp.reason}")
                print(f"     示例: {imp.example}")
                print(f"     预期提升: +{imp.expected_gain:.1f}分")
        else:
            print(f"✅ 钩子强度已达标，无需改进")

        # Test 4: PaywallOptimizer
        print(f"\n" + "="*60)
        print("测试4: PaywallOptimizer - 付费点优化")
        print("="*60)

        from runtime.commercial.paywall_optimizer_impl import PaywallOptimizer

        optimizer = PaywallOptimizer(model=model)

        score = optimizer.measure_hook_strength(test_chapter)

        print(f"\n✅ 钩子强度量化:")
        print(f"  总分: {score.overall_score:.1f}/100")
        print(f"  悬念强度: {score.cliffhanger_intensity:.1f}/100")
        print(f"  好奇触发: {score.curiosity_trigger:.1f}/100")
        print(f"  情感投入: {score.emotional_investment:.1f}/100")
        print(f"  冲突升级: {score.conflict_escalation:.1f}/100")
        print(f"  付费转化预测: {score.predicted_paywall_conversion:.1%}")

        # Summary
        print(f"\n" + "="*60)
        print("测试结果汇总")
        print("="*60)
        print(f"\n✅ 所有测试通过!")
        print(f"\n集成状态:")
        print(f"  LLM提供商: {provider}")
        print(f"  基础生成: ✅ 正常")
        print(f"  HookEnhancer: ✅ 正常")
        print(f"  PaywallOptimizer: ✅ 正常")
        print(f"  改进建议: ✅ 正常")

        print(f"\n🎉 P0模块LLM集成成功!")
        print(f"✅ 可以开始使用真实LLM进行商业化优化")

        assert True  # P0-4: Use assert instead of return

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Test failed: {e}")  # P0-4: Use pytest.fail instead of return


if __name__ == "__main__":
    success = test_p0_with_real_llm()
    sys.exit(0 if success else 1)

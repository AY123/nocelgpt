"""llm_integration.py — P0 Modules LLM Integration

Integrate P0 commercial modules with real LLM (DeepSeek/Claude).
Started: 2026-08-11 05:00

This script provides easy integration of P0 modules with production LLM.

Usage:
    from runtime.commercial.llm_integration import create_llm_model

    # Create LLM instance
    model = create_llm_model(provider="deepseek")

    # Use with P0 modules
    from runtime.retention.hook_enhancer_impl import HookEnhancer
    enhancer = HookEnhancer(model=model)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
"""
import os
from typing import Optional, Dict, Any


class LLMRequest:
    """LLM request wrapper."""
    def __init__(self, prompt: str, **kwargs):
        self.prompt = prompt
        self.kwargs = kwargs


class LLMResponse:
    """LLM response wrapper."""
    def __init__(self, text: str, **kwargs):
        self.text = text
        self.kwargs = kwargs


class SimpleLLM:
    """Simple LLM wrapper for P0 modules.

    Provides a minimal interface compatible with our P0 modules.
    """

    def __init__(self, provider: str = "deepseek", model_id: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize LLM.

        Args:
            provider: "deepseek" or "claude"
            model_id: Optional model ID override
            api_key: Optional API key (defaults to env var)
        """
        self.provider = provider
        self.model_id = model_id or self._default_model(provider)
        self.api_key = api_key or self._get_api_key(provider)

        # Initialize client
        self.client = self._create_client()

    def _default_model(self, provider: str) -> str:
        """Get default model for provider."""
        defaults = {
            "deepseek": "deepseek-chat",
            "claude": "claude-opus-4-8"
        }
        return defaults.get(provider, "deepseek-chat")

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key from environment."""
        env_vars = {
            "deepseek": "DEEPSEEK_API_KEY",
            "claude": "ANTHROPIC_API_KEY"
        }
        env_var = env_vars.get(provider)
        return os.environ.get(env_var) if env_var else None

    def _create_client(self):
        """Create API client."""
        if self.provider == "deepseek":
            try:
                from openai import OpenAI
                return OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.deepseek.com"
                )
            except ImportError:
                print("⚠️  openai package not installed. Run: pip install openai")
                return None

        elif self.provider == "claude":
            try:
                import anthropic
                return anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                print("⚠️  anthropic package not installed. Run: pip install anthropic")
                return None

        return None

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        if not self.client:
            raise RuntimeError(f"LLM client not initialized for {self.provider}")

        if not self.api_key:
            raise RuntimeError(f"API key not found for {self.provider}")

        try:
            if self.provider == "deepseek":
                return self._generate_deepseek(prompt, **kwargs)
            elif self.provider == "claude":
                return self._generate_claude(prompt, **kwargs)
        except Exception as e:
            print(f"⚠️  LLM generation error: {e}")
            raise

    def _generate_deepseek(self, prompt: str, **kwargs) -> str:
        """Generate with DeepSeek."""
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2000)
        )
        return response.choices[0].message.content

    def _generate_claude(self, prompt: str, **kwargs) -> str:
        """Generate with Claude."""
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=kwargs.get("max_tokens", 2000),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


def create_llm_model(
    provider: str = "deepseek",
    model_id: Optional[str] = None,
    api_key: Optional[str] = None
) -> SimpleLLM:
    """Create LLM model for P0 modules.

    Args:
        provider: "deepseek" or "claude"
        model_id: Optional model ID
        api_key: Optional API key

    Returns:
        SimpleLLM instance

    Example:
        >>> model = create_llm_model("deepseek")
        >>> from runtime.retention.hook_enhancer_impl import HookEnhancer
        >>> enhancer = HookEnhancer(model=model)
    """
    return SimpleLLM(provider=provider, model_id=model_id, api_key=api_key)


def test_llm_integration():
    """Test LLM integration with P0 modules."""
    print("\n" + "="*60)
    print("P0模块LLM集成测试")
    print("="*60)

    # Check API keys
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    claude_key = os.environ.get("ANTHROPIC_API_KEY")

    print(f"\n环境检查:")
    print(f"  DeepSeek API Key: {'✅ 已配置' if deepseek_key else '❌ 未配置'}")
    print(f"  Claude API Key: {'✅ 已配置' if claude_key else '❌ 未配置'}")

    # Choose available provider
    if deepseek_key:
        provider = "deepseek"
        print(f"\n使用: DeepSeek")
    elif claude_key:
        provider = "claude"
        print(f"\n使用: Claude")
    else:
        print(f"\n❌ 错误: 未找到API密钥")
        print(f"\n请配置环境变量:")
        print(f"  export DEEPSEEK_API_KEY='your-key'")
        print(f"  或")
        print(f"  export ANTHROPIC_API_KEY='your-key'")
        return False

    try:
        # Create model
        print(f"\n创建LLM模型...")
        model = create_llm_model(provider=provider)
        print(f"✅ 模型创建成功")

        # Test simple generation
        print(f"\n测试生成...")
        test_prompt = "请用一句话描述人工智能。"
        response = model.generate(test_prompt)
        print(f"✅ 生成成功:")
        print(f"  提示: {test_prompt}")
        print(f"  响应: {response[:100]}...")

        # Test with HookEnhancer
        print(f"\n测试HookEnhancer集成...")
        from runtime.retention.hook_enhancer_impl import HookEnhancer

        enhancer = HookEnhancer(model=model)
        test_chapter = """
第五十一章结尾

段奕尘看着手中的晶石，终于明白了一切。
原来，这才是真正的秘密。
他深吸一口气，向着矿道深处走去。
就在此时，身后传来一个冰冷的声音："站住。"
        """

        analysis = enhancer.analyze_chapter_ending(test_chapter)
        print(f"✅ HookEnhancer测试成功:")
        print(f"  钩子类型: {analysis.hook_type.value}")
        print(f"  强度分数: {analysis.strength_score:.1f}/100")

        print(f"\n🎉 LLM集成测试全部通过！")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_llm_integration()
    exit(0 if success else 1)

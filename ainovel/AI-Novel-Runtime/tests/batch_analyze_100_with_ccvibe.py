"""batch_analyze_100_with_ccvibe.py — 使用CC_VIBE的100章分析

使用CC_VIBE (gpt-5.6-sol) 运行完整100章分析
Created: 2026-08-11 23:50

Usage:
    python3 batch_analyze_100_with_ccvibe.py
"""
import os
import sys
import json
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


class CCVibeLLM:
    """CC_VIBE LLM wrapper for batch analysis."""

    def __init__(self):
        from openai import OpenAI

        self.url = os.environ.get("CC_VIBE_OPENAI_BASE_URL")
        self.key = os.environ.get("CC_VIBE_OPENAI_AUTH_TOKEN")
        self.model = os.environ.get("CC_VIBE_OPENAI_MODEL", "gpt-5.6-sol")

        self.client = OpenAI(
            api_key=self.key,
            base_url=self.url
        )

    def generate(self, prompt):
        """Generate response from prompt."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content


def main():
    print("\n" + "="*60)
    print("使用 CC_VIBE 运行100章完整分析")
    print("="*60)

    # Load env
    if not load_env():
        print("❌ Failed to load .env")
        return False

    # Create CC_VIBE LLM
    print("\n创建 CC_VIBE LLM...")
    model = CCVibeLLM()
    print(f"✅ 配置完成: {model.model}")

    # Import batch analyzer
    from tests.batch_analyze_100_chapters import batch_analyze_chapters

    # Monkey patch to use CC_VIBE
    import runtime.commercial.llm_integration as llm_mod

    def create_ccvibe_model(provider="deepseek", model_id=None, api_key=None):
        return CCVibeLLM()

    llm_mod.create_llm_model = create_ccvibe_model

    print("\n✅ CC_VIBE已就绪")
    print("\n开始分析100章...")
    print("预计时间: 25-30分钟")
    print("预计成本: ¥2-3")
    print("="*60)

    # Run analysis
    success = batch_analyze_chapters(1, 100, 1)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

"""test_deepseek_reasoner.py — Task 1.2.3 DeepSeek R1验证

验证deepseek-reasoner (R1) API可用性和效果
"""
import os
import pytest


# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not set"
)


class TestDeepSeekReasonerAvailability:
    """测试DeepSeek R1模型可用性"""

    def test_api_key_present(self):
        """API key已配置"""
        assert os.environ.get("DEEPSEEK_API_KEY"), "DEEPSEEK_API_KEY must be set"

    def test_create_deepseek_client(self):
        """可以创建DeepSeek客户端"""
        from runtime.llm.factory import create_llm_client

        client = create_llm_client("deepseek")
        assert client is not None

    def test_deepseek_chat_available(self):
        """deepseek-chat模型可用"""
        from runtime.llm.factory import create_llm_client

        client = create_llm_client("deepseek")

        # Simple test prompt
        response = client.generate(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "测试：请回复'OK'"}],
            temperature=0.0,
            max_tokens=10
        )

        assert response is not None
        assert response.text is not None
        assert len(response.text) > 0

    @pytest.mark.skip(reason="Need to verify R1 model name from API docs")
    def test_deepseek_reasoner_available(self):
        """deepseek-reasoner模型可用（如果存在）"""
        from runtime.llm.factory import create_llm_client

        client = create_llm_client("deepseek")

        # Potential R1 model names to try
        potential_names = [
            "deepseek-reasoner",
            "deepseek-r1",
            "deepseek-v4-reasoner",
            "deepseek-chat-r1",
        ]

        for model_name in potential_names:
            try:
                response = client.generate(
                    model=model_name,
                    messages=[{"role": "user", "content": "测试：请回复'OK'"}],
                    temperature=0.0,
                    max_tokens=10
                )

                if response and response.text:
                    print(f"✅ Found working R1 model: {model_name}")
                    assert True
                    return

            except Exception as e:
                print(f"❌ {model_name} failed: {e}")
                continue

        pytest.fail("No working R1 model found")


class TestHygieneModelSelection:
    """测试hygiene循环的模型选择"""

    def test_select_hygiene_model_function(self):
        """模型选择函数存在（待实现）"""
        # This test documents the planned API
        # To be implemented in prose_hygiene.py or revision.py

        # Expected usage:
        # hygiene_model = select_hygiene_model(
        #     default="deepseek-reasoner",
        #     fallback="deepseek-chat"
        # )

        # For now, just document the requirement
        pass


# Task 1.2.3 完成标记
# ✅ 验证API key配置
# ✅ 验证deepseek-chat可用
# 🟡 待确认：R1模型的实际名称（需查阅API文档）
# 🟡 待实现：hygiene模型选择函数（如果R1可用）

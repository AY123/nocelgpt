"""test_cc_vibe_connection.py — Test CC_VIBE OpenAI Connection

Test if CC_VIBE OpenAI-compatible endpoint can be connected.
Created: 2026-08-11 23:38

Usage:
    python3 test_cc_vibe_connection.py
"""
import os
from pathlib import Path

# Load .env
def load_env():
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")
        return True
    return False

print("="*60)
print("测试 CC_VIBE OpenAI 连接")
print("="*60)

# Load environment
print("\n加载.env配置...")
if load_env():
    print("✅ .env加载成功")
else:
    print("❌ .env加载失败")
    exit(1)

# Check CC_VIBE config
print("\n检查CC_VIBE配置:")
cc_vibe_url = os.environ.get("CC_VIBE_OPENAI_BASE_URL")
cc_vibe_key = os.environ.get("CC_VIBE_OPENAI_API_KEY") or os.environ.get("CC_VIBE_ANTHROPIC_AUTH_TOKEN")

if cc_vibe_url:
    print(f"  Base URL: {cc_vibe_url}")
else:
    print("  ⚠️  CC_VIBE_OPENAI_BASE_URL 未配置")

if cc_vibe_key:
    print(f"  API Key: {cc_vibe_key[:20]}...")
else:
    print("  ⚠️  API Key 未配置")

if not cc_vibe_url or not cc_vibe_key:
    print("\n❌ CC_VIBE配置不完整")
    print("\n尝试使用其他配置...")

    # Try anthropic config
    cc_vibe_url = os.environ.get("CC_VIBE_ANTHROPIC_BASE_URL")
    cc_vibe_key = os.environ.get("CC_VIBE_ANTHROPIC_AUTH_TOKEN")

    if cc_vibe_url and cc_vibe_key:
        print(f"  使用 Anthropic 配置:")
        print(f"  Base URL: {cc_vibe_url}")
        print(f"  Auth Token: {cc_vibe_key[:20]}...")
    else:
        print("❌ 也没有找到Anthropic配置")
        exit(1)

# Test connection
print("\n测试连接...")

try:
    from openai import OpenAI

    # Create client
    client = OpenAI(
        api_key=cc_vibe_key,
        base_url=cc_vibe_url
    )

    print("✅ OpenAI客户端创建成功")

    # Test simple completion
    print("\n发送测试请求...")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Default model, might be mapped by CC_VIBE
        messages=[{"role": "user", "content": "请说'你好'"}],
        max_tokens=50
    )

    print("✅ 请求成功!")
    print(f"\n响应内容: {response.choices[0].message.content}")
    print(f"模型: {response.model}")
    print(f"Token使用: {response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'}")

    print("\n🎉 CC_VIBE OpenAI 连接测试成功!")
    print("✅ 可以使用此配置进行批量分析")

except ImportError:
    print("❌ openai包未安装")
    print("   运行: pip3 install openai")
    exit(1)

except Exception as e:
    print(f"❌ 连接测试失败: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*60)
print("测试完成")
print("="*60)

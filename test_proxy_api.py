#!/usr/bin/env python3
"""
测试代理服务 API 配置
"""
import sys
import json
from pathlib import Path

def test_proxy_api(api_key: str, base_url: str, model: str = "gemini-2.5-flash-lite"):
    """
    测试代理服务 API
    
    Args:
        api_key: API Key
        base_url: 代理服务的基础URL
        model: 模型名称
    """
    try:
        print("=" * 60)
        print("🔍 测试代理服务 API")
        print("=" * 60)
        print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '*' * 4}")
        print(f"🌐 Base URL: {base_url}")
        print(f"📋 Model: {model}")
        print("-" * 60)
        
        from google import genai
        from google.genai import types
        
        # 配置 HttpOptions
        http_options = types.HttpOptions(base_url=base_url)
        print("✅ HttpOptions 创建成功")
        
        # 初始化客户端
        print("\n📤 初始化客户端...")
        client = genai.Client(api_key=api_key, http_options=http_options)
        print("✅ 客户端初始化成功")
        
        # 创建聊天会话
        print(f"\n📤 创建聊天会话 (model: {model})...")
        chat = client.chats.create(model=model)
        print("✅ 聊天会话创建成功")
        
        # 发送测试消息
        print("\n📤 发送测试消息...")
        response = chat.send_message("Hello, please respond with 'API key is valid'")
        
        print("\n✅ API 调用成功！")
        print(f"📥 响应内容: {response.text}")
        print("\n" + "=" * 60)
        print("✅ 代理服务 API 验证成功！")
        return True
        
    except Exception as e:
        error_type = type(e).__name__
        error_str = str(e)
        print(f"\n❌ 错误类型: {error_type}")
        print(f"❌ 错误详情: {error_str[:500]}")
        print("\n" + "=" * 60)
        print("❌ 代理服务 API 验证失败！")
        
        # 错误分析
        print("\n💡 可能的原因：")
        if '404' in error_str or 'not found' in error_str.lower():
            print("   1. Base URL 路径不正确")
            print("   2. 代理服务的端点格式可能不同")
            print("   3. 尝试不同的 base_url 格式：")
            print("      - https://claude-relay.sding.me/gemini")
            print("      - https://claude-relay.sding.me/gemini/v1")
            print("      - https://claude-relay.sding.me/api/gemini")
        elif '400' in error_str or 'invalid' in error_str.lower():
            print("   1. API Key 格式不正确")
            print("   2. 代理服务可能不接受此格式的 key")
        elif 'connection' in error_str.lower() or 'timeout' in error_str.lower():
            print("   1. 无法连接到代理服务")
            print("   2. 检查网络连接")
            print("   3. 检查代理服务是否可访问")
        
        return False

if __name__ == "__main__":
    # 从配置文件读取
    config_file = Path("config/config.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        chatgpt_config = config.get('chatgpt', {})
        api_key = chatgpt_config.get('api_key', '')
        base_url = chatgpt_config.get('base_url', '')
        model = chatgpt_config.get('model', 'gemini-2.5-flash-lite')
        
        if not api_key:
            print("❌ 配置文件中没有 API Key")
            sys.exit(1)
        
        if not base_url:
            print("❌ 配置文件中没有 base_url")
            print("💡 请在 config.json 中添加 base_url 字段")
            sys.exit(1)
        
        # 运行测试
        success = test_proxy_api(api_key, base_url, model)
        sys.exit(0 if success else 1)
    else:
        print("❌ 未找到配置文件 config/config.json")
        sys.exit(1)

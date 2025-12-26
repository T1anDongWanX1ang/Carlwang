#!/usr/bin/env python3
"""
测试 Gemini API Key 是否有效
"""
import sys
from google import genai

def test_gemini_api(api_key: str, model: str = "gemini-2.5-flash-lite"):
    """
    测试 Gemini API Key
    
    Args:
        api_key: Gemini API Key
        model: 模型名称
    """
    try:
        print(f"🔑 测试 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '*' * 4}")
        print(f"📋 使用模型: {model}")
        print("-" * 50)
        
        # 初始化客户端
        client = genai.Client(api_key=api_key)
        print("✅ 客户端初始化成功")
        
        # 创建聊天会话
        chat = client.chats.create(model=model)
        print("✅ 聊天会话创建成功")
        
        # 发送测试消息
        print("\n📤 发送测试消息...")
        response = chat.send_message("Hello, please respond with 'API key is valid'")
        
        print("✅ API 调用成功！")
        print(f"📥 响应内容: {response.text}")
        print("\n" + "=" * 50)
        print("✅ Gemini API Key 验证成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}")
        print(f"❌ 错误详情: {str(e)}")
        print("\n" + "=" * 50)
        print("❌ Gemini API Key 验证失败！")
        
        # 检查是否是 API key 问题
        error_str = str(e).lower()
        if 'api' in error_str and 'key' in error_str:
            print("\n💡 提示:")
            print("   - API Key 可能无效或已过期")
            print("   - 请检查 API Key 是否正确复制")
            print("   - 确保 API Key 有访问 Gemini API 的权限")
            print("   - 可以在 https://aistudio.google.com/apikey 获取或管理 API Key")
        elif '400' in str(e) or 'invalid' in error_str:
            print("\n💡 提示:")
            print("   - API Key 格式可能不正确")
            print("   - 请确认使用的是 Gemini API Key，而不是其他 Google 服务的 Key")
        
        return False

if __name__ == "__main__":
    # 从命令行参数或配置文件读取 API key
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    else:
        # 从配置文件读取
        import json
        from pathlib import Path
        
        config_file = Path("config/config.json")
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            api_key = config.get('chatgpt', {}).get('api_key', '')
            model = config.get('chatgpt', {}).get('model', 'gemini-2.5-flash-lite')
        else:
            print("❌ 未找到配置文件 config/config.json")
            print("💡 使用方法: python test_gemini_api.py <API_KEY>")
            sys.exit(1)
    
    if not api_key:
        print("❌ API Key 为空")
        print("💡 使用方法: python test_gemini_api.py <API_KEY>")
        sys.exit(1)
    
    # 运行测试
    success = test_gemini_api(api_key, model if 'model' in locals() else "gemini-2.5-flash-lite")
    sys.exit(0 if success else 1)

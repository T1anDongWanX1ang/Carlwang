#!/usr/bin/env python3
"""
检查 Gemini API 配置
用于诊断远程服务器的配置问题
"""
import os
import json
from pathlib import Path

def check_config():
    """检查配置"""
    print("=" * 60)
    print("🔍 Gemini API 配置检查")
    print("=" * 60)
    
    # 1. 检查配置文件
    print("\n1️⃣ 检查配置文件...")
    config_file = Path("config/config.json")
    if config_file.exists():
        print(f"   ✅ 配置文件存在: {config_file}")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            api_key = config.get('chatgpt', {}).get('api_key', '')
            model = config.get('chatgpt', {}).get('model', '')
            
            if api_key:
                masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else '*' * 10
                print(f"   📋 API Key (配置文件): {masked_key}")
                print(f"   📋 Model (配置文件): {model}")
            else:
                print("   ❌ 配置文件中没有 API Key")
        except Exception as e:
            print(f"   ❌ 读取配置文件失败: {e}")
    else:
        print(f"   ❌ 配置文件不存在: {config_file}")
    
    # 2. 检查环境变量
    print("\n2️⃣ 检查环境变量...")
    gemini_key = os.getenv('GEMINI_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL')
    openai_model = os.getenv('OPENAI_MODEL')
    
    if gemini_key:
        masked_key = f"{gemini_key[:10]}...{gemini_key[-4:]}" if len(gemini_key) > 14 else '*' * 10
        print(f"   ✅ GEMINI_API_KEY: {masked_key}")
    else:
        print("   ⚠️  GEMINI_API_KEY 未设置")
    
    if openai_key:
        masked_key = f"{openai_key[:10]}...{openai_key[-4:]}" if len(openai_key) > 14 else '*' * 10
        print(f"   ⚠️  OPENAI_API_KEY: {masked_key} (会覆盖配置文件)")
    else:
        print("   ✅ OPENAI_API_KEY 未设置")
    
    if gemini_model:
        print(f"   ✅ GEMINI_MODEL: {gemini_model}")
    if openai_model:
        print(f"   ⚠️  OPENAI_MODEL: {openai_model} (会覆盖配置文件)")
    
    # 3. 检查实际使用的配置
    print("\n3️⃣ 实际使用的配置（环境变量优先）...")
    from src.utils.config_manager import config as app_config
    
    # 检查是否有环境变量覆盖
    if openai_key:
        print("   ⚠️  警告: OPENAI_API_KEY 环境变量会覆盖配置文件中的 Gemini API Key")
        print("   💡 解决方案:")
        print("      1. 取消设置 OPENAI_API_KEY: unset OPENAI_API_KEY")
        print("      2. 或者设置 GEMINI_API_KEY: export GEMINI_API_KEY=your-gemini-key")
    
    actual_key = app_config.get('chatgpt', {}).get('api_key', '')
    actual_model = app_config.get('chatgpt', {}).get('model', '')
    
    if actual_key:
        masked_key = f"{actual_key[:10]}...{actual_key[-4:]}" if len(actual_key) > 14 else '*' * 10
        print(f"   📋 实际使用的 API Key: {masked_key}")
        print(f"   📋 实际使用的 Model: {actual_model}")
        
        # 检查 API key 格式
        if actual_key.startswith('AIza'):
            print("   ✅ API Key 格式正确（标准 Google Gemini API Key）")
        elif actual_key.startswith('cr_'):
            print("   ⚠️  API Key 格式异常：以 'cr_' 开头")
            print("   ❌ 这不是标准的 Google Gemini API Key！")
            print("   💡 标准 Gemini API Key 应该以 'AIza' 开头")
            print("   💡 请访问 https://aistudio.google.com/apikey 获取正确的 API Key")
            print("   💡 如果这是代理服务的 key，可能需要修改代码支持代理")
        elif actual_key.startswith('sk-'):
            print("   ⚠️  API Key 格式看起来像 OpenAI API Key")
            print("   ❌ 错误: 这是 OpenAI API Key，不是 Gemini API Key！")
        else:
            print("   ⚠️  API Key 格式未知")
    else:
        print("   ❌ 没有找到 API Key")
    
    # 4. 测试 API
    print("\n4️⃣ 测试 Gemini API...")
    try:
        from google import genai
        print("   ✅ google-genai 模块已安装")
        
        if actual_key:
            try:
                client = genai.Client(api_key=actual_key)
                chat = client.chats.create(model=actual_model)
                response = chat.send_message("test")
                print("   ✅ API 调用成功！")
                print(f"   📥 响应: {response.text[:50]}...")
            except Exception as e:
                error_str = str(e)
                print(f"   ❌ API 调用失败: {error_str[:200]}")
                
                if 'API key not valid' in error_str or 'INVALID_ARGUMENT' in error_str:
                    print("\n   💡 问题诊断:")
                    if actual_key.startswith('cr_'):
                        print("      - ❌ API Key 格式错误：以 'cr_' 开头")
                        print("      - ❌ 这不是标准的 Google Gemini API Key")
                        print("      - ✅ 标准 Gemini API Key 应该以 'AIza' 开头，约39个字符")
                        print("      - 📖 获取方法：访问 https://aistudio.google.com/apikey")
                    else:
                        print("      - API Key 无效或已过期")
                        print("      - 请检查 API Key 是否正确")
                        print("      - 确保使用的是 Gemini API Key，不是 OpenAI API Key")
                    if openai_key:
                        print("      - ⚠️  检测到 OPENAI_API_KEY 环境变量，可能覆盖了正确的 Gemini Key")
        else:
            print("   ⚠️  无法测试：没有 API Key")
    except ImportError:
        print("   ❌ google-genai 模块未安装")
        print("   💡 安装命令: pip install google-genai")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)

if __name__ == "__main__":
    check_config()

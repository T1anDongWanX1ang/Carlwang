#!/usr/bin/env python3
"""
诊断远程服务器 Gemini API 问题
用于对比本地和远程的差异
"""
import os
import sys
import json
import socket
import datetime
from pathlib import Path

def check_system_info():
    """检查系统信息"""
    print("=" * 60)
    print("🔍 系统环境诊断")
    print("=" * 60)
    
    # 1. Python 版本
    print(f"\n1️⃣ Python 版本: {sys.version}")
    
    # 2. 系统时间
    print(f"\n2️⃣ 系统时间: {datetime.datetime.now()}")
    print(f"   时区: {datetime.datetime.now().astimezone().tzinfo}")
    
    # 3. 网络连接测试
    print("\n3️⃣ 网络连接测试...")
    test_hosts = [
        ("Google API", "generativelanguage.googleapis.com"),
        ("Google DNS", "8.8.8.8"),
    ]
    
    for name, host in test_hosts:
        try:
            if ':' in host:
                # IP address
                socket.create_connection((host.split(':')[0], int(host.split(':')[1])), timeout=5)
            else:
                # Domain name
                socket.create_connection((host, 443), timeout=5)
            print(f"   ✅ {name} ({host}): 连接成功")
        except Exception as e:
            print(f"   ❌ {name} ({host}): 连接失败 - {e}")
    
    # 4. 检查配置文件
    print("\n4️⃣ 配置文件检查...")
    config_file = Path("config/config.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        api_key = config.get('chatgpt', {}).get('api_key', '')
        model = config.get('chatgpt', {}).get('model', '')
        
        print(f"   ✅ 配置文件存在")
        print(f"   📋 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '*' * 10}")
        print(f"   📋 Model: {model}")
        print(f"   📋 API Key 长度: {len(api_key)}")
        print(f"   📋 API Key 前缀: {api_key[:3] if len(api_key) >= 3 else 'N/A'}")
    else:
        print(f"   ❌ 配置文件不存在")
    
    # 5. 检查环境变量
    print("\n5️⃣ 环境变量检查...")
    env_vars = ['GEMINI_API_KEY', 'OPENAI_API_KEY', 'GEMINI_MODEL', 'OPENAI_MODEL']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            masked = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else '*' * 10
            print(f"   ⚠️  {var}: {masked}")
        else:
            print(f"   ✅ {var}: 未设置")
    
    # 6. 检查 google-genai 模块
    print("\n6️⃣ Python 模块检查...")
    try:
        import google.genai as genai
        print(f"   ✅ google-genai 模块已安装")
        print(f"   📋 模块路径: {genai.__file__}")
        
        # 检查模块版本
        try:
            import google.genai.version
            print(f"   📋 版本信息: {google.genai.version.__version__ if hasattr(google.genai.version, '__version__') else '未知'}")
        except:
            pass
    except ImportError as e:
        print(f"   ❌ google-genai 模块未安装: {e}")
    
    # 7. 实际 API 调用测试
    print("\n7️⃣ API 调用测试...")
    if config_file.exists():
        api_key = config.get('chatgpt', {}).get('api_key', '')
        model = config.get('chatgpt', {}).get('model', 'gemini-2.5-flash-lite')
        
        if api_key:
            try:
                from google import genai
                
                print(f"   📤 初始化客户端...")
                client = genai.Client(api_key=api_key)
                print(f"   ✅ 客户端初始化成功")
                
                print(f"   📤 创建聊天会话 (model: {model})...")
                chat = client.chats.create(model=model)
                print(f"   ✅ 聊天会话创建成功")
                
                print(f"   📤 发送测试消息...")
                response = chat.send_message("test")
                print(f"   ✅ API 调用成功！")
                print(f"   📥 响应: {response.text[:100]}...")
                
            except Exception as e:
                error_type = type(e).__name__
                error_str = str(e)
                print(f"   ❌ API 调用失败")
                print(f"   📋 错误类型: {error_type}")
                print(f"   📋 错误信息: {error_str[:500]}")
                
                # 详细错误分析
                if '400' in error_str or 'INVALID_ARGUMENT' in error_str:
                    print(f"\n   🔍 错误分析:")
                    if 'API key not valid' in error_str:
                        print(f"      - API Key 被 Google 服务器拒绝")
                        print(f"      - 可能原因:")
                        print(f"        1. API Key 格式错误")
                        print(f"        2. API Key 已过期或被撤销")
                        print(f"        3. API Key 没有访问 Gemini API 的权限")
                        print(f"        4. 网络代理或防火墙问题")
                        print(f"        5. 服务器 IP 被 Google 限制")
                    elif 'invalid' in error_str.lower():
                        print(f"      - 参数无效")
                elif '403' in error_str or 'PERMISSION_DENIED' in error_str:
                    print(f"\n   🔍 错误分析:")
                    print(f"      - 权限被拒绝")
                    print(f"      - 可能原因:")
                    print(f"        1. API Key 没有访问权限")
                    print(f"        2. API Key 绑定了 IP 白名单")
                    print(f"        3. 配额已用完")
                elif 'network' in error_str.lower() or 'timeout' in error_str.lower():
                    print(f"\n   🔍 错误分析:")
                    print(f"      - 网络问题")
                    print(f"      - 可能原因:")
                    print(f"        1. 服务器无法访问 Google API")
                    print(f"        2. 防火墙阻止连接")
                    print(f"        3. DNS 解析问题")
        else:
            print(f"   ⚠️  没有 API Key，跳过测试")
    
    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    check_system_info()

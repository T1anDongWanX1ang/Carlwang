#!/usr/bin/env python3
"""
配置设置脚本
帮助用户快速设置项目配置文件
"""

import json
import os
import shutil
from pathlib import Path

def setup_config():
    """设置配置文件"""
    config_dir = Path("config")
    template_file = config_dir / "config.example.json"
    config_file = config_dir / "config.json"
    
    print("🚀 Twitter数据爬虫配置设置")
    print("=" * 50)
    
    # 检查模板文件是否存在
    if not template_file.exists():
        print("❌ 模板文件不存在：config/config.example.json")
        return False
    
    # 如果配置文件已存在，询问是否覆盖
    if config_file.exists():
        response = input("⚠️  配置文件已存在，是否覆盖？(y/N): ").strip().lower()
        if response != 'y':
            print("取消设置")
            return False
    
    # 读取模板文件
    with open(template_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("\n📝 请输入以下配置信息：")
    
    # TweetScout API配置
    print("\n1️⃣ TweetScout API配置:")
    api_key = input("请输入TweetScout API Key: ").strip()
    if api_key:
        config['api']['headers']['ApiKey'] = api_key
    
    # OpenAI API配置
    print("\n2️⃣ OpenAI API配置:")
    openai_key = input("请输入OpenAI API Key (sk-...): ").strip()
    if openai_key:
        config['chatgpt']['api_key'] = openai_key
    
    # 数据库配置
    print("\n3️⃣ 数据库配置:")
    db_host = input("请输入数据库主机地址 (默认: 35.209.219.220): ").strip()
    if db_host:
        config['database']['host'] = db_host
    
    db_name = input("请输入数据库名称 (默认: public_data): ").strip()
    if db_name:
        config['database']['database'] = db_name
    
    db_user = input("请输入数据库用户名 (默认: transaction): ").strip()
    if db_user:
        config['database']['username'] = db_user
    
    db_password = input("请输入数据库密码: ").strip()
    if db_password:
        config['database']['password'] = db_password
    
    # 保存配置文件
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("\n✅ 配置文件创建成功: config/config.json")
        print("\n🔧 下一步:")
        print("1. 检查配置文件内容是否正确")
        print("2. 运行测试: python main.py --mode test")
        print("3. 开始使用: python main.py --mode once")
        
        return True
        
    except Exception as e:
        print(f"❌ 保存配置文件失败: {e}")
        return False

def reset_config():
    """重置配置文件到模板状态"""
    config_dir = Path("config")
    template_file = config_dir / "config.example.json"
    config_file = config_dir / "config.json"
    
    if not template_file.exists():
        print("❌ 模板文件不存在")
        return False
    
    try:
        shutil.copy2(template_file, config_file)
        print("✅ 配置文件已重置为模板状态")
        return True
    except Exception as e:
        print(f"❌ 重置失败: {e}")
        return False

def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_config()
    else:
        setup_config()

if __name__ == "__main__":
    main()
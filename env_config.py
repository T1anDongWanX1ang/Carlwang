#!/usr/bin/env python3
"""
环境变量配置加载器
用于生产环境部署时从环境变量读取敏感配置
"""

import os
import json
from pathlib import Path

def load_config_with_env():
    """
    加载配置文件，支持环境变量覆盖敏感配置
    """
    # 读取基础配置文件
    config_file = Path("config/config.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        # 如果没有config.json，使用模板
        template_file = Path("config/config.json.template")
        with open(template_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    
    # 从环境变量覆盖敏感配置
    # TweetScout API
    if os.getenv('TWEETSCOUT_API_KEY'):
        config['api']['headers']['ApiKey'] = os.getenv('TWEETSCOUT_API_KEY')
    
    # OpenAI API
    if os.getenv('OPENAI_API_KEY'):
        config['chatgpt']['api_key'] = os.getenv('OPENAI_API_KEY')
    
    # 数据库配置
    if os.getenv('DB_HOST'):
        config['database']['host'] = os.getenv('DB_HOST')
    if os.getenv('DB_NAME'):
        config['database']['database'] = os.getenv('DB_NAME')
    if os.getenv('DB_USER'):
        config['database']['username'] = os.getenv('DB_USER')
    if os.getenv('DB_PASSWORD'):
        config['database']['password'] = os.getenv('DB_PASSWORD')
    if os.getenv('DB_PORT'):
        config['database']['port'] = int(os.getenv('DB_PORT'))
    
    # 验证必要的配置
    required_configs = [
        ('TweetScout API Key', config['api']['headers'].get('ApiKey')),
        ('OpenAI API Key', config['chatgpt'].get('api_key')),
        ('Database Host', config['database'].get('host')),
        ('Database Password', config['database'].get('password'))
    ]
    
    for name, value in required_configs:
        if not value or value.startswith('YOUR_'):
            print(f"❌ 缺少必要配置: {name}")
            print(f"请设置对应的环境变量或配置文件")
            return None
    
    print("✅ 配置加载成功（包含环境变量覆盖）")
    return config

def create_env_file():
    """
    创建环境变量模板文件
    """
    env_content = """# Twitter数据爬虫环境变量配置
# 复制此文件为 .env 并填入实际值

# TweetScout API配置
TWEETSCOUT_API_KEY=your-tweetscout-api-key

# OpenAI API配置  
OPENAI_API_KEY=your-openai-api-key

# 数据库配置
DB_HOST=your-database-host
DB_NAME=your-database-name
DB_USER=your-database-username
DB_PASSWORD=your-database-password
DB_PORT=9030

# 可选：运行模式
RUN_MODE=production
"""
    
    with open('.env.template', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 创建环境变量模板文件: .env.template")
    print("请复制为 .env 并填入实际值")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "create-env":
        create_env_file()
    else:
        config = load_config_with_env()
        if config:
            print("配置验证成功")
        else:
            print("配置验证失败")
            sys.exit(1)
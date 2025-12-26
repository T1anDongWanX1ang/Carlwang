#!/usr/bin/env python3
"""
测试 KOL 推文配置是否正确
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置环境变量使用 Twitter API
os.environ['TWITTER_API_BACKEND'] = 'twitterapi'

from src.utils.config_manager import config
from src.utils.logger import get_logger

logger = get_logger(__name__)

def test_config():
    """测试配置"""
    print("=" * 60)
    print("KOL 推文配置测试")
    print("=" * 60)

    # 1. 测试 API 配置
    print("\n【1. API 配置】")
    api_config = config.get('api_twitterapi', {})
    print(f"  基础 URL: {api_config.get('base_url')}")
    print(f"  Endpoint: {api_config.get('endpoints', {}).get('list_tweets')}")

    default_params = api_config.get('default_params', {})
    print(f"  默认 List ID: {default_params.get('list_id')}")
    print(f"  List IDs: {default_params.get('list_ids')}")
    print(f"  KOL List IDs: {default_params.get('list_ids_kol')}")
    print(f"  项目 List IDs: {default_params.get('list_ids_project')}")

    # 2. 测试数据库配置
    print("\n【2. 数据库配置】")
    db_config = config.get('database', {})
    tables = db_config.get('tables', {})
    print(f"  推文表: {tables.get('tweet')}")
    print(f"  KOL 推文表: {tables.get('tweet_kol')}")
    print(f"  项目推文表: {tables.get('tweet_project')}")
    print(f"  用户表: {tables.get('user')}")

    # 3. 测试环境变量
    print("\n【3. 环境变量】")
    backend = os.getenv('TWITTER_API_BACKEND', 'twitterapi')
    print(f"  TWITTER_API_BACKEND: {backend}")

    # 4. 测试 API 客户端
    print("\n【4. API 客户端】")
    try:
        from src.crawler import crawler
        print(f"  API 客户端类型: {type(crawler.api_client).__name__}")
        print(f"  API 客户端模块: {crawler.api_client.__class__.__module__}")
    except Exception as e:
        print(f"  错误: {e}")

    # 5. 验证配置
    print("\n【5. 配置验证】")
    issues = []

    # 检查 KOL List ID
    kol_list_ids = default_params.get('list_ids_kol', [])
    if not kol_list_ids:
        issues.append("⚠️  KOL List IDs 未配置")
    elif kol_list_ids == ["1896516371435122886"]:
        print("  ✅ KOL List IDs 正确: 1896516371435122886")
    else:
        issues.append(f"⚠️  KOL List IDs 可能不正确: {kol_list_ids}")

    # 检查表名
    tweet_table = tables.get('tweet')
    if tweet_table == "twitter_tweet":
        print("  ✅ 推文表名正确: twitter_tweet")
    else:
        issues.append(f"⚠️  推文表名可能不正确: {tweet_table}，应该是 twitter_tweet")

    # 检查 API 类型
    if backend == "twitterapi":
        print("  ✅ 使用 Twitter API")
    else:
        issues.append(f"⚠️  当前使用: {backend}，应该是 twitterapi")

    # 显示问题
    if issues:
        print("\n【⚠️ 发现的问题】")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n【✅ 所有配置检查通过】")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_config()

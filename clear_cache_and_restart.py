#!/usr/bin/env python3
"""
清理Python缓存并验证修复部署
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def clear_python_cache():
    """清理Python缓存"""
    print("🧹 清理Python缓存...")
    
    # 删除.pyc文件
    subprocess.run(["find", ".", "-name", "*.pyc", "-delete"], capture_output=True)
    print("✅ 删除.pyc文件")
    
    # 删除__pycache__目录
    for pycache_dir in Path(".").rglob("__pycache__"):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir)
            print(f"✅ 删除缓存目录: {pycache_dir}")
    
    # 清理importlib缓存
    try:
        import importlib
        importlib.invalidate_caches()
        print("✅ 清理importlib缓存")
    except Exception as e:
        print(f"⚠️ 清理importlib缓存失败: {e}")

def verify_debug_logging():
    """验证调试日志配置"""
    print("\n🔍 验证调试日志配置...")
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from src.utils.config_manager import config
        
        logging_config = config.get('logging', {})
        log_level = logging_config.get('level', 'INFO')
        log_format = logging_config.get('format', '')
        
        print(f"✅ 日志级别: {log_level}")
        print(f"✅ 日志格式: {log_format}")
        
        if log_level == 'DEBUG' and 'funcName' in log_format:
            print("✅ 调试日志配置正确")
            return True
        else:
            print("❌ 调试日志配置不正确")
            return False
            
    except Exception as e:
        print(f"❌ 验证日志配置失败: {e}")
        return False

def test_fix_deployment():
    """测试修复部署是否生效"""
    print("\n🧪 测试修复部署...")
    
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from src.utils.topic_analyzer import TopicAnalyzer
        from src.models.tweet import Tweet
        from datetime import datetime
        
        analyzer = TopicAnalyzer()
        
        # 创建简单的测试数据
        test_tweet = Tweet(
            id_str="1966200000000000001",
            full_text="测试修复部署的推文内容",
            created_at="2025-09-12 21:00:00",
            favorite_count=10,
            retweet_count=5,
            reply_count=2
        )
        
        # 模拟话题数据（无topic_id）
        topic_data = {
            'topic_name': '修复部署测试话题',
            'brief': '测试修复是否部署成功',
            'tweets': [test_tweet],
            'engagement_total': 17,
            'created_at': datetime.now()
        }
        
        print("✅ 创建测试数据")
        
        # 测试话题创建
        topic = analyzer._create_topic_from_data(topic_data)
        
        if topic:
            print("✅ 话题创建成功")
            print(f"   话题ID: {topic.topic_id}")
            print(f"   是否UUID格式: {topic.topic_id.startswith('topic_')}")
            
            if topic.summary:
                import json
                try:
                    summary_data = json.loads(topic.summary)
                    summary_topic_id = summary_data.get('topic_id', '')
                    
                    if summary_topic_id == topic.topic_id:
                        print("✅ Summary中topic_id匹配")
                        return True
                    else:
                        print(f"❌ Summary中topic_id不匹配: '{summary_topic_id}' vs '{topic.topic_id}'")
                        return False
                        
                except json.JSONDecodeError:
                    print("❌ Summary JSON解析失败")
                    return False
            else:
                print("❌ Summary为空")
                return False
        else:
            print("❌ 话题创建失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 清理缓存并验证修复部署")
    print("=" * 50)
    
    # 1. 清理缓存
    clear_python_cache()
    
    # 2. 验证配置
    config_ok = verify_debug_logging()
    
    # 3. 测试修复
    if config_ok:
        fix_ok = test_fix_deployment()
        
        print(f"\n{'='*50}")
        if fix_ok:
            print("🎉 修复部署验证成功！")
            print("✅ 缓存已清理")
            print("✅ 调试日志已配置")
            print("✅ 修复逻辑工作正常")
            print("\n🚀 现在可以运行生产服务:")
            print("   python main.py --mode topic")
        else:
            print("❌ 修复部署验证失败")
            print("需要检查代码部署情况")
    else:
        print("\n❌ 配置验证失败")
        print("需要检查config.json配置")

if __name__ == '__main__':
    main()
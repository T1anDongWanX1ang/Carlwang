#!/usr/bin/env python3
"""
调试topics表summary字段为null的问题
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.topic_dao import topic_dao
from src.utils.topic_analyzer import topic_analyzer
from src.utils.logger import setup_logger


def check_topics_summary_status():
    """检查topics表中summary字段的状态"""
    setup_logger()
    
    print("🔍 检查topics表summary字段状态")
    print("=" * 60)
    
    try:
        # 查看最近的topics记录
        sql = f"""
        SELECT topic_id, topic_name, created_at, brief, summary, update_time
        FROM {topic_dao.table_name} 
        ORDER BY created_at DESC 
        LIMIT 10
        """
        
        results = topic_dao.db_manager.execute_query(sql)
        
        if results:
            print(f"📊 最近10条topics记录:")
            null_count = 0
            non_null_count = 0
            
            for i, topic in enumerate(results, 1):
                summary = topic.get('summary')
                status = "NULL" if summary is None else f"长度:{len(str(summary))}"
                
                print(f"   {i}. {topic.get('topic_name', 'N/A')}")
                print(f"      Topic ID: {topic.get('topic_id')}")
                print(f"      创建时间: {topic.get('created_at')}")
                print(f"      Summary状态: {status}")
                
                if summary is None:
                    null_count += 1
                else:
                    non_null_count += 1
                    # 显示summary的前100个字符
                    preview = str(summary)[:100] + "..." if len(str(summary)) > 100 else str(summary)
                    print(f"      Summary预览: {preview}")
                print()
            
            print(f"📈 Summary统计:")
            print(f"   NULL数量: {null_count}")
            print(f"   非NULL数量: {non_null_count}")
            print(f"   NULL比例: {null_count/(null_count+non_null_count)*100:.1f}%")
            
        else:
            print("❌ 没有找到任何topics记录")
            
    except Exception as e:
        print(f"❌ 检查过程出错: {e}")
        import traceback
        traceback.print_exc()


def debug_summary_generation():
    """调试summary生成过程"""
    print("\n🔧 调试summary生成过程")
    print("=" * 60)
    
    try:
        # 模拟topic_analyzer的调用
        from src.models.tweet import Tweet
        from datetime import datetime
        
        # 创建测试数据
        test_tweets = [
            Tweet(
                id_str="debug_test_1",
                full_text="Bitcoin is showing strong bullish momentum with institutional adoption increasing",
                kol_id="44196397",
                created_at="Wed Jan 10 15:00:00 +0000 2024",
                created_at_datetime=datetime.now(),
                favorite_count=100,
                retweet_count=50
            ),
            Tweet(
                id_str="debug_test_2", 
                full_text="The crypto market is experiencing significant growth across multiple sectors",
                created_at="Wed Jan 10 15:15:00 +0000 2024",
                created_at_datetime=datetime.now(),
                favorite_count=75,
                retweet_count=30
            )
        ]
        
        topic_data = {
            'topic_name': 'Debug Test Topic',
            'brief': 'Testing summary generation for debugging purposes',
            'category': 'cryptocurrency',
            'key_entities': ['Bitcoin', 'crypto market'],
            'created_at': datetime.now()
        }
        
        print("📊 调用_generate_enhanced_topic_summary...")
        print(f"   推文数量: {len(test_tweets)}")
        print(f"   KOL推文数量: {sum(1 for t in test_tweets if hasattr(t, 'kol_id') and t.kol_id)}")
        
        # 直接调用方法
        summary = topic_analyzer._generate_enhanced_topic_summary(topic_data, test_tweets)
        
        print(f"📄 生成结果:")
        if summary is None:
            print("   ❌ 返回None")
        elif summary == "":
            print("   ⚠️ 返回空字符串")
        else:
            print(f"   ✅ 返回内容 (长度: {len(summary)})")
            print(f"   预览: {summary[:200]}...")
        
        return summary
        
    except Exception as e:
        print(f"❌ 调试summary生成时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_original_method():
    """测试原始的summary生成方法"""
    print("\n🔄 测试原始summary生成方法")
    print("=" * 60)
    
    try:
        from src.api.chatgpt_client import chatgpt_client
        
        # 使用原始方法
        test_tweets = [
            "Bitcoin is showing strong bullish momentum with institutional adoption increasing",
            "The crypto market is experiencing significant growth across multiple sectors",
            "DeFi protocols are gaining more mainstream attention and adoption"
        ]
        
        print("📊 调用原始generate_topic_summary...")
        original_summary = chatgpt_client.generate_topic_summary(
            topic_name="Test Original Method",
            related_tweets=test_tweets
        )
        
        print(f"📄 原始方法结果:")
        if original_summary is None:
            print("   ❌ 返回None")
        elif original_summary == "":
            print("   ⚠️ 返回空字符串")
        else:
            print(f"   ✅ 返回内容 (长度: {len(original_summary)})")
            print(f"   内容: {original_summary}")
            
        return original_summary
        
    except Exception as e:
        print(f"❌ 测试原始方法时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_chatgpt_client_status():
    """检查ChatGPT客户端状态"""
    print("\n⚙️ 检查ChatGPT客户端状态")
    print("=" * 60)
    
    try:
        from src.api.chatgpt_client import chatgpt_client
        
        # 检查基本配置
        print("📊 ChatGPT客户端配置:")
        if hasattr(chatgpt_client, 'api_key'):
            print(f"   API Key: {'已配置' if chatgpt_client.api_key else '未配置'}")
        if hasattr(chatgpt_client, 'model'):
            print(f"   模型: {getattr(chatgpt_client, 'model', 'N/A')}")
        if hasattr(chatgpt_client, 'timeout'):
            print(f"   超时: {getattr(chatgpt_client, 'timeout', 'N/A')}秒")
        
        # 测试简单请求
        print("\n🧪 测试简单API请求:")
        test_response = chatgpt_client._make_request(
            messages=[
                {"role": "system", "content": "你是一个测试助手"},
                {"role": "user", "content": "请回复'测试成功'"}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        if test_response:
            print(f"   ✅ API调用成功: {test_response}")
        else:
            print("   ❌ API调用失败")
            
    except Exception as e:
        print(f"❌ 检查ChatGPT客户端时出错: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("🚨 Topics表Summary字段NULL问题调试")
    print("=" * 80)
    
    # 运行各项检查
    check_topics_summary_status()
    enhanced_summary = debug_summary_generation()
    original_summary = test_original_method()
    check_chatgpt_client_status()
    
    # 总结问题
    print("\n" + "=" * 80)
    print("🎯 问题诊断总结:")
    
    if enhanced_summary is None and original_summary is None:
        print("❌ 所有summary生成方法都返回None - ChatGPT API问题")
    elif enhanced_summary is None and original_summary is not None:
        print("❌ 增强版方法有问题 - 修改逻辑错误")
    elif enhanced_summary is not None and original_summary is None:
        print("⚠️ 原始方法有问题但增强版正常 - 配置问题")
    else:
        print("✅ 方法本身正常 - 可能是调用时机或数据问题")


if __name__ == '__main__':
    main()
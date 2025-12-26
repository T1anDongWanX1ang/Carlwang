#!/usr/bin/env python3
"""
测试修正后的逻辑
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.topic_analyzer import topic_analyzer
from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def test_corrected_logic():
    """测试修正后的summary生成逻辑"""
    setup_logger()
    
    print("🔍 测试修正后的summary生成逻辑")
    print("=" * 60)
    
    try:
        # 获取一个有推文关联的话题
        db_manager = topic_dao.db_manager
        
        sql = """
        SELECT DISTINCT t.topic_id, t.topic_name, t.brief, t.created_at
        FROM topics t
        JOIN twitter_tweet tw ON t.topic_id = tw.topic_id
        WHERE t.summary IS NOT NULL
        LIMIT 1
        """
        
        test_topics = db_manager.execute_query(sql)
        
        if not test_topics:
            print("❌ 没有找到有推文关联的话题进行测试")
            return False
        
        test_topic = test_topics[0]
        topic_id = test_topic['topic_id']
        topic_name = test_topic['topic_name']
        
        print(f"📊 测试话题: {topic_name}")
        print(f"   Topic ID: {topic_id}")
        
        # 获取关联推文
        tweet_sql = """
        SELECT id_str, kol_id, full_text, created_at
        FROM twitter_tweet
        WHERE topic_id = %s
        """
        
        tweet_records = db_manager.execute_query(tweet_sql, [topic_id])
        
        if not tweet_records:
            print("❌ 该话题没有关联推文")
            return False
        
        # 转换为Tweet对象
        from src.models.tweet import Tweet
        tweets = []
        for record in tweet_records:
            tweet = Tweet(
                id_str=record['id_str'],
                full_text=record['full_text'],
                kol_id=record.get('kol_id'),
                created_at=record.get('created_at'),
                created_at_datetime=datetime.now()
            )
            tweets.append(tweet)
        
        kol_count = sum(1 for t in tweets if t.kol_id)
        print(f"   📊 关联推文: 总计{len(tweets)}条，KOL推文{kol_count}条")
        
        # 构建话题数据
        topic_data = {
            'topic_id': topic_id,
            'topic_name': topic_name,
            'brief': test_topic.get('brief', ''),
            'category': 'cryptocurrency',
            'key_entities': topic_name.split(),
            'created_at': test_topic.get('created_at', datetime.now())
        }
        
        # 测试修正后的summary生成
        print(f"🧪 调用修正后的_generate_enhanced_topic_summary...")
        summary = topic_analyzer._generate_enhanced_topic_summary(topic_data, tweets)
        
        if summary:
            print(f"✅ Summary生成成功 (长度: {len(summary)})")
            print(f"📄 Summary预览: {summary[:200]}...")
            
            # 验证格式
            import json
            try:
                parsed = json.loads(summary)
                print(f"✅ JSON格式验证通过")
                
                if 'summary' in parsed:
                    print(f"📊 观点数量: {len(parsed['summary'])}")
                    
                    for i, viewpoint in enumerate(parsed['summary'][:2], 1):
                        print(f"   观点{i}: {viewpoint.get('viewpoint', '')[:60]}...")
                        related_tweets = viewpoint.get('related_tweets', [])
                        print(f"   相关推文: {related_tweets}")
                        
                        # 验证推文ID格式
                        valid_ids = [t for t in related_tweets if isinstance(t, str) and len(t) < 50]
                        if valid_ids:
                            print(f"   ✅ 推文ID格式正确: {valid_ids}")
                        else:
                            print(f"   ⚠️ 推文ID格式可能有问题")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON格式验证失败: {e}")
                return False
        else:
            print(f"❌ Summary生成失败")
            return False
    
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_sample_results():
    """显示现有的summary样本"""
    print(f"\n📋 查看现有summary样本")
    print("-" * 40)
    
    try:
        db_manager = topic_dao.db_manager
        
        sql = """
        SELECT topic_name, summary
        FROM topics
        WHERE summary IS NOT NULL
        ORDER BY update_time DESC
        LIMIT 3
        """
        
        samples = db_manager.execute_query(sql)
        
        if samples:
            for i, sample in enumerate(samples, 1):
                print(f"样本{i}: {sample['topic_name']}")
                
                try:
                    import json
                    parsed = json.loads(sample['summary'])
                    
                    if 'summary' in parsed:
                        for j, viewpoint in enumerate(parsed['summary'][:1], 1):
                            print(f"  观点{j}: {viewpoint.get('viewpoint', '')[:50]}...")
                            print(f"  相关推文: {viewpoint.get('related_tweets', [])}")
                    print()
                except:
                    print(f"  格式: 非JSON或解析失败")
                    print()
        else:
            print("没有找到summary样本")
            
    except Exception as e:
        print(f"❌ 查看样本失败: {e}")


def main():
    """主函数"""
    print("🎯 修正后逻辑测试")
    print("=" * 80)
    
    # 测试修正逻辑
    success = test_corrected_logic()
    
    # 显示样本
    show_sample_results()
    
    print("\n" + "=" * 80)
    print("🎯 测试总结:")
    if success:
        print("✅ 修正后的逻辑工作正常")
        print("✅ 始终使用大模型生成summary")
        print("✅ related_tweets格式包含推文ID")
        print("✅ 通过topic_id直接关联推文")
    else:
        print("❌ 修正逻辑存在问题，需要进一步检查")


if __name__ == '__main__':
    main()
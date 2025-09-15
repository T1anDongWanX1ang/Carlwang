#!/usr/bin/env python3
"""
修复topics表中为null的summary字段
为没有summary的话题生成KOL观点分析总结
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.utils.topic_analyzer import topic_analyzer
from src.models.tweet import Tweet
from src.utils.logger import setup_logger


def get_null_summary_topics(limit: int = 50):
    """获取summary为null的话题"""
    try:
        db_manager = topic_dao.db_manager
        
        sql = """
        SELECT topic_id, topic_name, brief, created_at
        FROM topics 
        WHERE summary IS NULL 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        
        results = db_manager.execute_query(sql, [limit])
        return results if results else []
        
    except Exception as e:
        print(f"❌ 获取null summary话题失败: {e}")
        return []


def get_topic_related_tweets_by_id(topic_id: str):
    """通过topic_id直接获取关联的推文"""
    try:
        db_manager = tweet_dao.db_manager
        
        sql = """
        SELECT id_str, kol_id, full_text, created_at,
               favorite_count, retweet_count, reply_count, view_count
        FROM twitter_tweet
        WHERE topic_id = %s
        ORDER BY created_at DESC
        """
        
        tweet_records = db_manager.execute_query(sql, [topic_id])
        
        if not tweet_records:
            return []
        
        # 转换为Tweet对象
        tweets = []
        for record in tweet_records:
            from src.models.tweet import Tweet
            tweet = Tweet(
                id_str=record['id_str'],
                full_text=record['full_text'],
                kol_id=record.get('kol_id'),
                created_at=record.get('created_at'),
                created_at_datetime=datetime.now(),
                favorite_count=record.get('favorite_count', 0),
                retweet_count=record.get('retweet_count', 0),
                reply_count=record.get('reply_count', 0),
                view_count=record.get('view_count', 0)
            )
            tweets.append(tweet)
        
        return tweets
        
    except Exception as e:
        print(f"❌ 获取话题关联推文失败: {e}")
        return []


def fix_topic_summary(topic_data):
    """为单个话题生成summary（使用topic_id直接关联）"""
    try:
        topic_name = topic_data['topic_name']
        topic_id = topic_data['topic_id']
        print(f"🔧 处理话题: {topic_name}")
        print(f"   Topic ID: {topic_id}")
        
        # 通过topic_id直接获取关联推文
        related_tweets = get_topic_related_tweets_by_id(topic_id)
        
        if not related_tweets:
            print(f"   ⚠️ 没有找到关联推文，跳过")
            return False
        
        print(f"   📊 找到 {len(related_tweets)} 条关联推文")
        
        # 检查KOL推文情况
        kol_tweets = [t for t in related_tweets if hasattr(t, 'kol_id') and t.kol_id]
        print(f"   🎯 其中 {len(kol_tweets)} 条KOL推文")
        
        # 构建话题数据用于summary生成
        topic_summary_data = {
            'topic_id': topic_id,
            'topic_name': topic_name,
            'brief': topic_data.get('brief', ''),
            'category': 'cryptocurrency',
            'key_entities': topic_name.split(),
            'created_at': topic_data.get('created_at', datetime.now())
        }
        
        # 始终使用AI生成summary（不再区分是否有KOL）
        summary = topic_analyzer._generate_enhanced_topic_summary(topic_summary_data, related_tweets)
        
        if summary:
            print(f"   ✅ AI生成summary成功 (长度: {len(summary)})")
            
            # 更新数据库
            db_manager = topic_dao.db_manager
            update_sql = """
            UPDATE topics 
            SET summary = %s, update_time = %s 
            WHERE topic_id = %s
            """
            
            result = db_manager.execute_update(update_sql, [
                summary, 
                datetime.now(), 
                topic_id
            ])
            
            if result:
                print(f"   ✅ 数据库更新成功")
                return True
            else:
                print(f"   ❌ 数据库更新失败")
                return False
        else:
            print(f"   ❌ AI summary生成失败")
            return False
            
    except Exception as e:
        print(f"❌ 处理话题 {topic_data.get('topic_name', 'Unknown')} 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    setup_logger()
    
    print("🚀 修复topics表null summary字段")
    print("=" * 60)
    
    # 获取需要修复的话题
    null_topics = get_null_summary_topics(30)  # 处理最近30个话题
    
    if not null_topics:
        print("✅ 没有发现需要修复的话题")
        return
    
    print(f"📊 发现 {len(null_topics)} 个需要修复的话题")
    
    # 批量处理
    success_count = 0
    skip_count = 0
    
    for i, topic in enumerate(null_topics, 1):
        print(f"\n处理进度: {i}/{len(null_topics)}")
        print(f"话题: {topic['topic_name']}")
        print(f"创建时间: {topic['created_at']}")
        
        if fix_topic_summary(topic):
            success_count += 1
        else:
            skip_count += 1
    
    # 输出结果
    print("\n" + "=" * 60)
    print("🎯 修复结果统计:")
    print(f"   总处理数量: {len(null_topics)}")
    print(f"   修复成功: {success_count}")
    print(f"   跳过/失败: {skip_count}")
    print(f"   成功率: {success_count/len(null_topics)*100:.1f}%")
    
    if success_count > 0:
        print(f"\n✅ 成功为 {success_count} 个话题生成了summary")
    
    if skip_count > 0:
        print(f"\n⚠️ {skip_count} 个话题未能生成summary（可能缺少相关推文）")


if __name__ == '__main__':
    main()
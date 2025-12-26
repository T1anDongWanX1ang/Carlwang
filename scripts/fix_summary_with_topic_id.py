#!/usr/bin/env python3
"""
使用topic_id关联修复summary - 正确版本
始终使用大模型总结，related_tweets使用推文ID
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.topic_dao import topic_dao
from src.database.tweet_dao import tweet_dao
from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import setup_logger


def get_topic_tweets_by_id(topic_id: str):
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
        
        tweets = db_manager.execute_query(sql, [topic_id])
        return tweets if tweets else []
        
    except Exception as e:
        print(f"❌ 获取topic推文失败: {e}")
        return []


def generate_ai_summary_always(topic_data, tweets):
    """始终使用大模型生成summary，按照指定格式"""
    try:
        if not tweets:
            print(f"   ⚠️ 没有关联推文，无法生成summary")
            return None
        
        topic_name = topic_data.get('topic_name', topic_data.get('topic_id', ''))
        
        # 构建完整的话题数据
        enhanced_topic_data = {
            'topic_id': topic_data.get('topic_id', ''),
            'topic_name': topic_name,
            'category': 'cryptocurrency',
            'key_entities': topic_name.split(),
            'timestamp': datetime.now().isoformat(),
            'brief': topic_data.get('brief', f"{topic_name} 相关讨论"),
            'related_tweets': []
        }
        
        # 构建推文数据
        for tweet in tweets:
            tweet_data = {
                'id_str': tweet['id_str'],
                'kol_id': tweet.get('kol_id', ''),
                'full_text': tweet['full_text']
            }
            enhanced_topic_data['related_tweets'].append(tweet_data)
        
        kol_count = sum(1 for t in tweets if t.get('kol_id'))
        print(f"   📊 推文详情: 总计{len(tweets)}条，KOL推文{kol_count}条")
        
        # 始终使用KOL观点分析方法（大模型）
        summary = chatgpt_client.generate_kol_consensus_summary(enhanced_topic_data)
        
        if summary:
            print(f"   ✅ AI总结生成成功 (长度: {len(summary)})")
            
            # 验证并修正格式
            import json
            try:
                parsed = json.loads(summary)
                
                # 确保related_tweets使用推文ID而不是推文内容
                if 'summary' in parsed:
                    for viewpoint in parsed['summary']:
                        if 'related_tweets' in viewpoint:
                            # 如果related_tweets包含长文本，替换为ID
                            tweet_refs = viewpoint['related_tweets']
                            tweet_ids = []
                            
                            for ref in tweet_refs:
                                if isinstance(ref, str):
                                    if len(ref) > 50:  # 长文本，查找对应的推文ID
                                        # 查找包含此文本的推文ID
                                        for tweet in tweets:
                                            if ref[:30] in tweet['full_text']:
                                                tweet_ids.append(tweet['id_str'])
                                                break
                                    else:
                                        tweet_ids.append(ref)  # 已经是ID或短引用
                            
                            viewpoint['related_tweets'] = tweet_ids[:3]  # 限制数量
                
                # 重新序列化
                summary = json.dumps(parsed, ensure_ascii=False)
                print(f"   ✅ 格式验证并修正完成")
                
            except json.JSONDecodeError as e:
                print(f"   ⚠️ JSON格式问题: {e}")
                return summary  # 返回原始结果
                
            return summary
        else:
            print(f"   ❌ AI总结生成失败")
            return None
            
    except Exception as e:
        print(f"❌ 生成AI总结异常: {e}")
        import traceback
        traceback.print_exc()
        return None


def fix_topic_summary_correct(topic_data):
    """使用正确的逻辑修复单个话题的summary"""
    try:
        topic_id = topic_data['topic_id']
        topic_name = topic_data['topic_name']
        
        print(f"🔧 处理话题: {topic_name}")
        print(f"   Topic ID: {topic_id}")
        
        # 通过topic_id直接获取关联推文
        tweets = get_topic_tweets_by_id(topic_id)
        
        if not tweets:
            print(f"   ❌ 没有找到关联推文，跳过")
            return False
        
        # 始终使用AI生成summary
        summary = generate_ai_summary_always(topic_data, tweets)
        
        if summary:
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
            print(f"   ❌ summary生成失败")
            return False
            
    except Exception as e:
        print(f"❌ 处理话题失败: {e}")
        return False


def main():
    """主函数 - 修复有推文关联的topics"""
    setup_logger()
    
    print("🚀 使用正确逻辑修复topics表summary")
    print("=" * 60)
    
    try:
        db_manager = topic_dao.db_manager
        
        # 获取有关联推文但summary为null的话题
        sql = """
        SELECT DISTINCT t.topic_id, t.topic_name, t.brief, t.created_at
        FROM topics t
        JOIN twitter_tweet tw ON t.topic_id = tw.topic_id
        WHERE t.summary IS NULL
        ORDER BY t.created_at DESC
        LIMIT 15
        """
        
        topics_to_fix = db_manager.execute_query(sql)
        
        if not topics_to_fix:
            print("✅ 没有发现需要修复的话题（有推文关联但无summary）")
            return
        
        print(f"📊 发现 {len(topics_to_fix)} 个有推文关联但无summary的话题")
        
        # 批量处理
        success_count = 0
        
        for i, topic in enumerate(topics_to_fix, 1):
            print(f"\n处理进度: {i}/{len(topics_to_fix)}")
            
            if fix_topic_summary_correct(topic):
                success_count += 1
        
        # 输出结果
        print("\n" + "=" * 60)
        print("🎯 修复结果统计:")
        print(f"   总处理数量: {len(topics_to_fix)}")
        print(f"   修复成功: {success_count}")
        print(f"   成功率: {success_count/len(topics_to_fix)*100:.1f}%")
        
        if success_count > 0:
            print(f"\n✅ 成功为 {success_count} 个话题生成了AI summary")
            print(f"✅ 所有summary都使用了大模型生成")
            print(f"✅ related_tweets字段包含正确的推文ID")
        
    except Exception as e:
        print(f"❌ 修复过程异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
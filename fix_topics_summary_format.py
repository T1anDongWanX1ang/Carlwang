#!/usr/bin/env python3
"""
批量修复topics表中summary字段的格式问题
修复两个主要问题：
1. topic_id字段使用话题名称而非正确的topic_id格式
2. related_tweets字段包含占位符或推文内容而非推文ID
"""
import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.utils.logger import setup_logger


def find_problematic_records(limit: int = None):
    """查找有问题的summary记录"""
    sql = """
    SELECT topic_id, topic_name, summary, update_time
    FROM topics
    WHERE summary IS NOT NULL
    AND summary != ''
    AND summary != 'null'
    ORDER BY update_time DESC
    """
    
    if limit:
        sql += f" LIMIT {limit}"
    
    records = tweet_dao.db_manager.execute_query(sql)
    
    problematic = []
    
    for record in records:
        try:
            summary = record['summary']
            if not summary:
                continue
                
            parsed = json.loads(summary)
            needs_fix = False
            issues = []
            
            # 检查topic_id格式
            if 'topic_id' in parsed:
                topic_id_in_summary = str(parsed['topic_id'])
                if not topic_id_in_summary.startswith('topic_'):
                    needs_fix = True
                    issues.append(f"topic_id格式错误: {topic_id_in_summary}")
            
            # 检查related_tweets格式
            if 'summary' in parsed:
                for viewpoint in parsed['summary']:
                    if 'related_tweets' in viewpoint:
                        for tweet_ref in viewpoint['related_tweets']:
                            if isinstance(tweet_ref, str):
                                if (not tweet_ref.isdigit() or 
                                    len(tweet_ref) < 10 or 
                                    tweet_ref in ['initial_discussion', 'discussion', 'mentioned']):
                                    needs_fix = True
                                    issues.append(f"related_tweets格式问题: {tweet_ref}")
                                    break
            
            if needs_fix:
                problematic.append({
                    'record': record,
                    'issues': issues
                })
                
        except json.JSONDecodeError:
            problematic.append({
                'record': record,
                'issues': ['JSON格式错误']
            })
        except Exception as e:
            print(f"检查记录异常: {e}")
    
    return problematic


def get_related_tweets_for_topic(topic_id: str, limit: int = 10):
    """获取话题相关的推文ID"""
    sql = """
    SELECT id_str, kol_id, full_text
    FROM twitter_tweet
    WHERE topic_id = %s
    AND kol_id IS NOT NULL
    AND full_text IS NOT NULL
    AND LENGTH(full_text) > 20
    ORDER BY created_at_datetime DESC
    LIMIT %s
    """
    
    return tweet_dao.db_manager.execute_query(sql, [topic_id, limit])


def fix_summary_record(record, issues):
    """修复单条summary记录"""
    topic_id = record['topic_id']
    topic_name = record['topic_name']
    summary = record['summary']
    
    print(f"\n🔧 修复记录: {topic_name} ({topic_id})")
    print(f"   问题: {', '.join(issues)}")
    
    try:
        # 解析原始summary
        parsed = json.loads(summary)
        fixed = False
        
        # 修复topic_id字段
        if 'topic_id' in parsed:
            old_topic_id = parsed['topic_id']
            if not str(old_topic_id).startswith('topic_'):
                parsed['topic_id'] = topic_id  # 使用数据库中的正确topic_id
                print(f"   ✓ 修复topic_id: {old_topic_id} -> {topic_id}")
                fixed = True
        else:
            parsed['topic_id'] = topic_id
            print(f"   ✓ 添加topic_id: {topic_id}")
            fixed = True
        
        # 获取相关推文ID用于修复related_tweets
        related_tweets = get_related_tweets_for_topic(topic_id, 20)
        available_tweet_ids = [tweet['id_str'] for tweet in related_tweets if tweet['id_str']]
        
        if not available_tweet_ids:
            print(f"   ⚠️ 没有找到相关推文，跳过related_tweets修复")
            if not fixed:
                return False
        else:
            # 修复related_tweets字段
            if 'summary' in parsed:
                for viewpoint in parsed['summary']:
                    if 'related_tweets' in viewpoint:
                        tweet_refs = viewpoint['related_tweets']
                        valid_tweet_ids = []
                        
                        for ref in tweet_refs:
                            if isinstance(ref, str):
                                ref = ref.strip()
                                
                                # 检查是否是有效的推文ID
                                if ref.isdigit() and 10 <= len(ref) <= 25:
                                    valid_tweet_ids.append(ref)
                                elif ref in ['initial_discussion', 'discussion', 'mentioned']:
                                    # 用实际推文ID替换占位符
                                    for tweet_id in available_tweet_ids:
                                        if tweet_id not in valid_tweet_ids:
                                            valid_tweet_ids.append(tweet_id)
                                            break
                                elif len(ref) > 50:
                                    # 长文本，尝试匹配推文内容
                                    matched = False
                                    for tweet in related_tweets:
                                        if ref[:30] in tweet.get('full_text', ''):
                                            if tweet['id_str'] not in valid_tweet_ids:
                                                valid_tweet_ids.append(tweet['id_str'])
                                                matched = True
                                                break
                                    if not matched and available_tweet_ids:
                                        # 没匹配到，用第一个可用的
                                        for tweet_id in available_tweet_ids:
                                            if tweet_id not in valid_tweet_ids:
                                                valid_tweet_ids.append(tweet_id)
                                                break
                                else:
                                    # 其他情况，假设是推文ID
                                    valid_tweet_ids.append(ref)
                        
                        # 确保至少有一个推文ID
                        if not valid_tweet_ids and available_tweet_ids:
                            valid_tweet_ids = available_tweet_ids[:3]
                        
                        # 限制数量并更新
                        old_refs = viewpoint['related_tweets']
                        viewpoint['related_tweets'] = valid_tweet_ids[:3]
                        
                        if old_refs != valid_tweet_ids[:3]:
                            print(f"   ✓ 修复related_tweets: {len(old_refs)}个 -> {len(valid_tweet_ids[:3])}个有效ID")
                            fixed = True
        
        if fixed:
            # 重新序列化并更新数据库
            new_summary = json.dumps(parsed, ensure_ascii=False)
            
            update_sql = """
            UPDATE topics 
            SET summary = %s, update_time = %s
            WHERE topic_id = %s
            """
            
            affected_rows = tweet_dao.db_manager.execute_update(
                update_sql, 
                [new_summary, datetime.now(), topic_id]
            )
            
            if affected_rows > 0:
                print(f"   ✅ 数据库更新成功")
                return True
            else:
                print(f"   ❌ 数据库更新失败")
                return False
        else:
            print(f"   ℹ️ 无需修复")
            return True
            
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON解析失败: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 修复过程异常: {e}")
        return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量修复topics表summary字段格式问题')
    parser.add_argument('--limit', type=int, help='限制处理记录数量')
    parser.add_argument('--dry-run', action='store_true', help='只检查不修复')
    
    args = parser.parse_args()
    
    setup_logger()
    
    print("🔧 批量修复topics表summary字段格式")
    print("=" * 80)
    
    try:
        # 查找有问题的记录
        print("1️⃣ 查找有问题的记录...")
        problematic_records = find_problematic_records(args.limit)
        
        if not problematic_records:
            print("✅ 没有找到需要修复的记录")
            return
        
        print(f"📊 找到 {len(problematic_records)} 条需要修复的记录")
        
        if args.dry_run:
            print(f"\n🔍 预览模式 (--dry-run)")
            for i, item in enumerate(problematic_records, 1):
                record = item['record']
                issues = item['issues']
                print(f"\n{i}. {record['topic_name']} ({record['topic_id']})")
                print(f"   问题: {', '.join(issues)}")
            return
        
        # 开始修复
        print(f"\n2️⃣ 开始修复记录...")
        
        success_count = 0
        failed_count = 0
        
        for i, item in enumerate(problematic_records, 1):
            record = item['record']
            issues = item['issues']
            
            print(f"\n处理进度: {i}/{len(problematic_records)}")
            
            try:
                if fix_summary_record(record, issues):
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"   ❌ 修复异常: {e}")
                failed_count += 1
        
        # 输出统计结果
        print(f"\n3️⃣ 修复结果统计")
        print("=" * 80)
        print(f"✅ 修复成功: {success_count} 条")
        print(f"❌ 修复失败: {failed_count} 条")
        print(f"📊 总处理数: {success_count + failed_count} 条")
        print(f"🎯 成功率: {success_count/(success_count+failed_count)*100:.1f}%")
        
        if success_count > 0:
            print(f"\n🎉 已成功修复 {success_count} 条记录的summary格式问题！")
        
        if failed_count > 0:
            print(f"\n⚠️ 仍有 {failed_count} 条记录修复失败，请手动检查")
        
    except Exception as e:
        print(f"❌ 批量修复失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
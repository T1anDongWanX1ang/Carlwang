#!/usr/bin/env python3
"""
批量更新用户语言类型
根据用户的推文内容和个人资料描述，自动检测并更新用户的主要语言类型
"""
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.tweet_dao import tweet_dao
from src.database.user_dao import user_dao
from src.utils.language_detector import get_language_detector
from src.utils.logger import setup_logger


def update_user_languages(limit: int = None, batch_size: int = 100):
    """
    批量更新用户语言类型
    
    Args:
        limit: 最大处理数量，None表示处理所有用户
        batch_size: 批处理大小
    """
    setup_logger()
    
    print("🚀 开始批量更新用户语言类型")
    print("=" * 60)
    
    try:
        # 初始化语言检测器
        language_detector = get_language_detector(tweet_dao.db_manager)
        
        # 1. 获取需要更新的用户
        print("1️⃣ 查询需要更新的用户")
        print("-" * 40)
        
        # 查询语言字段为空的用户
        sql = """
        SELECT u.id_str, u.screen_name, u.name, u.description, u.followers_count
        FROM twitter_user u
        WHERE u.language IS NULL
        AND u.id_str IN (
            SELECT DISTINCT t.kol_id 
            FROM twitter_tweet t 
            WHERE t.kol_id IS NOT NULL
        )
        ORDER BY u.followers_count DESC
        """
        
        if limit:
            sql += f" LIMIT {limit}"
        
        users_to_update = tweet_dao.db_manager.execute_query(sql)
        
        if not users_to_update:
            print("✅ 没有需要更新的用户")
            return
        
        print(f"📊 找到 {len(users_to_update)} 个用户需要更新语言类型")
        
        # 2. 批量处理
        total_updated = 0
        total_failed = 0
        
        for i in range(0, len(users_to_update), batch_size):
            batch = users_to_update[i:i + batch_size]
            
            print(f"\n2️⃣ 处理第 {i//batch_size + 1} 批 ({len(batch)} 个用户)")
            print("-" * 40)
            
            batch_updated = 0
            batch_failed = 0
            
            for user_data in batch:
                user_id = user_data['id_str']
                user_desc = user_data.get('description', '')
                user_name = user_data.get('screen_name', 'unknown')
                
                try:
                    # 检测用户语言
                    detected_language = language_detector.detect_user_language(
                        user_id=user_id,
                        user_description=user_desc,
                        recent_days=30,
                        min_tweets=2
                    )
                    
                    # 更新数据库
                    update_sql = """
                    UPDATE twitter_user 
                    SET language = %s, update_time = %s 
                    WHERE id_str = %s
                    """
                    
                    affected_rows = tweet_dao.db_manager.execute_update(
                        update_sql, 
                        [detected_language, datetime.now(), user_id]
                    )
                    
                    if affected_rows > 0:
                        print(f"✅ {user_name} ({user_id}): {detected_language}")
                        batch_updated += 1
                    else:
                        print(f"❌ {user_name} ({user_id}): 更新失败")
                        batch_failed += 1
                        
                except Exception as e:
                    print(f"❌ {user_name} ({user_id}): 处理异常 - {e}")
                    batch_failed += 1
            
            total_updated += batch_updated
            total_failed += batch_failed
            
            print(f"📊 第 {i//batch_size + 1} 批结果: 成功 {batch_updated}, 失败 {batch_failed}")
        
        # 3. 统计结果
        print(f"\n3️⃣ 最终统计")
        print("-" * 40)
        print(f"✅ 成功更新: {total_updated} 个用户")
        print(f"❌ 更新失败: {total_failed} 个用户")
        print(f"📊 总处理数: {total_updated + total_failed} 个用户")
        
        # 4. 语言分布统计
        print(f"\n4️⃣ 语言分布统计")
        print("-" * 40)
        
        language_stats_sql = """
        SELECT 
            language,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM twitter_user WHERE language IS NOT NULL), 2) as percentage
        FROM twitter_user
        WHERE language IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
        """
        
        stats = tweet_dao.db_manager.execute_query(language_stats_sql)
        
        for stat in stats:
            print(f"📈 {stat['language']}: {stat['count']} 用户 ({stat['percentage']}%)")
        
    except Exception as e:
        print(f"❌ 批量更新失败: {e}")
        import traceback
        traceback.print_exc()


def update_specific_users(user_ids: list):
    """
    更新指定用户的语言类型
    
    Args:
        user_ids: 用户ID列表
    """
    setup_logger()
    
    print(f"🎯 更新指定用户语言类型")
    print("=" * 60)
    
    try:
        language_detector = get_language_detector(tweet_dao.db_manager)
        
        updated = 0
        failed = 0
        
        for user_id in user_ids:
            try:
                # 获取用户信息
                user = user_dao.get_user_by_id(user_id)
                if not user:
                    print(f"❌ 用户不存在: {user_id}")
                    failed += 1
                    continue
                
                # 检测语言
                detected_language = language_detector.detect_user_language(
                    user_id=user_id,
                    user_description=user.description,
                    recent_days=30,
                    min_tweets=2
                )
                
                # 更新数据库
                update_sql = """
                UPDATE twitter_user 
                SET language = %s, update_time = %s 
                WHERE id_str = %s
                """
                
                affected_rows = tweet_dao.db_manager.execute_update(
                    update_sql, 
                    [detected_language, datetime.now(), user_id]
                )
                
                if affected_rows > 0:
                    print(f"✅ {user.screen_name} ({user_id}): {detected_language}")
                    updated += 1
                else:
                    print(f"❌ {user.screen_name} ({user_id}): 更新失败")
                    failed += 1
                    
            except Exception as e:
                print(f"❌ 用户 {user_id}: 处理异常 - {e}")
                failed += 1
        
        print(f"\n📊 更新结果: 成功 {updated}, 失败 {failed}")
        
    except Exception as e:
        print(f"❌ 指定用户更新失败: {e}")


def check_language_detection_quality():
    """
    检查语言检测质量
    """
    setup_logger()
    
    print("🔍 检查语言检测质量")
    print("=" * 60)
    
    try:
        # 1. 检查已更新的用户样本
        sample_sql = """
        SELECT u.id_str, u.screen_name, u.description, u.language,
               COUNT(t.id_str) as tweet_count
        FROM twitter_user u
        LEFT JOIN twitter_tweet t ON u.id_str = t.kol_id
        WHERE u.language IS NOT NULL
        GROUP BY u.id_str, u.screen_name, u.description, u.language
        HAVING tweet_count >= 3
        ORDER BY tweet_count DESC
        LIMIT 10
        """
        
        samples = tweet_dao.db_manager.execute_query(sample_sql)
        
        print("📋 语言检测样本:")
        for sample in samples:
            print(f"  {sample['screen_name']} ({sample['language']}): {sample['tweet_count']} 条推文")
            if sample['description']:
                desc_preview = sample['description'][:50] + "..." if len(sample['description']) > 50 else sample['description']
                print(f"    描述: {desc_preview}")
        
        # 2. 统计检测结果
        stats_sql = """
        SELECT 
            language,
            COUNT(*) as user_count,
            AVG(followers_count) as avg_followers,
            MAX(followers_count) as max_followers
        FROM twitter_user 
        WHERE language IS NOT NULL
        GROUP BY language
        """
        
        stats = tweet_dao.db_manager.execute_query(stats_sql)
        
        print(f"\n📊 语言检测统计:")
        for stat in stats:
            print(f"  {stat['language']}: {stat['user_count']} 用户, 平均粉丝 {stat['avg_followers']:.0f}, 最大粉丝 {stat['max_followers']}")
        
    except Exception as e:
        print(f"❌ 质量检查失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量更新用户语言类型')
    parser.add_argument('--limit', type=int, help='最大处理数量')
    parser.add_argument('--batch-size', type=int, default=100, help='批处理大小')
    parser.add_argument('--users', nargs='+', help='指定要更新的用户ID列表')
    parser.add_argument('--check-quality', action='store_true', help='检查语言检测质量')
    
    args = parser.parse_args()
    
    if args.check_quality:
        check_language_detection_quality()
    elif args.users:
        update_specific_users(args.users)
    else:
        update_user_languages(limit=args.limit, batch_size=args.batch_size)


if __name__ == '__main__':
    main()
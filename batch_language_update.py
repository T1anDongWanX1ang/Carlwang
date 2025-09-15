#!/usr/bin/env python3
"""
批量更新用户语言信息脚本
用于处理数据库中language为null的现有用户记录
"""

import time
import sys
from datetime import datetime
from src.database.user_dao import UserDAO
from src.utils.user_language_integration import UserLanguageIntegration
from src.api.chatgpt_client import chatgpt_client


def main():
    """主处理函数"""
    print("开始批量语言检测...")
    print(f"开始时间: {datetime.now()}")
    
    # 初始化
    dao = UserDAO()
    integration = UserLanguageIntegration(
        db_manager=dao.db_manager,
        chatgpt_client=chatgpt_client
    )
    
    # 获取初始统计
    null_count_sql = 'SELECT COUNT(*) as count FROM twitter_user WHERE language IS NULL'
    initial_null_count = dao.db_manager.execute_query(null_count_sql)[0]['count']
    print(f"初始待处理用户数: {initial_null_count}")
    
    processed_total = 0
    batch_size = 20  # 较小的批次以确保稳定性
    batch_num = 0
    
    while True:
        batch_num += 1
        
        # 获取下一批待处理用户
        get_batch_sql = f'SELECT id_str FROM twitter_user WHERE language IS NULL LIMIT {batch_size}'
        batch_users = dao.db_manager.execute_query(get_batch_sql)
        
        if not batch_users:
            print("所有用户处理完成！")
            break
        
        user_ids = [user['id_str'] for user in batch_users]
        print(f"\n--- 第 {batch_num} 批 ({len(user_ids)} 用户) ---")
        
        try:
            batch_start_time = time.time()
            
            # 处理当前批次
            results = integration.update_existing_users_language(
                user_ids=user_ids,
                force_update=False
            )
            
            batch_end_time = time.time()
            batch_duration = batch_end_time - batch_start_time
            
            # 统计结果
            batch_success = len(results)
            processed_total += batch_success
            
            print(f"批次完成: {batch_success}/{len(user_ids)} 成功")
            print(f"批次耗时: {batch_duration:.2f}秒")
            
            # 统计语言分布
            if results:
                languages = {}
                for lang in results.values():
                    languages[lang] = languages.get(lang, 0) + 1
                print(f"本批语言分布: {languages}")
            
            # 检查剩余数量
            current_null_count = dao.db_manager.execute_query(null_count_sql)[0]['count']
            print(f"剩余待处理: {current_null_count}")
            
            # 每处理10批显示总体进度
            if batch_num % 10 == 0:
                print(f"\n=== 进度报告 ===")
                print(f"已处理批次: {batch_num}")
                print(f"总计处理用户: {processed_total}")
                print(f"剩余用户: {current_null_count}")
                print(f"完成比例: {((initial_null_count - current_null_count) / initial_null_count * 100):.1f}%")
            
        except Exception as e:
            print(f"批次 {batch_num} 处理失败: {e}")
            # 遇到错误时稍作等待后继续
            time.sleep(5)
            continue
        
        # 批次间休息，避免过度占用资源
        time.sleep(2)
        
        # 安全检查：如果单批次处理时间过长，增加休息时间
        if batch_duration > 30:
            print("检测到处理较慢，延长休息时间...")
            time.sleep(5)
    
    # 最终统计
    final_stats_sql = '''
    SELECT 
        language,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM twitter_user), 2) as percentage
    FROM twitter_user 
    WHERE language IS NOT NULL 
    GROUP BY language 
    ORDER BY count DESC
    '''
    
    final_null_count = dao.db_manager.execute_query(null_count_sql)[0]['count']
    final_stats = dao.db_manager.execute_query(final_stats_sql)
    
    print(f"\n=== 最终统计 ===")
    print(f"结束时间: {datetime.now()}")
    print(f"总计处理用户: {processed_total}")
    print(f"剩余null记录: {final_null_count}")
    print(f"\n最终语言分布:")
    for stat in final_stats:
        print(f"  {stat['language']}: {stat['count']} ({stat['percentage']}%)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断处理")
        sys.exit(0)
    except Exception as e:
        print(f"程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
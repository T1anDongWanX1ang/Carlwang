#!/usr/bin/env python3
"""
数据迁移脚本：将 twitter_tweet_project_new 表数据迁移到 twitter_tweet_back_test_cmc300 表
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.database.connection import db_manager
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_field_mapping():
    """
    获取字段映射关系
    返回：(相同字段列表, 源表字段映射到目标表字段的字典)
    """
    # 相同的字段（直接映射）
    common_fields = [
        'id_str',
        'in_reply_to_status_id_str', 
        'full_text',
        'created_at_datetime',
        'bookmark_count',
        'favorite_count',
        'quote_count', 
        'reply_count',
        'retweet_count',
        'view_count',
        'update_time',
        'tweet_url',
        'sentiment',
        'link_url',
        'isAnnounce',
        'summary',
        'is_activity',
        'activity_detail',
        'is_retweet'
    ]
    
    # 特殊映射关系（源表字段 -> 目标表字段）
    # kol_id 映射到 user_id，user_name 设置为 NULL
    special_mapping = {
        'kol_id': 'user_id'
    }
    
    return common_fields, special_mapping

def migrate_data_batch(batch_size=1000):
    """
    批量迁移数据
    
    Args:
        batch_size: 每批处理的数据量
    """
    try:
        # 获取字段映射
        common_fields, special_mapping = get_field_mapping()
        
        # 检查源表数据量
        count_sql = "SELECT COUNT(*) as total FROM twitter_tweet_project_new"
        count_result = db_manager.execute_query(count_sql)
        total_records = count_result[0]['total'] if count_result else 0
        
        logger.info(f"源表 twitter_tweet_project_new 总共有 {total_records} 条记录")
        
        if total_records == 0:
            logger.warning("源表没有数据，无需迁移")
            return
        
        # 构建查询SQL - 包含公共字段和特殊映射字段
        source_fields = common_fields + list(special_mapping.keys())  # 添加 kol_id
        source_fields_str = ', '.join(source_fields)
        select_sql = f"SELECT {source_fields_str} FROM twitter_tweet_project_new ORDER BY id_str"
        
        # 构建目标字段列表
        target_fields = common_fields + ['user_id', 'user_name']  # 目标表字段
        target_fields_str = ', '.join(target_fields)
        
        logger.info(f"开始迁移数据，批量大小: {batch_size}")
        logger.info(f"字段映射: kol_id -> user_id, user_name -> NULL")
        
        # 分批处理数据
        offset = 0
        success_count = 0
        error_count = 0
        
        while offset < total_records:
            try:
                # 获取一批数据
                batch_sql = f"{select_sql} LIMIT {batch_size} OFFSET {offset}"
                batch_data = db_manager.execute_query(batch_sql)
                
                if not batch_data:
                    break
                
                logger.info(f"处理第 {offset//batch_size + 1} 批，记录范围: {offset+1}-{offset+len(batch_data)}")
                
                # 准备批量插入的数据
                batch_values = []
                for record in batch_data:
                    # 准备插入数据
                    insert_values = []
                    
                    # 添加公共字段的值
                    for field in common_fields:
                        insert_values.append(record.get(field))
                    
                    # 添加特殊映射字段的值
                    insert_values.append(record.get('kol_id'))  # user_id 从 kol_id 获取
                    insert_values.append(None)  # user_name 设置为 NULL
                    
                    batch_values.append(tuple(insert_values))
                
                # 执行批量插入
                if batch_values:
                    placeholders = ', '.join(['%s'] * len(target_fields))
                    values_placeholder = f"({placeholders})"
                    all_values_placeholder = ', '.join([values_placeholder] * len(batch_values))
                    
                    batch_insert_sql = f"""
                    INSERT INTO twitter_tweet_back_test_cmc300 ({target_fields_str})
                    VALUES {all_values_placeholder}
                    """
                    
                    # 展开所有值为一个扁平列表
                    flat_values = []
                    for values_tuple in batch_values:
                        flat_values.extend(values_tuple)
                    
                    affected_rows = db_manager.execute_update(batch_insert_sql, tuple(flat_values))
                    
                    if affected_rows > 0:
                        success_count += len(batch_data)
                        logger.info(f"批量插入成功: {affected_rows} 条记录")
                    else:
                        error_count += len(batch_data)
                        logger.warning(f"批量插入失败")
                
                offset += batch_size
                
                # 显示进度
                progress = min(100, (offset / total_records) * 100)
                logger.info(f"迁移进度: {progress:.1f}% ({success_count}/{total_records})")
                
            except Exception as e:
                logger.error(f"处理批次失败: offset={offset}, 错误: {e}")
                error_count += len(batch_data) if 'batch_data' in locals() else batch_size
                offset += batch_size
                continue
        
        logger.info(f"数据迁移完成！成功: {success_count} 条，失败: {error_count} 条")
        
        # 验证迁移结果
        verify_migration()
        
    except Exception as e:
        logger.error(f"数据迁移过程失败: {e}")
        raise

def verify_migration():
    """验证迁移结果"""
    try:
        # 检查目标表记录数
        target_count_sql = "SELECT COUNT(*) as total FROM twitter_tweet_back_test_cmc300"
        target_result = db_manager.execute_query(target_count_sql)
        target_count = target_result[0]['total'] if target_result else 0
        
        # 检查源表记录数
        source_count_sql = "SELECT COUNT(*) as total FROM twitter_tweet_project_new"
        source_result = db_manager.execute_query(source_count_sql)
        source_count = source_result[0]['total'] if source_result else 0
        
        logger.info(f"迁移验证 - 源表记录数: {source_count}, 目标表记录数: {target_count}")
        
        if target_count > 0:
            # 抽样检查几条记录
            sample_sql = """
            SELECT id_str, full_text, created_at_datetime, sentiment 
            FROM twitter_tweet_back_test_cmc300 
            ORDER BY id_str 
            LIMIT 3
            """
            sample_result = db_manager.execute_query(sample_sql)
            
            logger.info("目标表样本数据:")
            for record in sample_result:
                logger.info(f"  ID: {record['id_str']}, 内容: {record['full_text'][:50]}...")
        
    except Exception as e:
        logger.error(f"验证迁移结果失败: {e}")

def clear_target_table():
    """清空目标表（可选）"""
    try:
        clear_sql = "DELETE FROM twitter_tweet_back_test_cmc300"
        affected_rows = db_manager.execute_update(clear_sql)
        logger.info(f"已清空目标表，删除了 {affected_rows} 条记录")
        
    except Exception as e:
        logger.error(f"清空目标表失败: {e}")
        raise

def main():
    """主函数"""
    logger.info("开始数据迁移任务")
    
    try:
        # 命令行参数处理
        clear_target = False
        batch_size = 1000
        
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                if arg == '--clear':
                    clear_target = True
                elif arg.startswith('--batch='):
                    try:
                        batch_size = int(arg.split('=')[1])
                    except ValueError:
                        logger.warning("批量大小参数无效，使用默认值")
                elif arg == '--help':
                    print("用法: python migrate_data.py [选项]")
                    print("选项:")
                    print("  --clear          清空目标表")
                    print("  --batch=N        设置批量大小（默认1000）")
                    print("  --help           显示帮助信息")
                    return 0
        else:
            # 如果没有命令行参数，使用交互模式
            try:
                clear_choice = input("是否要清空目标表 twitter_tweet_back_test_cmc300？(y/N): ").strip().lower()
                if clear_choice in ['y', 'yes']:
                    clear_target = True
                
                batch_input = input(f"请输入批量处理大小 (默认 {batch_size}): ").strip()
                if batch_input:
                    batch_size = int(batch_input)
            except (EOFError, KeyboardInterrupt):
                logger.info("使用默认设置：不清空目标表，批量大小=1000")
            except ValueError:
                logger.warning("输入的批量大小无效，使用默认值")
        
        # 如果需要清空目标表
        if clear_target:
            clear_target_table()
        
        # 执行迁移
        start_time = datetime.now()
        migrate_data_batch(batch_size)
        end_time = datetime.now()
        
        duration = end_time - start_time
        logger.info(f"迁移任务完成，耗时: {duration}")
        
    except KeyboardInterrupt:
        logger.info("用户中断了迁移任务")
    except Exception as e:
        logger.error(f"迁移任务失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
检查数据库表结构
"""
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(__file__))

from src.database.tweet_dao import tweet_dao

def check_table_structure():
    """检查推文表结构"""
    
    try:
        # 连接数据库
        if not tweet_dao.db_manager.test_connection():
            print("数据库连接失败")
            return
        
        # 查询表结构
        sql = "DESCRIBE twitter_tweet"
        
        result = tweet_dao.db_manager.execute_query(sql)
        
        if result:
            print("推文表结构:")
            print("=" * 80)
            print(f"{'Field':<25} {'Type':<20} {'Null':<8} {'Key':<8} {'Default':<15} {'Extra':<10}")
            print("-" * 80)
            
            has_kol_id = False
            has_is_valid = False
            has_sentiment = False
            has_tweet_url = False
            
            for row in result:
                field = row.get('Field', '')
                type_info = row.get('Type', '')
                null_info = row.get('Null', '')
                key_info = row.get('Key', '')
                default_info = str(row.get('Default', '')) if row.get('Default') is not None else 'NULL'
                extra_info = row.get('Extra', '')
                
                print(f"{field:<25} {type_info:<20} {null_info:<8} {key_info:<8} {default_info:<15} {extra_info:<10}")
                
                # 检查新字段
                if field == 'kol_id':
                    has_kol_id = True
                elif field == 'is_valid':
                    has_is_valid = True
                elif field == 'sentiment':
                    has_sentiment = True
                elif field == 'tweet_url':
                    has_tweet_url = True
            
            print("\n字段检查结果:")
            print(f"- kol_id字段: {'✅ 存在' if has_kol_id else '❌ 不存在'}")
            print(f"- is_valid字段: {'✅ 存在' if has_is_valid else '❌ 不存在'}")
            print(f"- sentiment字段: {'✅ 存在' if has_sentiment else '❌ 不存在'}")
            print(f"- tweet_url字段: {'✅ 存在' if has_tweet_url else '❌ 不存在'}")
        else:
            print("无法获取表结构")
            
    except Exception as e:
        print(f"检查表结构失败: {e}")
        
    finally:
        tweet_dao.db_manager.close()

if __name__ == '__main__':
    check_table_structure()
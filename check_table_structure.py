#!/usr/bin/env python3
"""
检查数据库表结构
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.database.connection import db_manager

def check_table_structure():
    """检查表结构"""
    try:
        # 检查项目推文表结构
        project_table_sql = "DESCRIBE twitter_tweet_project_new"
        project_columns = db_manager.execute_query(project_table_sql)
        
        print("=== twitter_tweet_project_new 表结构 ===")
        for col in project_columns:
            print(f"{col['Field']:<30} {col['Type']:<20} {col['Null']:<5} {col['Key']:<5} {col['Default']}")
        
        print("\n=== twitter_tweet 表结构 ===")
        # 检查常规推文表结构
        regular_table_sql = "DESCRIBE twitter_tweet"
        regular_columns = db_manager.execute_query(regular_table_sql)
        
        for col in regular_columns:
            print(f"{col['Field']:<30} {col['Type']:<20} {col['Null']:<5} {col['Key']:<5} {col['Default']}")
        
        # 找出差异
        project_fields = {col['Field'] for col in project_columns}
        regular_fields = {col['Field'] for col in regular_columns}
        
        print(f"\n=== 字段差异分析 ===")
        print(f"项目表独有字段: {project_fields - regular_fields}")
        print(f"常规表独有字段: {regular_fields - project_fields}")
        
    except Exception as e:
        print(f"检查表结构失败: {e}")

if __name__ == "__main__":
    check_table_structure()

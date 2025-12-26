#!/usr/bin/env python3
"""
为tweet表添加缺失的字段
确保project_id和topic_id字段存在
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.utils.logger import setup_logger


def add_missing_fields():
    """为tweet表添加缺失的字段"""
    setup_logger()
    
    print("🔧 检查并添加tweet表缺失的字段")
    print("=" * 60)
    
    # 需要添加的字段定义
    fields_to_add = [
        {
            'name': 'kol_id',
            'definition': 'kol_id VARCHAR(50) NULL COMMENT "KOL用户ID"'
        },
        {
            'name': 'entity_id', 
            'definition': 'entity_id VARCHAR(64) NULL COMMENT "实体ID（向后兼容）"'
        },
        {
            'name': 'project_id',
            'definition': 'project_id VARCHAR(64) NULL COMMENT "项目ID（project_xxx格式）"'
        },
        {
            'name': 'topic_id',
            'definition': 'topic_id VARCHAR(64) NULL COMMENT "话题ID（topic_xxx格式）"'
        },
        {
            'name': 'is_valid',
            'definition': 'is_valid TINYINT(1) NULL COMMENT "是否为有效内容"'
        },
        {
            'name': 'sentiment',
            'definition': 'sentiment VARCHAR(20) NULL COMMENT "情绪倾向"'
        },
        {
            'name': 'tweet_url',
            'definition': 'tweet_url TEXT NULL COMMENT "推文URL"'
        }
    ]
    
    table_name = 'twitter_data_product.twitter_tweet'
    
    for field in fields_to_add:
        field_name = field['name']
        field_def = field['definition']
        
        print(f"\n🔍 检查字段: {field_name}")
        
        try:
            # 尝试添加字段（如果已存在会报错，但不影响）
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {field_def}"
            
            print(f"📝 执行SQL: {alter_sql}")
            
            db_manager.execute_update(alter_sql)
            print(f"✅ 字段 {field_name} 添加成功")
            
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg or "Duplicate column name" in error_msg:
                print(f"ℹ️  字段 {field_name} 已存在，跳过")
            else:
                print(f"❌ 添加字段 {field_name} 失败: {e}")
    
    print(f"\n🎉 字段检查和添加完成！")


def verify_fields():
    """验证字段是否成功添加"""
    print(f"\n🔍 验证字段是否存在...")
    
    try:
        # 尝试查询一条包含所有字段的数据
        sql = """
        SELECT id_str, kol_id, entity_id, project_id, topic_id, is_valid, sentiment, tweet_url
        FROM twitter_data_product.twitter_tweet 
        LIMIT 1
        """
        
        result = db_manager.execute_query(sql)
        print(f"✅ 所有字段验证成功！可以查询包含新字段的数据。")
        
        if result:
            print(f"📊 示例数据字段:")
            for key in result[0].keys():
                print(f"   - {key}")
        
        return True
        
    except Exception as e:
        print(f"❌ 字段验证失败: {e}")
        return False


def main():
    """主函数"""
    print("🎯 Tweet表字段更新工具")
    print("=" * 80)
    
    try:
        # 1. 添加缺失字段
        add_missing_fields()
        
        # 2. 验证字段
        verify_success = verify_fields()
        
        if verify_success:
            print(f"\n🎊 所有字段更新成功！")
            print("现在可以正确存储project_id和topic_id到数据库了。")
            return True
        else:
            print(f"\n⚠️ 字段验证失败，请检查数据库权限。")
            return False
            
    except Exception as e:
        print(f"\n❌ 更新过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
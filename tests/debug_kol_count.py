#!/usr/bin/env python3
"""
调试KOL数据表，分析为什么总是只有17条数据
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.kol_dao import kol_dao
from src.utils.logger import setup_logger


def analyze_kol_table():
    """分析KOL表的数据情况"""
    setup_logger()
    
    print("🔍 分析KOL表数据情况")
    print("=" * 60)
    
    try:
        # 1. 查看表的总记录数
        sql_total = f"SELECT COUNT(*) as total FROM {kol_dao.table_name}"
        total_result = kol_dao.db_manager.execute_query(sql_total)
        total_count = total_result[0]['total'] if total_result else 0
        
        print(f"1. KOL表总记录数: {total_count}")
        
        # 2. 查看活跃KOL的筛选条件
        print(f"\n2. 活跃KOL筛选条件分析:")
        print(f"   - influence_score >= 30.0")
        print(f"   - trust_rating >= 5.0")
        
        # 3. 按照不同条件统计数据
        queries = [
            {
                "name": "influence_score >= 30.0",
                "sql": f"SELECT COUNT(*) as count FROM {kol_dao.table_name} WHERE influence_score >= 30.0"
            },
            {
                "name": "trust_rating >= 5.0", 
                "sql": f"SELECT COUNT(*) as count FROM {kol_dao.table_name} WHERE trust_rating >= 5.0"
            },
            {
                "name": "influence_score >= 30.0 AND trust_rating >= 5.0",
                "sql": f"SELECT COUNT(*) as count FROM {kol_dao.table_name} WHERE influence_score >= 30.0 AND trust_rating >= 5.0"
            },
            {
                "name": "influence_score IS NOT NULL",
                "sql": f"SELECT COUNT(*) as count FROM {kol_dao.table_name} WHERE influence_score IS NOT NULL"
            },
            {
                "name": "trust_rating IS NOT NULL",
                "sql": f"SELECT COUNT(*) as count FROM {kol_dao.table_name} WHERE trust_rating IS NOT NULL"
            }
        ]
        
        for query in queries:
            try:
                result = kol_dao.db_manager.execute_query(query["sql"])
                count = result[0]['count'] if result else 0
                print(f"   {query['name']}: {count} 条")
            except Exception as e:
                print(f"   {query['name']}: 查询失败 - {e}")
        
        # 4. 查看influence_score和trust_rating的分布
        print(f"\n3. 数据分布分析:")
        
        # influence_score分布
        influence_dist_sql = f"""
        SELECT 
            CASE 
                WHEN influence_score IS NULL THEN 'NULL'
                WHEN influence_score < 10 THEN '< 10'
                WHEN influence_score < 20 THEN '10-20'
                WHEN influence_score < 30 THEN '20-30'
                WHEN influence_score < 50 THEN '30-50'
                WHEN influence_score < 80 THEN '50-80'
                ELSE '>= 80'
            END as score_range,
            COUNT(*) as count
        FROM {kol_dao.table_name}
        GROUP BY score_range
        ORDER BY count DESC
        """
        
        try:
            influence_results = kol_dao.db_manager.execute_query(influence_dist_sql)
            print("   influence_score分布:")
            for row in influence_results:
                print(f"     {row['score_range']}: {row['count']} 条")
        except Exception as e:
            print(f"   influence_score分布查询失败: {e}")
        
        # trust_rating分布
        trust_dist_sql = f"""
        SELECT 
            CASE 
                WHEN trust_rating IS NULL THEN 'NULL'
                WHEN trust_rating < 3 THEN '< 3'
                WHEN trust_rating < 5 THEN '3-5'
                WHEN trust_rating < 7 THEN '5-7'
                WHEN trust_rating < 9 THEN '7-9'
                ELSE '>= 9'
            END as rating_range,
            COUNT(*) as count
        FROM {kol_dao.table_name}
        GROUP BY rating_range
        ORDER BY count DESC
        """
        
        try:
            trust_results = kol_dao.db_manager.execute_query(trust_dist_sql)
            print("   trust_rating分布:")
            for row in trust_results:
                print(f"     {row['rating_range']}: {row['count']} 条")
        except Exception as e:
            print(f"   trust_rating分布查询失败: {e}")
        
        # 5. 查看具体的活跃KOL数据
        print(f"\n4. 活跃KOL详情 (前10条):")
        active_kol_sql = f"""
        SELECT kol_id, type, influence_score, trust_rating, is_kol100, summary
        FROM {kol_dao.table_name}
        WHERE influence_score >= 30.0
        AND trust_rating >= 5.0
        ORDER BY influence_score DESC, is_kol100 DESC
        LIMIT 10
        """
        
        try:
            active_kols = kol_dao.db_manager.execute_query(active_kol_sql)
            for i, kol in enumerate(active_kols, 1):
                print(f"   {i}. {kol['kol_id']}")
                print(f"      类型: {kol['type']}")
                print(f"      影响力: {kol['influence_score']}")
                print(f"      信任度: {kol['trust_rating']}")
                print(f"      KOL100: {kol['is_kol100']}")
                print(f"      描述: {kol['summary'][:50] if kol['summary'] else 'None'}...")
                print()
        except Exception as e:
            print(f"   活跃KOL详情查询失败: {e}")
        
        # 6. 使用DAO方法验证
        print(f"5. DAO方法验证:")
        active_kols_dao = kol_dao.get_active_kols()
        print(f"   get_active_kols()返回: {len(active_kols_dao)} 条")
        
        # 7. 检查表结构
        print(f"\n6. 表结构检查:")
        try:
            desc_sql = f"DESCRIBE {kol_dao.table_name}"
            desc_result = kol_dao.db_manager.execute_query(desc_sql)
            
            print("   字段列表:")
            for row in desc_result:
                field_name = row.get('Field', row.get('field', ''))
                field_type = row.get('Type', row.get('type', ''))
                field_null = row.get('Null', row.get('null', ''))
                print(f"     {field_name}: {field_type}, Null={field_null}")
        except Exception as e:
            print(f"   表结构查询失败: {e}")
        
    except Exception as e:
        print(f"❌ 分析过程出错: {e}")
        import traceback
        traceback.print_exc()


def test_different_thresholds():
    """测试不同的阈值设置"""
    print(f"\n7. 测试不同阈值:")
    print("=" * 60)
    
    thresholds = [
        (0, 0),      # 无限制
        (10, 3),     # 低门槛
        (20, 4),     # 中低门槛
        (30, 5),     # 当前门槛
        (50, 6),     # 高门槛
        (80, 8),     # 很高门槛
    ]
    
    for influence_min, trust_min in thresholds:
        try:
            # 直接查询数据库
            sql = f"""
            SELECT COUNT(*) as count
            FROM {kol_dao.table_name}
            WHERE influence_score >= {influence_min}
            AND trust_rating >= {trust_min}
            """
            
            result = kol_dao.db_manager.execute_query(sql)
            count = result[0]['count'] if result else 0
            
            print(f"   influence>={influence_min}, trust>={trust_min}: {count} 条")
            
        except Exception as e:
            print(f"   阈值({influence_min}, {trust_min})查询失败: {e}")


def main():
    """主函数"""
    print("🔍 KOL表数据分析")
    print("=" * 80)
    
    analyze_kol_table()
    test_different_thresholds()
    
    print("\n" + "=" * 80)
    print("🎯 分析结论:")
    print("1. 检查KOL表的总记录数")
    print("2. 分析筛选条件是否过于严格")
    print("3. 查看数据分布是否均匀")
    print("4. 确认17条记录是否为实际的有效活跃KOL数量")


if __name__ == '__main__':
    main()
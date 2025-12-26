#!/usr/bin/env python3
"""
更新现有KOL数据的标签格式脚本
为现有KOL添加语言标签并转换为多标签格式
"""
import sys
import os
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.connection import db_manager
from src.database.kol_dao import kol_dao
from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import setup_logger


def update_kol_tags():
    """更新现有KOL的标签格式"""
    
    # 设置日志
    setup_logger()
    logger = logging.getLogger(__name__)
    
    logger.info("开始更新现有KOL标签格式")
    
    try:
        # 获取所有现有KOL
        sql = "SELECT kol_id, tag, type FROM kols WHERE tag IS NOT NULL"
        existing_kols = db_manager.execute_query(sql)
        
        if not existing_kols:
            logger.info("没有找到需要更新的KOL数据")
            return
        
        logger.info(f"找到 {len(existing_kols)} 个KOL需要更新标签")
        
        updated_count = 0
        
        for kol in existing_kols:
            try:
                kol_id = kol['kol_id']
                current_tag = kol['tag'] or ""
                kol_type = kol['type'] or "influencer"
                
                print(f"\n处理KOL: {kol_id}")
                print(f"当前标签: {current_tag}")
                
                # 检查是否已经包含语言标签
                current_tags = [tag.strip() for tag in current_tag.split(',') if tag.strip()]
                has_language_tag = any(tag in ["English", "Chinese"] for tag in current_tags)
                
                if has_language_tag:
                    print(f"✅ 已包含语言标签，跳过")
                    continue
                
                # 根据用户ID推断语言（简单规则）
                # 这里可以根据实际情况调整检测逻辑
                language_tag = "English"  # 默认英文
                
                # 如果有中文相关的专业标签，可能是中文用户
                chinese_indicators = ["比特币", "以太坊", "区块链"]
                if any(indicator in current_tag for indicator in chinese_indicators):
                    language_tag = "Chinese"
                
                # 构建新的标签
                new_tags = [language_tag]
                if current_tags:
                    new_tags.extend(current_tags)
                
                # 去重并限制数量
                unique_tags = []
                for tag in new_tags:
                    if tag not in unique_tags:
                        unique_tags.append(tag)
                
                if len(unique_tags) > 5:
                    unique_tags = unique_tags[:5]
                
                new_tag_string = ",".join(unique_tags)
                
                # 更新数据库
                update_sql = "UPDATE kols SET tag = %s WHERE kol_id = %s"
                affected_rows = db_manager.execute_update(update_sql, (new_tag_string, kol_id))
                
                if affected_rows > 0:
                    print(f"✅ 更新成功: {current_tag} → {new_tag_string}")
                    updated_count += 1
                else:
                    print(f"❌ 更新失败")
                
            except Exception as e:
                logger.error(f"更新KOL {kol_id} 失败: {e}")
                continue
        
        logger.info(f"KOL标签更新完成，成功更新 {updated_count} 个KOL")
        
        # 显示更新后的结果
        show_updated_results()
        
    except Exception as e:
        logger.error(f"更新KOL标签失败: {e}")


def show_updated_results():
    """显示更新后的结果"""
    print("\n" + "="*60)
    print("=== 更新后的KOL标签格式 ===")
    
    try:
        results = db_manager.execute_query(
            "SELECT kol_id, tag, type FROM kols WHERE tag IS NOT NULL ORDER BY kol_id LIMIT 10"
        )
        
        for row in results:
            tags = row['tag'].split(',') if row['tag'] else []
            language_tags = [tag for tag in tags if tag.strip() in ["English", "Chinese"]]
            professional_tags = [tag for tag in tags if tag.strip() not in ["English", "Chinese"]]
            
            print(f"\nKOL: {row['kol_id']:15} 类型: {row['type']:10}")
            print(f"   完整标签: {row['tag']}")
            print(f"   语言标签: {language_tags}")
            print(f"   专业标签: {professional_tags}")
        
    except Exception as e:
        print(f"显示更新结果失败: {e}")


def validate_tag_format():
    """验证标签格式是否正确"""
    print("\n" + "="*60)
    print("🔍 验证标签格式")
    
    try:
        # 统计标签格式
        sql = """
        SELECT 
            tag,
            COUNT(*) as count,
            CASE 
                WHEN tag LIKE '%English%' OR tag LIKE '%Chinese%' THEN 'has_language'
                ELSE 'no_language'
            END as language_status
        FROM kols 
        WHERE tag IS NOT NULL 
        GROUP BY tag, language_status
        ORDER BY count DESC
        LIMIT 20
        """
        
        results = db_manager.execute_query(sql)
        
        total_kols = 0
        with_language = 0
        
        print("\n📊 标签格式统计:")
        for row in results:
            count = row['count']
            total_kols += count
            
            if row['language_status'] == 'has_language':
                with_language += count
                status = "✅"
            else:
                status = "❌"
            
            print(f"{status} {row['tag']:30} 数量: {count}")
        
        print(f"\n📈 统计结果:")
        print(f"总KOL数: {total_kols}")
        print(f"包含语言标签: {with_language}")
        print(f"完成率: {with_language/total_kols*100:.1f}%")
        
    except Exception as e:
        print(f"验证标签格式失败: {e}")


def main():
    """主函数"""
    print("🔧 KOL标签格式更新工具")
    
    # 显示当前状态
    validate_tag_format()
    
    # 询问是否执行更新
    print(f"\n这将为所有现有KOL添加语言标签(English/Chinese)。")
    response = input("是否继续执行更新？(y/N): ").strip().lower()
    
    if response == 'y':
        # 执行更新
        update_kol_tags()
        
        # 再次验证
        validate_tag_format()
        
        print("""
🎉 KOL标签更新完成！

=== 新的标签格式特点 ===
✅ 必须包含语言标签：English 或 Chinese
✅ 支持多个专业标签：BTC, ETH, DeFi, NFT等
✅ 逗号分隔格式：例如"English,DeFi,Bitcoin"
✅ 数量限制：最多5个标签
✅ 自动去重：避免重复标签
        """)
    else:
        print("取消更新操作")


if __name__ == '__main__':
    main() 
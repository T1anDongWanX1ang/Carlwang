#!/usr/bin/env python3
"""
修复topics表中brief字段的中文数据，统一转换为英文
"""
import sys
from pathlib import Path
import time
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.api.chatgpt_client import chatgpt_client
from src.utils.logger import get_logger


class ChineseBriefFixer:
    """中文Brief修复器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.fixed_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        
    def get_chinese_brief_records(self, limit=50):
        """获取包含中文的brief记录"""
        try:
            sql = """
            SELECT topic_id, topic_name, brief, created_at
            FROM topics 
            WHERE brief REGEXP '[\\u4e00-\\u9fff]' 
            ORDER BY created_at DESC 
            LIMIT %s
            """
            
            results = db_manager.execute_query(sql, (limit,))
            return results or []
            
        except Exception as e:
            self.logger.error(f"获取中文brief记录失败: {e}")
            return []
    
    def translate_brief_to_english(self, chinese_brief, topic_name=""):
        """将中文brief翻译为英文"""
        try:
            prompt = f"""
            Please translate the following Chinese cryptocurrency topic brief to English. 
            Keep it professional, concise (20-50 words), and maintain the original meaning.

            Topic Name: {topic_name}
            Chinese Brief: {chinese_brief}

            Requirements:
            - Professional cryptocurrency terminology
            - Concise and clear (20-50 words)
            - Maintain original meaning
            - Return only the English translation, no other text

            English Brief:
            """
            
            messages = [
                {"role": "system", "content": "You are a professional cryptocurrency market analyst and translator, skilled at translating Chinese crypto content to English accurately."},
                {"role": "user", "content": prompt}
            ]
            
            response = chatgpt_client._make_request(
                messages=messages,
                temperature=0.2,
                max_tokens=100
            )
            
            if response:
                english_brief = response.strip()
                # 简单验证：确保结果不包含中文
                if not self._contains_chinese(english_brief):
                    return english_brief
                else:
                    self.logger.warning(f"翻译结果仍包含中文: {english_brief}")
                    return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"翻译brief失败: {e}")
            return None
    
    def _contains_chinese(self, text):
        """检查文本是否包含中文字符"""
        import re
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def update_brief_in_db(self, topic_id, new_brief):
        """更新数据库中的brief字段"""
        try:
            sql = """
            UPDATE topics 
            SET brief = %s, update_time = %s 
            WHERE topic_id = %s
            """
            
            affected_rows = db_manager.execute_update(
                sql, 
                (new_brief, datetime.now(), topic_id)
            )
            
            return affected_rows > 0
            
        except Exception as e:
            self.logger.error(f"更新数据库brief失败: {e}")
            return False
    
    def fix_batch(self, batch_size=10):
        """批量修复一批中文brief记录"""
        records = self.get_chinese_brief_records(batch_size)
        
        if not records:
            self.logger.info("没有找到需要修复的中文brief记录")
            return False
        
        self.logger.info(f"开始修复 {len(records)} 条中文brief记录...")
        
        for i, record in enumerate(records, 1):
            topic_id = record['topic_id']
            topic_name = record['topic_name'] or ""
            chinese_brief = record['brief']
            created_at = record['created_at']
            
            print(f"\n{i}/{len(records)} 处理: {topic_id}")
            print(f"主题: {topic_name}")
            print(f"中文简述: {chinese_brief}")
            
            # 翻译为英文
            english_brief = self.translate_brief_to_english(chinese_brief, topic_name)
            
            if english_brief:
                # 更新数据库
                success = self.update_brief_in_db(topic_id, english_brief)
                
                if success:
                    self.fixed_count += 1
                    print(f"✅ 修复成功: {english_brief}")
                    self.logger.info(f"修复成功: {topic_id}")
                else:
                    self.failed_count += 1
                    print(f"❌ 数据库更新失败")
                    self.logger.error(f"数据库更新失败: {topic_id}")
            else:
                self.failed_count += 1
                print(f"❌ 翻译失败")
                self.logger.error(f"翻译失败: {topic_id}")
            
            # 避免API调用过于频繁
            if i < len(records):
                time.sleep(2)
        
        return len(records) == batch_size  # 如果返回的记录数等于批量大小，说明可能还有更多
    
    def fix_all(self, batch_size=10, max_batches=None):
        """修复所有中文brief记录"""
        self.logger.info("开始批量修复所有中文brief记录...")
        
        batch_count = 0
        
        while True:
            batch_count += 1
            
            if max_batches and batch_count > max_batches:
                self.logger.info(f"达到最大批次限制: {max_batches}")
                break
            
            print(f"\n{'='*60}")
            print(f"第 {batch_count} 批次处理")
            print(f"{'='*60}")
            
            has_more = self.fix_batch(batch_size)
            
            print(f"\n批次 {batch_count} 完成:")
            print(f"  - 已修复: {self.fixed_count} 条")
            print(f"  - 失败: {self.failed_count} 条")
            
            if not has_more:
                self.logger.info("所有批次处理完成")
                break
            
            # 批次间暂停
            print(f"等待 5 秒后处理下一批次...")
            time.sleep(5)
        
        print(f"\n{'='*60}")
        print(f"修复完成总结:")
        print(f"  - 总计修复成功: {self.fixed_count} 条")
        print(f"  - 总计修复失败: {self.failed_count} 条")
        print(f"  - 处理批次数: {batch_count}")
        print(f"{'='*60}")
        
        return self.fixed_count, self.failed_count
    
    def get_remaining_chinese_count(self):
        """获取剩余的中文brief记录数量"""
        try:
            sql = """
            SELECT COUNT(*) as count 
            FROM topics 
            WHERE brief REGEXP '[\\u4e00-\\u9fff]'
            """
            
            result = db_manager.execute_query(sql)
            if result:
                return result[0]['count']
            return 0
            
        except Exception as e:
            self.logger.error(f"获取剩余中文记录数失败: {e}")
            return 0


def main():
    """主函数"""
    print("Topics表Brief字段中文转英文修复工具")
    print("="*50)
    
    # 检查剩余需要修复的记录数
    fixer = ChineseBriefFixer()
    remaining_count = fixer.get_remaining_chinese_count()
    
    print(f"当前需要修复的中文brief记录数: {remaining_count}")
    
    if remaining_count == 0:
        print("没有需要修复的记录，程序退出。")
        return
    
    # 询问用户处理方式
    print("\n请选择处理方式:")
    print("1. 修复一小批 (10条)")
    print("2. 修复中等批量 (50条)")
    print("3. 修复所有记录")
    print("4. 仅查看前10条记录")
    
    choice = input("请输入选择 (1-4): ").strip()
    
    if choice == "1":
        print("\n开始修复一小批记录...")
        fixer.fix_batch(batch_size=10)
        
    elif choice == "2":
        print("\n开始修复中等批量记录...")
        fixer.fix_all(batch_size=10, max_batches=5)
        
    elif choice == "3":
        confirm = input(f"确认要修复所有 {remaining_count} 条记录吗？(y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            print("\n开始修复所有记录...")
            fixer.fix_all(batch_size=10)
        else:
            print("操作已取消。")
            
    elif choice == "4":
        print("\n查看前10条需要修复的记录:")
        records = fixer.get_chinese_brief_records(10)
        for i, record in enumerate(records, 1):
            print(f"{i}. {record['topic_id']}: {record['brief'][:100]}...")
    
    else:
        print("无效选择，程序退出。")
    
    # 显示最终状态
    final_count = fixer.get_remaining_chinese_count()
    print(f"\n剩余需要修复的记录数: {final_count}")


if __name__ == "__main__":
    main()

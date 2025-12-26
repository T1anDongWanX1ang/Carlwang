#!/usr/bin/env python3
"""
Marco数据生成脚本
基于推文数据批量生成衍生指标和AI总结
"""
import sys
import os
import logging
from datetime import datetime, timedelta
import time
import argparse
from typing import Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.marco_processor import marco_processor
from src.database.marco_dao import marco_dao
from src.database.connection import db_manager
from src.utils.logger import setup_logger


class MarcoDataGenerator:
    """Marco数据生成器"""
    
    def __init__(self):
        """初始化生成器"""
        self.logger = logging.getLogger(__name__)
        self.processor = marco_processor
        self.marco_dao = marco_dao
        
    def generate_marco_for_period(self, start_date: datetime, 
                                 end_date: datetime,
                                 force_regenerate: bool = False) -> int:
        """
        为指定时间段生成Marco数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            force_regenerate: 是否强制重新生成已存在的数据
            
        Returns:
            成功生成的数据数量
        """
        try:
            self.logger.info(f"开始生成Marco数据: {start_date} 到 {end_date}")
            
            # 生成30分钟对齐的时间戳序列
            timestamps = self.processor.generate_timestamp_sequence(start_date, end_date)
            
            self.logger.info(f"需要处理{len(timestamps)}个时间点")
            
            success_count = 0
            skip_count = 0
            error_count = 0
            
            for i, timestamp in enumerate(timestamps, 1):
                try:
                    self.logger.info(f"处理时间点 {i}/{len(timestamps)}: {timestamp}")
                    
                    # 检查是否已存在数据
                    if not force_regenerate and self.marco_dao.exists_for_timestamp(timestamp):
                        self.logger.info(f"时间点 {timestamp} 的数据已存在，跳过")
                        skip_count += 1
                        continue
                    
                    # 生成Marco数据
                    marco_data = self.processor.process_tweets_to_marco(timestamp)
                    
                    if marco_data:
                        # 保存到数据库
                        if self.marco_dao.insert(marco_data):
                            success_count += 1
                            self.logger.info(f"成功生成并保存Marco数据: {timestamp}")
                        else:
                            error_count += 1
                            self.logger.error(f"保存Marco数据失败: {timestamp}")
                    else:
                        self.logger.warning(f"生成Marco数据失败: {timestamp}")
                        error_count += 1
                    
                    # 添加延迟避免API请求过于频繁
                    time.sleep(2)  # 2秒延迟
                    
                    # 每10个时间点输出进度
                    if i % 10 == 0:
                        self.logger.info(f"进度: {i}/{len(timestamps)}, "
                                       f"成功: {success_count}, 跳过: {skip_count}, 失败: {error_count}")
                
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"处理时间点 {timestamp} 异常: {e}")
                    continue
            
            self.logger.info(f"Marco数据生成完成！总计: {len(timestamps)}, "
                           f"成功: {success_count}, 跳过: {skip_count}, 失败: {error_count}")
            
            return success_count
            
        except Exception as e:
            self.logger.error(f"生成Marco数据期间出现异常: {e}")
            return 0
    
    def generate_latest_marco(self, hours_back: int = 4) -> bool:
        """
        生成最新的Marco数据
        
        Args:
            hours_back: 往前推几小时
            
        Returns:
            是否成功
        """
        try:
            # 计算最新的30分钟对齐时间点
            now = datetime.now()
            latest_timestamp = now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)
            
            self.logger.info(f"生成最新Marco数据: {latest_timestamp}")
            
            # 生成Marco数据
            marco_data = self.processor.process_tweets_to_marco(latest_timestamp)
            
            if marco_data:
                # 保存到数据库
                if self.marco_dao.insert(marco_data):
                    self.logger.info(f"成功生成最新Marco数据: sentiment={marco_data.sentiment_index:.2f}")
                    return True
                else:
                    self.logger.error("保存最新Marco数据失败")
                    return False
            else:
                self.logger.warning("生成最新Marco数据失败")
                return False
                
        except Exception as e:
            self.logger.error(f"生成最新Marco数据异常: {e}")
            return False
    
    def backfill_marco_data(self, days_back: int = 7) -> int:
        """
        回填Marco数据
        
        Args:
            days_back: 往前回填几天的数据
            
        Returns:
            成功生成的数据数量
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            self.logger.info(f"开始回填Marco数据: 最近{days_back}天")
            
            return self.generate_marco_for_period(start_date, end_date)
            
        except Exception as e:
            self.logger.error(f"回填Marco数据异常: {e}")
            return 0
    
    def test_connection(self) -> bool:
        """
        测试数据库连接
        
        Returns:
            连接是否正常
        """
        try:
            if db_manager.test_connection():
                self.logger.info("数据库连接测试成功")
                return True
            else:
                self.logger.error("数据库连接测试失败")
                return False
        except Exception as e:
            self.logger.error(f"数据库连接测试异常: {e}")
            return False
    
    def show_statistics(self):
        """显示统计信息"""
        try:
            stats = self.marco_dao.get_statistics()
            
            print("\n=== Marco数据统计信息 ===")
            print(f"总记录数: {stats.get('total_records', 0)}")
            print(f"平均情感指数: {stats.get('average_sentiment', 0)}")
            print(f"最早时间: {stats.get('earliest_timestamp', 'N/A')}")
            print(f"最新时间: {stats.get('latest_timestamp', 'N/A')}")
            
            # 显示最新几条记录
            latest_records = self.marco_dao.get_latest(5)
            if latest_records:
                print("\n=== 最新Marco数据 ===")
                for record in latest_records:
                    print(f"时间: {record.timestamp}, 情感指数: {record.sentiment_index:.2f}")
                    if record.summary:
                        print(f"总结: {record.summary[:100]}...")
                    print("-" * 50)
            
        except Exception as e:
            self.logger.error(f"显示统计信息异常: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Marco数据生成脚本')
    
    parser.add_argument('--mode', choices=['latest', 'backfill', 'period', 'stats', 'test'], 
                       default='latest', help='运行模式')
    parser.add_argument('--days', type=int, default=7, help='回填天数')
    parser.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD HH:MM)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD HH:MM)')
    parser.add_argument('--force', action='store_true', help='强制重新生成')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logger()
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    logger = logging.getLogger(__name__)
    
    # 创建生成器
    generator = MarcoDataGenerator()
    
    try:
        if args.mode == 'test':
            # 测试连接
            success = generator.test_connection()
            sys.exit(0 if success else 1)
            
        elif args.mode == 'stats':
            # 显示统计信息
            generator.show_statistics()
            
        elif args.mode == 'latest':
            # 生成最新数据
            logger.info("开始生成最新Marco数据")
            success = generator.generate_latest_marco()
            if success:
                logger.info("最新Marco数据生成成功")
            else:
                logger.error("最新Marco数据生成失败")
                sys.exit(1)
                
        elif args.mode == 'backfill':
            # 回填数据
            logger.info(f"开始回填最近{args.days}天的Marco数据")
            count = generator.backfill_marco_data(args.days)
            logger.info(f"回填完成，成功生成{count}条数据")
            
        elif args.mode == 'period':
            # 指定时间段生成
            if not args.start or not args.end:
                logger.error("period模式需要指定--start和--end参数")
                sys.exit(1)
            
            try:
                start_date = datetime.strptime(args.start, '%Y-%m-%d %H:%M')
                end_date = datetime.strptime(args.end, '%Y-%m-%d %H:%M')
            except ValueError:
                logger.error("日期格式错误，请使用: YYYY-MM-DD HH:MM")
                sys.exit(1)
            
            logger.info(f"开始生成指定时间段的Marco数据")
            count = generator.generate_marco_for_period(start_date, end_date, args.force)
            logger.info(f"时间段数据生成完成，成功生成{count}条数据")
        
        # 显示最终统计
        generator.show_statistics()
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行异常: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 
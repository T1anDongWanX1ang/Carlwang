"""
定时任务调度器
"""
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any
import signal
import sys

from .config_manager import config


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.scheduler_config = config.get_scheduler_config()
        self.interval_minutes = self.scheduler_config.get('interval_minutes', 5)
        self.max_workers = self.scheduler_config.get('max_workers', 1)
        self.enable_logging = self.scheduler_config.get('enable_logging', True)
        
        self.logger = logging.getLogger(__name__)
        
        # 调度器状态
        self.is_running = False
        self.is_stopped = False
        self.scheduler_thread = None
        self.task_function = None
        
        # 任务统计
        self.task_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_run_time = None
        self.next_run_time = None
        
        # 设置信号处理器用于优雅关闭
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def set_task(self, task_function: Callable[[], bool]) -> None:
        """
        设置要执行的任务函数
        
        Args:
            task_function: 任务函数，应返回bool表示是否成功
        """
        self.task_function = task_function
        self.logger.info(f"任务函数已设置: {task_function.__name__}")
    
    def start(self) -> None:
        """启动调度器"""
        if self.is_running:
            self.logger.warning("调度器已经在运行中")
            return
        
        if not self.task_function:
            raise ValueError("必须先设置任务函数才能启动调度器")
        
        self.is_running = True
        self.is_stopped = False
        
        # 计算下次运行时间
        self.next_run_time = datetime.now() + timedelta(minutes=self.interval_minutes)
        
        # 启动调度器线程
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info(f"调度器已启动，间隔 {self.interval_minutes} 分钟")
        self.logger.info(f"下次运行时间: {self.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def stop(self) -> None:
        """停止调度器"""
        if not self.is_running:
            self.logger.warning("调度器未在运行")
            return
        
        self.logger.info("正在停止调度器...")
        self.is_running = False
        
        # 等待调度器线程结束
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
        
        self.is_stopped = True
        self.logger.info("调度器已停止")
    
    def run_once(self) -> bool:
        """
        立即执行一次任务
        
        Returns:
            任务是否成功执行
        """
        if not self.task_function:
            self.logger.error("任务函数未设置")
            return False
        
        return self._execute_task()
    
    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 检查是否到了执行时间
                if current_time >= self.next_run_time:
                    self._execute_task()
                    
                    # 计算下次运行时间
                    self.next_run_time = current_time + timedelta(minutes=self.interval_minutes)
                    
                    if self.enable_logging:
                        self.logger.info(f"下次运行时间: {self.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 等待一段时间后再检查
                time.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                self.logger.error(f"调度器循环出现异常: {e}")
                time.sleep(60)  # 出错后等待1分钟
    
    def _execute_task(self) -> bool:
        """
        执行任务
        
        Returns:
            任务是否成功执行
        """
        if not self.task_function:
            return False
        
        self.task_count += 1
        self.last_run_time = datetime.now()
        
        if self.enable_logging:
            self.logger.info(f"开始执行任务 #{self.task_count}")
            start_time = time.time()
        
        try:
            # 执行任务
            success = self.task_function()
            
            if success:
                self.success_count += 1
                if self.enable_logging:
                    elapsed_time = time.time() - start_time
                    self.logger.info(f"任务 #{self.task_count} 执行成功，耗时 {elapsed_time:.2f} 秒")
            else:
                self.error_count += 1
                self.logger.error(f"任务 #{self.task_count} 执行失败")
            
            return success
            
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"任务 #{self.task_count} 执行异常: {e}")
            return False
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"接收到信号 {signum}，正在关闭调度器...")
        self.stop()
        sys.exit(0)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取调度器状态
        
        Returns:
            状态信息字典
        """
        return {
            'is_running': self.is_running,
            'is_stopped': self.is_stopped,
            'interval_minutes': self.interval_minutes,
            'task_count': self.task_count,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': (self.success_count / max(self.task_count, 1)) * 100,
            'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
            'next_run_time': self.next_run_time.isoformat() if self.next_run_time else None,
            'time_to_next_run': str(self.next_run_time - datetime.now()) if self.next_run_time else None
        }
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.task_count = 0
        self.success_count = 0
        self.error_count = 0
        self.last_run_time = None
        self.logger.info("调度器统计信息已重置")
    
    def update_interval(self, minutes: int) -> None:
        """
        更新执行间隔
        
        Args:
            minutes: 新的间隔分钟数
        """
        if minutes <= 0:
            raise ValueError("间隔时间必须大于0分钟")
        
        self.interval_minutes = minutes
        
        # 如果正在运行，重新计算下次运行时间
        if self.is_running:
            self.next_run_time = datetime.now() + timedelta(minutes=minutes)
        
        self.logger.info(f"执行间隔已更新为 {minutes} 分钟")
        
        # 更新配置
        config.update_config('scheduler.interval_minutes', minutes)


class CrawlerScheduler(TaskScheduler):
    """爬虫专用调度器"""
    
    def __init__(self):
        """初始化爬虫调度器"""
        super().__init__()
        self.crawler_function = None
    
    def set_crawler(self, crawler_function: Callable[[], bool]) -> None:
        """
        设置爬虫函数
        
        Args:
            crawler_function: 爬虫函数
        """
        self.crawler_function = crawler_function
        self.set_task(crawler_function)
        self.logger.info("爬虫函数已设置")
    
    def start_crawling(self) -> None:
        """开始定时爬取"""
        if not self.crawler_function:
            raise ValueError("必须先设置爬虫函数")
        
        self.logger.info("开始定时爬取Twitter数据...")
        self.start()
    
    def run_crawler_once(self) -> bool:
        """立即执行一次爬取"""
        self.logger.info("立即执行一次数据爬取...")
        return self.run_once()


# 全局调度器实例
scheduler = CrawlerScheduler() 
"""
日志配置模块
"""
import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

from .config_manager import config


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称，如果不指定则使用根记录器

    Returns:
        配置好的日志记录器
    """
    # 获取日志配置
    log_config = config.get_logging_config()

    # 创建或获取记录器
    logger = logging.getLogger(name)

    # 🎯 关键修复：避免重复配置（检查handlers数量）
    if logger.handlers:
        # 如果已经有handlers，直接返回，不再添加
        return logger

    # 设置日志级别
    log_level = getattr(logging, log_config.get('level', 'INFO').upper())
    logger.setLevel(log_level)

    # 🎯 防止日志传播到父logger（避免重复打印）
    logger.propagate = False

    # 创建格式化器
    formatter = logging.Formatter(
        log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    log_file = log_config.get('file')
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 解析文件大小
        max_bytes = _parse_file_size(log_config.get('max_file_size', '10MB'))
        backup_count = log_config.get('backup_count', 5)

        # 创建轮转文件处理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 如果这是根logger的初始化，设置第三方库的日志级别
    if name is None:
        # 抑制OpenAI的详细debug日志
        openai_logger = logging.getLogger('openai')
        openai_logger.setLevel(logging.WARNING)

        # 抑制Google Gemini的详细日志
        google_genai_logger = logging.getLogger('google_genai')
        google_genai_logger.setLevel(logging.WARNING)
        logging.getLogger('google_genai.models').setLevel(logging.WARNING)
        logging.getLogger('google.genai').setLevel(logging.WARNING)

        # 抑制urllib3的详细debug日志
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.WARNING)

        # 抑制其他可能的verbose日志
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
        logging.getLogger('urllib3.util.retry').setLevel(logging.WARNING)

        # 抑制httpcore和httpx的详细HTTP请求日志
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('httpcore.http11').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)

    return logger


def _parse_file_size(size_str: str) -> int:
    """
    解析文件大小字符串
    
    Args:
        size_str: 大小字符串，如 "10MB", "1GB"
        
    Returns:
        字节数
    """
    size_str = size_str.upper().strip()
    
    if size_str.endswith('KB'):
        return int(size_str[:-2]) * 1024
    elif size_str.endswith('MB'):
        return int(size_str[:-2]) * 1024 * 1024
    elif size_str.endswith('GB'):
        return int(size_str[:-2]) * 1024 * 1024 * 1024
    else:
        # 假设是字节数
        return int(size_str)


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    Args:
        name: 记录器名称
        
    Returns:
        日志记录器
    """
    return setup_logger(name)


# 设置根日志记录器
setup_logger() 
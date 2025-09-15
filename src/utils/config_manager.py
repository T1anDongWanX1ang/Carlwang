"""
配置管理模块
用于加载和管理应用程序配置
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果不指定则使用默认路径
        """
        if config_file is None:
            # 获取项目根目录
            current_dir = Path(__file__).parent.parent.parent
            config_file = current_dir / "config" / "config.json"
        
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            print(f"配置文件加载成功: {self.config_file}")
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点分隔的嵌套键
        
        Args:
            key: 配置键，支持 "api.base_url" 格式
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self.get('api', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.get('database', {})
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度器配置"""
        return self.get('scheduler', {})
    
    def get_field_mapping(self) -> Dict[str, str]:
        """获取字段映射配置"""
        return self.get('field_mapping', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get('logging', {})
    
    def update_config(self, key: str, value: Any) -> None:
        """
        更新配置值
        
        Args:
            key: 配置键，支持点分隔的嵌套键
            value: 新值
        """
        keys = key.split('.')
        config_ref = self.config
        
        # 导航到最后一级的父对象
        for k in keys[:-1]:
            if k not in config_ref:
                config_ref[k] = {}
            config_ref = config_ref[k]
        
        # 设置值
        config_ref[keys[-1]] = value
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"配置文件保存成功: {self.config_file}")
        except Exception as e:
            raise Exception(f"保存配置文件失败: {e}")
    
    def reload_config(self) -> None:
        """重新加载配置文件"""
        self.load_config()


# 全局配置实例
config = ConfigManager() 
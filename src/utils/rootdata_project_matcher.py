"""
RootData项目匹配器
用于从推文中提取的项目名称与RootData数据库中的项目进行匹配
"""
import logging
from typing import List, Optional, Set
from ..database.connection import db_manager


class RootDataProjectMatcher:
    """RootData项目匹配器"""

    def __init__(self):
        """初始化项目匹配器"""
        self.logger = logging.getLogger(__name__)
        self.db_manager = db_manager

        # 缓存RootData的项目名称列表
        self._project_name_cache: Set[str] = set()
        self._project_name_lower_map: dict = {}  # 小写名称 -> 原始名称的映射
        self._load_projects_from_db()

    def _load_projects_from_db(self):
        """从RootData数据库加载所有的项目名称"""
        try:
            sql = "SELECT DISTINCT name FROM public_data.rootdata_projects WHERE name IS NOT NULL AND name != ''"
            results = self.db_manager.execute_query(sql)

            if results:
                for row in results:
                    name = row.get('name', '').strip()
                    if name:
                        self._project_name_cache.add(name)
                        # 建立小写映射，用于不区分大小写的匹配
                        name_lower = name.lower()
                        # 如果有多个项目名称只有大小写不同，保留第一个
                        if name_lower not in self._project_name_lower_map:
                            self._project_name_lower_map[name_lower] = name

                self.logger.info(f"成功从RootData加载 {len(self._project_name_cache)} 个项目名称")
            else:
                self.logger.warning("未能从RootData加载项目名称")

        except Exception as e:
            self.logger.error(f"加载RootData项目名称失败: {e}")

    def reload_projects(self):
        """重新加载项目名称缓存"""
        self._project_name_cache.clear()
        self._project_name_lower_map.clear()
        self._load_projects_from_db()

    def match_project_name(self, ai_project_name: str) -> Optional[str]:
        """
        将AI提取的项目名称与RootData中的项目进行匹配

        Args:
            ai_project_name: AI提取的项目名称

        Returns:
            匹配到的RootData项目名称，如果没有匹配则返回None
        """
        if not ai_project_name:
            return None

        try:
            ai_name_stripped = ai_project_name.strip()

            # 1. 精确匹配（区分大小写）
            if ai_name_stripped in self._project_name_cache:
                self.logger.debug(f"精确匹配: {ai_name_stripped}")
                return ai_name_stripped

            # 2. 不区分大小写匹配
            ai_name_lower = ai_name_stripped.lower()
            if ai_name_lower in self._project_name_lower_map:
                matched_name = self._project_name_lower_map[ai_name_lower]
                self.logger.debug(f"不区分大小写匹配: {ai_name_stripped} -> {matched_name}")
                return matched_name

            # 3. 模糊匹配（处理常见的变体）
            # 例如：Bitcoin -> BTC, Ethereum -> ETH等
            fuzzy_match = self._fuzzy_match(ai_name_stripped)
            if fuzzy_match:
                self.logger.debug(f"模糊匹配: {ai_name_stripped} -> {fuzzy_match}")
                return fuzzy_match

            # 4. 未匹配到
            self.logger.debug(f"未匹配到RootData项目: {ai_name_stripped}")
            return None

        except Exception as e:
            self.logger.error(f"匹配项目名称失败: {e}")
            return None

    def _fuzzy_match(self, ai_name: str) -> Optional[str]:
        """
        模糊匹配，处理常见变体

        Args:
            ai_name: AI提取的名称

        Returns:
            匹配的项目名称或None
        """
        # 常见的项目名称别名映射
        alias_map = {
            'btc': 'bitcoin',
            'eth': 'ethereum',
            'sol': 'solana',
            'ada': 'cardano',
            'matic': 'polygon',
            'link': 'chainlink',
            'uni': 'uniswap',
            'avax': 'avalanche',
            'dot': 'polkadot',
            'bnb': 'binance coin',
        }

        ai_name_lower = ai_name.lower()

        # 检查是否是别名
        if ai_name_lower in alias_map:
            full_name = alias_map[ai_name_lower]
            # 在缓存中查找完整名称
            if full_name in self._project_name_lower_map:
                return self._project_name_lower_map[full_name]

        # 检查是否包含关系（宽松匹配）
        # 例如：AI识别为 "Bitcoin Network" 可以匹配到 "Bitcoin"
        for cached_name_lower, original_name in self._project_name_lower_map.items():
            # 如果AI名称包含缓存名称，或缓存名称包含AI名称
            if (cached_name_lower in ai_name_lower or
                ai_name_lower in cached_name_lower) and len(ai_name_lower) >= 3:
                self.logger.debug(f"包含匹配: {ai_name} ≈ {original_name}")
                return original_name

        return None

    def is_valid_project(self, project_name: str) -> bool:
        """
        检查项目名称是否在RootData中存在

        Args:
            project_name: 项目名称

        Returns:
            是否存在
        """
        if not project_name:
            return False

        return project_name.strip().lower() in self._project_name_lower_map

    def get_cached_projects(self) -> List[str]:
        """获取缓存的所有项目名称列表"""
        return sorted(list(self._project_name_cache))

    def get_cache_size(self) -> int:
        """获取缓存的项目数量"""
        return len(self._project_name_cache)


# 全局项目匹配器实例
rootdata_project_matcher = RootDataProjectMatcher()

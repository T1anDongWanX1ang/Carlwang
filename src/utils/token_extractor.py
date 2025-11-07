"""
Token Symbol提取器
用于从推文中提取加密货币token symbol，并与coinmarketcap数据库匹配
"""
import logging
from typing import List, Optional, Dict, Any, Set
from ..database.connection import db_manager


class TokenExtractor:
    """Token Symbol提取器"""

    def __init__(self):
        """初始化Token提取器"""
        self.logger = logging.getLogger(__name__)
        self.db_manager = db_manager

        # 缓存coinmarketcap的symbol列表
        self._symbol_cache: Set[str] = set()
        self._symbol_map: Dict[str, str] = {}  # symbol -> 规范化的symbol
        self._load_symbols_from_db()

    def _load_symbols_from_db(self):
        """从数据库加载所有的token symbol"""
        try:
            sql = "SELECT DISTINCT symbol FROM public_data.coinmarketcap_cryptocurrency_listing"
            results = self.db_manager.execute_query(sql)

            if results:
                for row in results:
                    symbol = row.get('symbol', '').strip().upper()
                    if symbol:
                        self._symbol_cache.add(symbol)
                        self._symbol_map[symbol] = symbol

                self.logger.info(f"成功从数据库加载 {len(self._symbol_cache)} 个token symbol")
            else:
                self.logger.warning("未能从数据库加载token symbol")

        except Exception as e:
            self.logger.error(f"加载token symbol失败: {e}")

    def reload_symbols(self):
        """重新加载symbol缓存"""
        self._symbol_cache.clear()
        self._symbol_map.clear()
        self._load_symbols_from_db()

    def validate_symbols(self, symbols: List[str]) -> List[str]:
        """
        验证symbol列表，只保留在coinmarketcap表中存在的symbol

        Args:
            symbols: symbol列表

        Returns:
            验证后的symbol列表
        """
        validated_symbols = []

        for symbol in symbols:
            symbol_upper = symbol.strip().upper()
            if symbol_upper in self._symbol_cache:
                validated_symbols.append(symbol_upper)
            else:
                self.logger.debug(f"Symbol {symbol} 不在coinmarketcap表中，已过滤")

        return validated_symbols

    def extract_symbols_from_text(self, text: str, ai_extracted_symbols: List[str] = None) -> Optional[str]:
        """
        从文本中提取token symbols，结合AI提取的结果和数据库验证

        Args:
            text: 推文文本
            ai_extracted_symbols: AI提取的symbol列表

        Returns:
            验证后的symbol字符串（逗号分隔），如果没有则返回None
        """
        try:
            validated_symbols = []

            # 1. 如果有AI提取的结果，优先验证AI提取的symbols
            if ai_extracted_symbols:
                validated_symbols = self.validate_symbols(ai_extracted_symbols)

            # 2. 如果没有AI结果或AI结果为空，尝试简单的文本匹配（作为备用）
            if not validated_symbols and text:
                # 简单的规则提取：查找大写的代币符号（2-10个字符）
                import re
                # 匹配$符号后面的大写字母，或者单独的大写字母组合
                pattern = r'\$([A-Z]{2,10})\b|\b([A-Z]{2,10})\b'
                matches = re.findall(pattern, text.upper())

                potential_symbols = []
                for match in matches:
                    # match是一个元组，取非空的部分
                    symbol = match[0] if match[0] else match[1]
                    if symbol:
                        potential_symbols.append(symbol)

                # 去重
                potential_symbols = list(set(potential_symbols))

                # 验证是否在数据库中
                validated_symbols = self.validate_symbols(potential_symbols)

            # 3. 返回结果
            if validated_symbols:
                # 去重并排序
                unique_symbols = sorted(list(set(validated_symbols)))
                result = ','.join(unique_symbols)
                self.logger.debug(f"提取到的token symbols: {result}")
                return result
            else:
                return None

        except Exception as e:
            self.logger.error(f"从文本提取token symbol失败: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取symbol的详细信息

        Args:
            symbol: token symbol

        Returns:
            symbol的详细信息字典
        """
        try:
            symbol_upper = symbol.strip().upper()
            sql = """
            SELECT symbol, name, slug, cmc_rank, price, market_cap
            FROM public_data.coinmarketcap_cryptocurrency_listing
            WHERE symbol = %s
            LIMIT 1
            """
            results = self.db_manager.execute_query(sql, (symbol_upper,))

            if results:
                return results[0]
            return None

        except Exception as e:
            self.logger.error(f"查询symbol信息失败: {e}")
            return None

    def get_cached_symbols(self) -> List[str]:
        """获取缓存的所有symbol列表"""
        return sorted(list(self._symbol_cache))

    def is_valid_symbol(self, symbol: str) -> bool:
        """
        检查symbol是否有效（存在于数据库中）

        Args:
            symbol: token symbol

        Returns:
            是否有效
        """
        return symbol.strip().upper() in self._symbol_cache


# 全局token提取器实例
token_extractor = TokenExtractor()

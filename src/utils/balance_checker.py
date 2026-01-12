"""
TwitterAPI.io 余额查询工具
用于查询当前账户余额
"""
import requests
from typing import Dict, Any, Optional
from ..utils.config_manager import config
from ..utils.logger import get_logger


class BalanceChecker:
    """TwitterAPI.io 余额查询器"""

    def __init__(self):
        """初始化余额查询器"""
        self.logger = get_logger(__name__)

        # 读取API配置
        self.api_config = config.get('api_twitterapi', config.get_api_config())
        self.headers = self.api_config.get('headers', {})

        # 余额查询接口
        self.balance_url = "https://api.twitterapi.io/oapi/my/info"

        # Credits 与 USD 的转换率
        self.credits_per_usd = 100000  # 1 USD = 100,000 Credits

    def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        查询账户余额

        Returns:
            余额信息字典，包含：
            - credits: 剩余 credits
            - usd: 剩余美元（换算后）
            - raw_data: 原始API返回数据

            如果查询失败返回 None
        """
        try:
            self.logger.info("正在查询 TwitterAPI.io 账户余额...")

            response = requests.get(
                self.balance_url,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # 提取余额 credits
                recharge_credits = data.get('recharge_credits', 0)

                # 转换为 USD
                balance_usd = recharge_credits / self.credits_per_usd

                result = {
                    'credits': recharge_credits,
                    'usd': balance_usd,
                    'raw_data': data
                }

                self.logger.info(f"✅ 余额查询成功: {recharge_credits:,} credits (${balance_usd:.2f} USD)")
                return result

            else:
                self.logger.error(f"余额查询失败，状态码: {response.status_code}")
                self.logger.error(f"响应内容: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"查询余额时发生异常: {e}")
            return None

    def format_balance(self, balance_info: Dict[str, Any]) -> str:
        """
        格式化余额信息为可读字符串

        Args:
            balance_info: get_balance() 返回的余额信息

        Returns:
            格式化的字符串
        """
        if not balance_info:
            return "余额查询失败"

        credits = balance_info['credits']
        usd = balance_info['usd']

        return f"{credits:,} credits (${usd:.2f} USD)"


# 创建全局实例
balance_checker = BalanceChecker()

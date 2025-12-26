#!/usr/bin/env python3
"""
获取 KOL 关注列表并入库
从 twitter_kol 表读取所有 KOL，查询其关注列表，存入 twitter_kol_all 表

带缓存和断点续传功能，防止API重复调用浪费费用

使用方法：
    # 测试模式（只处理前3个KOL，不调用API，不入库）
    python fetch_kol_followings.py --test

    # 模拟模式（调用真实API但不入库，测试API连接）
    python fetch_kol_followings.py --dry-run --limit 1

    # 正式运行（处理所有KOL，自动使用缓存）
    python fetch_kol_followings.py

    # 正式运行（指定处理数量）
    python fetch_kol_followings.py --limit 10

    # 从缓存恢复（只入库已缓存的数据，不调用API）
    python fetch_kol_followings.py --resume

    # 清理所有缓存和进度
    python fetch_kol_followings.py --clear-cache

    # 查看缓存状态
    python fetch_kol_followings.py --cache-status
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import time
import requests
import json
import os
from dateutil import parser

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import db_manager
from src.utils.logger import get_logger


class KOLFollowingsFetcher:
    """KOL关注列表获取器（带缓存和断点续传）"""

    def __init__(self, api_key: str, cache_dir: str = ".kol_cache"):
        """
        初始化获取器

        Args:
            api_key: Twitter API密钥
            cache_dir: 缓存目录路径
        """
        self.logger = get_logger(__name__)
        self.db_manager = db_manager
        self.api_key = api_key
        self.api_base_url = "https://api.twitterapi.io/twitter/user/followings"

        # 缓存配置
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.progress_file = self.cache_dir / "progress.json"

        # 统计信息
        self.total_kols = 0
        self.processed_kols = 0
        self.success_kols = 0
        self.failed_kols = 0
        self.total_followings = 0
        self.inserted_followings = 0
        self.skipped_followings = 0
        self.api_calls = 0
        self.cache_hits = 0

    def fetch_all_kol_followings(self,
                                  limit: Optional[int] = None,
                                  skip: int = 0,
                                  test_mode: bool = False,
                                  dry_run: bool = False,
                                  resume_mode: bool = False,
                                  sleep_interval: float = 0.5) -> bool:
        """
        获取所有KOL的关注列表（带缓存和断点续传）

        Args:
            limit: 限制处理的KOL数量（None表示处理全部）
            skip: 跳过前N个KOL
            test_mode: 测试模式（不调用API，不入库）
            dry_run: 模拟运行（调用API但不入库）
            resume_mode: 恢复模式（只处理已缓存的数据，不调用API）
            sleep_interval: API调用间隔秒数（默认0.5秒）

        Returns:
            是否成功
        """
        try:
            self.logger.info("=" * 60)
            self.logger.info("开始获取KOL关注列表")
            if test_mode:
                self.logger.info("【测试模式 - 不调用API，不入库】")
            elif dry_run:
                self.logger.info("【模拟运行 - 调用API但不入库】")
            elif resume_mode:
                self.logger.info("【恢复模式 - 从缓存恢复，不调用API】")
            else:
                self.logger.info("【正常模式 - 自动使用缓存，避免重复API调用】")
            self.logger.info("=" * 60)

            # 1. 加载进度信息
            completed_kols = self._load_progress()
            self.logger.info(f"已完成入库的KOL数: {len(completed_kols)}")

            # 2. 获取所有KOL
            kols = self._get_all_kols()
            self.total_kols = len(kols)

            self.logger.info(f"从 twitter_kol 表获取到 {self.total_kols} 个KOL")

            if not kols:
                self.logger.warning("没有找到KOL数据")
                return False

            # 3. 过滤已完成的KOL
            if not resume_mode:
                kols = [k for k in kols if k.get('user_name') not in completed_kols]
                self.logger.info(f"过滤已完成的KOL后剩余: {len(kols)} 个")

            # 4. 应用跳过和限制
            if skip > 0:
                kols = kols[skip:]
                self.logger.info(f"跳过前 {skip} 个KOL，剩余 {len(kols)} 个")

            if limit:
                kols = kols[:limit]
                self.logger.info(f"限制处理 {limit} 个KOL")

            # 5. 测试模式特殊处理
            if test_mode:
                kols = kols[:3]
                self.logger.info(f"测试模式：只处理前 {len(kols)} 个KOL")

            # 6. 逐个处理KOL
            for idx, kol in enumerate(kols, 1):
                user_name = kol.get('user_name')
                self.logger.info(f"\n[{idx}/{len(kols)}] 处理KOL: {user_name}")

                try:
                    if test_mode:
                        # 测试模式：不调用API
                        self.logger.info(f"  [测试] 将调用API获取关注列表")
                        self.processed_kols += 1
                        self.success_kols += 1
                    else:
                        # 获取关注列表（优先使用缓存）
                        followings = self._get_followings_with_cache(
                            user_name,
                            use_api=not resume_mode
                        )

                        if followings:
                            self.logger.info(f"  获取到 {len(followings)} 个关注用户")
                            self.total_followings += len(followings)

                            if not dry_run:
                                # 入库（传递当前KOL的user_name作为follower_id）
                                inserted = self._save_followings(followings, follower_id=user_name)
                                self.inserted_followings += inserted
                                self.skipped_followings += (len(followings) - inserted)
                                self.logger.info(f"  入库: {inserted} 条新增, {len(followings) - inserted} 条已存在")

                                # 入库成功后，记录进度并清理缓存
                                self._mark_completed(user_name)
                                self._clear_cache_for_kol(user_name)
                            else:
                                self.logger.info(f"  [模拟] 将入库 {len(followings)} 条数据")

                            self.success_kols += 1
                        else:
                            self.logger.warning(f"  未获取到关注列表")
                            self.failed_kols += 1

                        self.processed_kols += 1

                        # API限流保护（避免请求过快）
                        if not resume_mode and idx < len(kols) and sleep_interval > 0:
                            time.sleep(sleep_interval)

                except Exception as e:
                    self.logger.error(f"  处理KOL失败: {e}")
                    import traceback
                    self.logger.error(f"  详细错误: {traceback.format_exc()}")
                    self.failed_kols += 1
                    continue

            # 7. 显示统计
            self._show_statistics(test_mode, dry_run, resume_mode)

            return True

        except Exception as e:
            self.logger.error(f"获取KOL关注列表失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _get_all_kols(self) -> List[Dict[str, Any]]:
        """
        从数据库获取所有KOL

        Returns:
            KOL列表
        """
        try:
            sql = """
            SELECT id, user_name, name, followers
            FROM public_data.twitter_kol
            WHERE user_name IS NOT NULL AND user_name != ''
            ORDER BY followers DESC
            """

            results = self.db_manager.execute_query(sql)
            return results or []

        except Exception as e:
            self.logger.error(f"查询KOL数据失败: {e}")
            return []

    def _get_cache_file(self, user_name: str) -> Path:
        """获取缓存文件路径"""
        # 使用安全的文件名
        safe_name = user_name.replace('/', '_').replace('\\', '_')
        return self.cache_dir / f"{safe_name}.json"

    def _load_progress(self) -> Set[str]:
        """
        加载已完成的KOL进度

        Returns:
            已完成的KOL用户名集合
        """
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('completed', []))
            return set()
        except Exception as e:
            self.logger.warning(f"加载进度文件失败: {e}")
            return set()

    def _mark_completed(self, user_name: str):
        """
        标记KOL为已完成

        Args:
            user_name: KOL用户名
        """
        try:
            completed = self._load_progress()
            completed.add(user_name)

            data = {
                'completed': list(completed),
                'last_update': datetime.now().isoformat()
            }

            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"  标记为已完成: {user_name}")

        except Exception as e:
            self.logger.warning(f"保存进度失败: {e}")

    def _get_followings_with_cache(self, user_name: str, use_api: bool = True) -> List[Dict[str, Any]]:
        """
        获取关注列表（优先使用缓存）

        Args:
            user_name: 用户名
            use_api: 是否允许调用API

        Returns:
            关注用户列表
        """
        cache_file = self._get_cache_file(user_name)

        # 1. 尝试从缓存读取
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    followings = cache_data.get('followings', [])
                    if followings:
                        self.cache_hits += 1
                        self.logger.info(f"  [缓存命中] 从缓存读取 {len(followings)} 条数据")
                        return followings
            except Exception as e:
                self.logger.warning(f"  读取缓存失败: {e}")

        # 2. 缓存不存在或读取失败，调用API
        if use_api:
            followings = self._fetch_followings(user_name)

            # 3. API调用成功，保存到缓存
            if followings:
                self._save_to_cache(user_name, followings)
                self.api_calls += 1

            return followings
        else:
            self.logger.warning(f"  缓存不存在且不允许调用API")
            return []

    def _save_to_cache(self, user_name: str, followings: List[Dict[str, Any]]):
        """
        保存数据到缓存

        Args:
            user_name: 用户名
            followings: 关注用户列表
        """
        try:
            cache_file = self._get_cache_file(user_name)
            cache_data = {
                'user_name': user_name,
                'followings': followings,
                'fetch_time': datetime.now().isoformat(),
                'count': len(followings)
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            self.logger.debug(f"  已保存到缓存: {cache_file.name}")

        except Exception as e:
            self.logger.warning(f"  保存缓存失败: {e}")

    def _clear_cache_for_kol(self, user_name: str):
        """
        清理指定KOL的缓存

        Args:
            user_name: 用户名
        """
        try:
            cache_file = self._get_cache_file(user_name)
            if cache_file.exists():
                cache_file.unlink()
                self.logger.debug(f"  已清理缓存: {cache_file.name}")
        except Exception as e:
            self.logger.warning(f"  清理缓存失败: {e}")

    def clear_all_cache(self):
        """清理所有缓存"""
        try:
            self.logger.info("开始清理所有缓存...")

            # 清理缓存文件
            cache_files = list(self.cache_dir.glob("*.json"))
            cache_files = [f for f in cache_files if f.name != "progress.json"]

            for cache_file in cache_files:
                cache_file.unlink()

            # 清理进度文件
            if self.progress_file.exists():
                self.progress_file.unlink()

            self.logger.info(f"✓ 已清理 {len(cache_files)} 个缓存文件和进度文件")

        except Exception as e:
            self.logger.error(f"清理缓存失败: {e}")

    def show_cache_status(self):
        """显示缓存状态"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("缓存状态信息")
            self.logger.info("=" * 60)

            # 统计缓存文件
            cache_files = list(self.cache_dir.glob("*.json"))
            cache_files = [f for f in cache_files if f.name != "progress.json"]

            self.logger.info(f"缓存目录: {self.cache_dir.absolute()}")
            self.logger.info(f"缓存文件数: {len(cache_files)}")

            # 统计缓存大小
            total_size = sum(f.stat().st_size for f in cache_files)
            self.logger.info(f"缓存总大小: {total_size / 1024:.2f} KB")

            # 加载进度
            completed = self._load_progress()
            self.logger.info(f"已完成入库: {len(completed)} 个KOL")

            # 显示缓存列表（最多显示10个）
            if cache_files:
                self.logger.info(f"\n缓存文件列表（前10个）:")
                for cache_file in cache_files[:10]:
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            user_name = data.get('user_name', 'unknown')
                            count = data.get('count', 0)
                            fetch_time = data.get('fetch_time', 'unknown')
                            self.logger.info(f"  - {user_name}: {count} 条数据, 获取时间: {fetch_time}")
                    except:
                        continue

            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"查看缓存状态失败: {e}")

    def _fetch_followings(self, user_name: str, page_size: int = 200) -> List[Dict[str, Any]]:
        """
        调用第三方API获取关注列表（支持分页获取所有数据）

        Args:
            user_name: 用户名
            page_size: 每页数量（最大200）

        Returns:
            关注用户列表（所有分页数据）
        """
        all_followings = []
        cursor = ""
        page_num = 1

        try:
            while True:
                url = self.api_base_url
                params = {
                    'pageSize': page_size,
                    'userName': user_name,
                    'cursor': cursor
                }
                headers = {
                    'X-API-Key': self.api_key
                }

                self.logger.debug(f"  API请求(第{page_num}页): {url}?userName={user_name}&pageSize={page_size}&cursor={cursor[:20]}...")

                response = requests.get(url, params=params, headers=headers, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    followings = data.get('followings', [])
                    has_next_page = data.get('has_next_page', False)
                    next_cursor = data.get('next_cursor', '')

                    all_followings.extend(followings)
                    self.logger.debug(f"  第{page_num}页获取到 {len(followings)} 条数据, 累计: {len(all_followings)} 条")

                    # 如果没有下一页,结束循环
                    if not has_next_page or not next_cursor:
                        break

                    # 准备获取下一页
                    cursor = next_cursor
                    page_num += 1

                    # 分页间隔,避免请求过快
                    time.sleep(0.5)
                else:
                    self.logger.error(f"  API请求失败: HTTP {response.status_code}")
                    self.logger.error(f"  响应内容: {response.text[:200]}")
                    break

            return all_followings

        except requests.RequestException as e:
            self.logger.error(f"  API请求异常: {e}")
            return all_followings  # 返回已获取的数据
        except json.JSONDecodeError as e:
            self.logger.error(f"  JSON解析失败: {e}")
            return all_followings
        except Exception as e:
            self.logger.error(f"  获取关注列表失败: {e}")
            return all_followings

    def _save_followings(self, followings: List[Dict[str, Any]], follower_id: str = None) -> int:
        """
        保存关注用户到数据库（批量插入优化）

        Args:
            followings: 关注用户列表
            follower_id: 关注者的user_name（即哪个KOL关注了这些用户）

        Returns:
            成功插入的数量
        """
        if not followings:
            return 0

        try:
            # 1. 批量映射数据
            user_data_list = []
            for following in followings:
                try:
                    user_data = self._map_following_data(following, follower_id)
                    user_data_list.append(user_data)
                except Exception as e:
                    self.logger.warning(f"  映射数据失败 {following.get('id')}: {e}")
                    continue

            if not user_data_list:
                return 0

            # 2. 批量插入
            return self._batch_insert_users(user_data_list)

        except Exception as e:
            self.logger.error(f"  批量保存失败: {e}")
            # 批量插入失败时，回退到逐条插入
            self.logger.warning(f"  回退到逐条插入模式...")
            return self._save_followings_fallback(followings, follower_id)

    def _map_following_data(self, following: Dict[str, Any], follower_id: str = None) -> Dict[str, Any]:
        """
        映射API返回数据到数据库字段

        Args:
            following: API返回的关注用户数据
            follower_id: 关注者的user_name（即哪个KOL关注了这个用户）

        Returns:
            映射后的数据字典
        """
        # 解析创建时间
        created_at_str = following.get('created_at')
        created_at_time = None
        account_age_days = None

        if created_at_str:
            try:
                # 解析时间字符串
                parsed_time = parser.parse(created_at_str)

                # 移除时区信息，转换为naive datetime
                if parsed_time.tzinfo is not None:
                    created_at_time = parsed_time.replace(tzinfo=None)
                else:
                    created_at_time = parsed_time

                # 计算账户年龄
                account_age_days = (datetime.now() - created_at_time).days

            except Exception as e:
                self.logger.warning(f"  解析时间失败 ({created_at_str}): {e}")
                # 时间解析失败时，尝试只保留原始字符串
                created_at_time = None
                account_age_days = None

        return {
            'id': following.get('id'),
            'name': following.get('name'),
            'user_name': following.get('screen_name'),  # screen_name -> user_name
            'avatar': following.get('profile_image_url_https'),
            'description': following.get('description'),
            'created_at': created_at_str,
            'created_at_time': created_at_time,
            'account_age_days': account_age_days,
            'followers': following.get('followers_count', 0),
            'following': following.get('following_count', 0),
            'statuses_count': following.get('statuses_count', 0),
            'follower_id': follower_id,  # 添加关注者的user_name
            'update_time': datetime.now()
        }

    def _insert_or_update_user(self, user_data: Dict[str, Any]) -> bool:
        """
        插入或更新用户数据（使用 Doris Unique Key 自动去重）

        Args:
            user_data: 用户数据

        Returns:
            是否成功
        """
        try:
            # 使用反引号包裹保留关键字字段名（following）
            sql = """
            INSERT INTO public_data.twitter_kol_all (
                `id`, `name`, `user_name`, `avatar`, `description`,
                `created_at`, `created_at_time`, `account_age_days`,
                `followers`, `following`, `statuses_count`, `follower_id`, `update_time`
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            params = (
                user_data['id'],
                user_data['name'],
                user_data['user_name'],
                user_data['avatar'],
                user_data['description'],
                user_data['created_at'],
                user_data['created_at_time'],
                user_data['account_age_days'],
                user_data['followers'],
                user_data['following'],
                user_data['statuses_count'],
                user_data['follower_id'],
                user_data['update_time']
            )

            affected_rows = self.db_manager.execute_update(sql, params)
            return affected_rows > 0

        except Exception as e:
            # 如果是重复键错误，不算失败
            if 'Duplicate entry' in str(e) or 'duplicate key' in str(e).lower():
                self.logger.debug(f"  用户已存在: {user_data['id']}")
                return False
            else:
                raise e

    def _batch_insert_users(self, user_data_list: List[Dict[str, Any]]) -> int:
        """
        批量插入用户数据（性能优化）

        Args:
            user_data_list: 用户数据列表

        Returns:
            成功插入的数量
        """
        if not user_data_list:
            return 0

        try:
            sql = """
            INSERT INTO public_data.twitter_kol_all (
                `id`, `name`, `user_name`, `avatar`, `description`,
                `created_at`, `created_at_time`, `account_age_days`,
                `followers`, `following`, `statuses_count`, `follower_id`, `update_time`
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            # 准备批量插入的参数
            params_list = []
            for user_data in user_data_list:
                params = (
                    user_data['id'],
                    user_data['name'],
                    user_data['user_name'],
                    user_data['avatar'],
                    user_data['description'],
                    user_data['created_at'],
                    user_data['created_at_time'],
                    user_data['account_age_days'],
                    user_data['followers'],
                    user_data['following'],
                    user_data['statuses_count'],
                    user_data['follower_id'],
                    user_data['update_time']
                )
                params_list.append(params)

            # 使用 db_manager 的上下文管理器批量执行
            with self.db_manager.get_cursor() as (conn, cursor):
                try:
                    cursor.executemany(sql, params_list)
                    conn.commit()
                    inserted_count = cursor.rowcount
                    self.logger.debug(f"  批量插入成功: {inserted_count} 条")
                    return inserted_count
                except Exception as e:
                    conn.rollback()
                    # 如果是重复键错误，尝试逐条插入以获取准确计数
                    if 'Duplicate entry' in str(e) or 'duplicate key' in str(e).lower():
                        self.logger.debug(f"  批量插入遇到重复键，切换到逐条插入模式")
                        return self._save_followings_one_by_one(user_data_list)
                    else:
                        raise e

        except Exception as e:
            self.logger.error(f"  批量插入失败: {e}")
            raise e

    def _save_followings_one_by_one(self, user_data_list: List[Dict[str, Any]]) -> int:
        """
        逐条插入用户数据（处理重复键情况）

        Args:
            user_data_list: 用户数据列表

        Returns:
            成功插入的数量
        """
        inserted_count = 0
        for user_data in user_data_list:
            try:
                if self._insert_or_update_user(user_data):
                    inserted_count += 1
            except Exception as e:
                self.logger.warning(f"  插入用户失败 {user_data['id']}: {e}")
                continue
        return inserted_count

    def _save_followings_fallback(self, followings: List[Dict[str, Any]], follower_id: str = None) -> int:
        """
        回退方案：逐条保存（原始实现）

        Args:
            followings: 关注用户列表
            follower_id: 关注者的user_name（即哪个KOL关注了这些用户）

        Returns:
            成功插入的数量
        """
        inserted_count = 0
        for following in followings:
            try:
                user_data = self._map_following_data(following, follower_id)
                if self._insert_or_update_user(user_data):
                    inserted_count += 1
            except Exception as e:
                self.logger.error(f"  保存用户失败 {following.get('id')}: {e}")
                continue
        return inserted_count

    def _show_statistics(self, test_mode: bool = False, dry_run: bool = False, resume_mode: bool = False):
        """显示统计信息"""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("处理完成！")
        self.logger.info(f"总KOL数: {self.total_kols}")
        self.logger.info(f"已处理: {self.processed_kols}")
        self.logger.info(f"成功: {self.success_kols}")
        self.logger.info(f"失败: {self.failed_kols}")

        if not test_mode:
            self.logger.info(f"\nAPI调用统计:")
            self.logger.info(f"  API调用次数: {self.api_calls}")
            self.logger.info(f"  缓存命中次数: {self.cache_hits}")
            self.logger.info(f"  总关注用户数: {self.total_followings}")

            if not dry_run:
                self.logger.info(f"\n入库统计:")
                self.logger.info(f"  新增入库: {self.inserted_followings}")
                self.logger.info(f"  已存在跳过: {self.skipped_followings}")

        self.logger.info("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description='获取KOL关注列表并入库（带缓存和断点续传）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试模式
  python %(prog)s --test

  # 模拟运行
  python %(prog)s --dry-run --limit 1

  # 正式运行
  python %(prog)s --limit 10

  # 从缓存恢复
  python %(prog)s --resume

  # 查看缓存状态
  python %(prog)s --cache-status

  # 清理缓存
  python %(prog)s --clear-cache
        """
    )

    parser.add_argument('--limit', type=int, default=None,
                        help='限制处理的KOL数量')
    parser.add_argument('--skip', type=int, default=0,
                        help='跳过前N个KOL（已废弃，使用进度自动跳过）')
    parser.add_argument('--test', action='store_true',
                        help='测试模式（不调用API，不入库）')
    parser.add_argument('--dry-run', action='store_true',
                        help='模拟运行（调用API但不入库）')
    parser.add_argument('--resume', action='store_true',
                        help='恢复模式（只处理已缓存的数据，不调用API）')
    parser.add_argument('--cache-status', action='store_true',
                        help='查看缓存状态')
    parser.add_argument('--clear-cache', action='store_true',
                        help='清理所有缓存和进度')
    parser.add_argument('--cache-dir', type=str, default='.kol_cache',
                        help='缓存目录路径（默认: .kol_cache）')
    parser.add_argument('--sleep', type=float, default=0.5,
                        help='API调用间隔秒数（默认: 0.5秒，设为0表示无间隔）')
    parser.add_argument('--api-key', type=str,
                        default='new1_038536908c7f4960812ee7d601f620a1',
                        help='Twitter API密钥')

    args = parser.parse_args()

    # 创建获取器
    fetcher = KOLFollowingsFetcher(api_key=args.api_key, cache_dir=args.cache_dir)
    logger = get_logger(__name__)

    # 处理特殊命令
    if args.cache_status:
        fetcher.show_cache_status()
        sys.exit(0)

    if args.clear_cache:
        confirm = input("确认清理所有缓存和进度？(yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            fetcher.clear_all_cache()
            print("\n✓ 缓存已清理")
            sys.exit(0)
        else:
            print("\n✗ 操作已取消")
            sys.exit(0)

    # 测试数据库连接
    if not db_manager.test_connection():
        logger.error("数据库连接失败，请检查配置")
        sys.exit(1)

    logger.info("数据库连接成功\n")

    # 执行获取
    success = fetcher.fetch_all_kol_followings(
        limit=args.limit,
        skip=args.skip,
        test_mode=args.test,
        dry_run=args.dry_run,
        resume_mode=args.resume,
        sleep_interval=args.sleep
    )

    if success:
        print("\n✓ 处理完成")
        sys.exit(0)
    else:
        print("\n✗ 处理失败")
        sys.exit(1)


if __name__ == '__main__':
    main()

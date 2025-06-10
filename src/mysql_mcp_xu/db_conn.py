import asyncio
import logging

import aiomysql
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mysql_mcp_xu')


class MySQLConnectionPool:
    """MySQL 连接池，具备自动重连功能"""

    def __init__(self, config):
        self.pool: Optional[aiomysql.Pool] = None
        self.config = config
        self.max_retries = 3
        self.retry_delay = 2

    async def init_pool(self):
        """初始化连接池"""
        for attempt in range(self.max_retries):
            try:
                if self.pool and not self.pool.closed:
                    self.pool.close()
                    await self.pool.wait_closed()

                self.pool = await aiomysql.create_pool(
                    # autocommit=True,
                    pool_recycle=300,  # 每 5 分钟重新连接一次
                    minsize=1,
                    connect_timeout=15,
                    echo=False,
                    charset='utf8mb4',
                    # init_command="SET SESSION sql_mode='STRICT_TRANS_TABLES'",
                    **self.config
                )

                await self._test_connection()
                logger.info("连接池已成功初始化")
                return

            except Exception as e:
                logger.error(f"连接池初始化失败 (尝试次数: {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise Exception("连接池初始化失败")

    async def _test_connection(self):
        """测试连接池是否正常运行"""
        if not self.pool or self.pool.closed:
            raise Exception("连接池没有正常运行")

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT 1")
                result = await cursor.fetchone()
                if not result or result[0] != 1:
                    raise Exception("连接池测试失败")

    async def get_connection(self):
        """从池中获取连接，并实现自动重连功能"""
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                if not self.pool or self.pool.closed:
                    await self.init_pool()
                await self._test_connection()
                return self.pool.acquire()
            except Exception as e:
                logger.warning(f"次数： {attempt + 1} 连接失败，重试中... : {e}")
                if self.pool and not self.pool.closed:
                    try:
                        self.pool.close()
                        await self.pool.wait_closed()
                    except:
                        pass
                    self.pool = None

                if attempt < max_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise Exception(f"数据库连接失败")

    async def close(self):
        """
        关闭连接池
        """
        if self.pool and not self.pool.closed:
            self.pool.close()
            await self.pool.wait_closed()
            logger.info("连接池已关闭")

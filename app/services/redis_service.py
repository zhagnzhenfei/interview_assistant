import json
from redis import asyncio as aioredis
from typing import Optional, Dict, Any
import os
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

load_dotenv()

class RedisService:
    def __init__(self):
        # 使用环境变量中配置的 Redis URL，包含密码
        self.redis_url = os.getenv("REDIS_URL", "redis://:redis123456@localhost:6379/0")
        self.redis = None

    async def connect(self):
        if not self.redis:
            try:
                self.redis = await aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # 测试连接
                await self.redis.ping()
                logging.info("Successfully connected to Redis")
            except Exception as e:
                logging.error(f"Redis connection error: {str(e)}")
                raise

    async def disconnect(self):
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def create_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """创建新任务"""
        task_data.update({
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        await self.redis.set(f"task:{task_id}", json.dumps(task_data))
        # 设置24小时过期
        await self.redis.expire(f"task:{task_id}", 24 * 60 * 60)

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        task_data = await self.redis.get(f"task:{task_id}")
        return json.loads(task_data) if task_data else None

    async def update_task_status(self, task_id: str, status: str, result: Optional[str] = None) -> bool:
        """更新任务状态"""
        task_data = await self.get_task(task_id)
        if not task_data:
            return False
        
        task_data.update({
            "status": status,
            "updated_at": datetime.now().isoformat()
        })
        if result:
            task_data["result"] = result

        await self.redis.set(f"task:{task_id}", json.dumps(task_data))
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task_data = await self.get_task(task_id)
        if not task_data or task_data["status"] == "completed":
            return False

        await self.update_task_status(task_id, "cancelled")
        return True

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        return await self.redis.delete(f"task:{task_id}") > 0

# 创建全局Redis服务实例
redis_service = RedisService() 
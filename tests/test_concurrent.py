import asyncio
import aiohttp
import os
import json
from datetime import datetime
import logging
from typing import List, Dict
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 测试配置
BASE_URL = "http://localhost:8000"  # 根据实际情况修改
TOKEN = "your_test_token"  # 替换为实际的测试token
CONCURRENT_USERS = 10  # 并发用户数
TEST_IMAGE_PATH = "/home/ubuntu/interview_assistant/test_inages/0b575d36db614da2528a1c2e9306ea5.jpg"
PROGRAMMING_LANGUAGES = ["python", "java", "cpp", "javascript"]

class ConcurrentTest:
    def __init__(self):
        self.results: List[Dict] = []
        self.session = None

    async def init_session(self):
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def upload_image(self, user_id: int) -> str:
        """上传图片并返回image_url"""
        try:
            with open(TEST_IMAGE_PATH, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('image',
                             f,
                             filename='test.jpg',
                             content_type='image/jpeg')

                async with self.session.post(
                    f"{BASE_URL}/upload_image",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["image_url"]
                    else:
                        error_text = await response.text()
                        raise Exception(f"Upload failed: {error_text}")
        except Exception as e:
            logger.error(f"User {user_id} - Upload failed: {str(e)}")
            raise

    async def submit_task(self, user_id: int, image_url: str) -> str:
        """提交任务并返回task_id"""
        try:
            data = {
                "image_url": image_url,
                "programming_language": random.choice(PROGRAMMING_LANGUAGES)
            }

            async with self.session.post(
                f"{BASE_URL}/chat_with_vlm/submit",
                headers={
                    "Authorization": f"Bearer {TOKEN}",
                    "Content-Type": "application/json"
                },
                json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["task_id"]
                else:
                    error_text = await response.text()
                    raise Exception(f"Submit failed: {error_text}")
        except Exception as e:
            logger.error(f"User {user_id} - Submit failed: {str(e)}")
            raise

    async def check_task_status(self, user_id: int, task_id: str) -> Dict:
        """检查任务状态"""
        try:
            async with self.session.get(
                f"{BASE_URL}/chat_with_vlm/status/{task_id}",
                headers={"Authorization": f"Bearer {TOKEN}"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"Status check failed: {error_text}")
        except Exception as e:
            logger.error(f"User {user_id} - Status check failed: {str(e)}")
            raise

    async def get_stream_response(self, user_id: int, task_id: str):
        """获取流式响应"""
        try:
            async with self.session.get(
                f"{BASE_URL}/chat_with_vlm/stream/{task_id}",
                headers={"Authorization": f"Bearer {TOKEN}"}
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            yield line.decode('utf-8')
                else:
                    error_text = await response.text()
                    raise Exception(f"Stream failed: {error_text}")
        except Exception as e:
            logger.error(f"User {user_id} - Stream failed: {str(e)}")
            raise

    async def simulate_user(self, user_id: int):
        """模拟单个用户的操作流程"""
        start_time = datetime.now()
        try:
            # 1. 上传图片
            image_url = await self.upload_image(user_id)
            logger.info(f"User {user_id} - Image uploaded: {image_url}")

            # 2. 提交任务
            task_id = await self.submit_task(user_id, image_url)
            logger.info(f"User {user_id} - Task submitted: {task_id}")

            # 3. 检查任务状态
            status = await self.check_task_status(user_id, task_id)
            logger.info(f"User {user_id} - Task status: {status['status']}")

            # 4. 获取流式响应
            response_count = 0
            async for response in self.get_stream_response(user_id, task_id):
                response_count += 1
                if response_count % 10 == 0:  # 每10条响应记录一次
                    logger.info(f"User {user_id} - Received response {response_count}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.results.append({
                "user_id": user_id,
                "status": "success",
                "duration": duration,
                "response_count": response_count
            })

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.results.append({
                "user_id": user_id,
                "status": "failed",
                "duration": duration,
                "error": str(e)
            })

    async def run_concurrent_test(self):
        """运行并发测试"""
        await self.init_session()
        try:
            # 创建并发任务
            tasks = [self.simulate_user(i) for i in range(CONCURRENT_USERS)]
            
            # 等待所有任务完成
            start_time = datetime.now()
            await asyncio.gather(*tasks)
            end_time = datetime.now()
            
            # 计算总体统计信息
            total_duration = (end_time - start_time).total_seconds()
            successful_tests = len([r for r in self.results if r["status"] == "success"])
            failed_tests = len([r for r in self.results if r["status"] == "failed"])
            
            # 输出测试报告
            logger.info("\n=== Test Report ===")
            logger.info(f"Total Duration: {total_duration:.2f} seconds")
            logger.info(f"Concurrent Users: {CONCURRENT_USERS}")
            logger.info(f"Successful Tests: {successful_tests}")
            logger.info(f"Failed Tests: {failed_tests}")
            
            if successful_tests > 0:
                avg_duration = sum(r["duration"] for r in self.results if r["status"] == "success") / successful_tests
                logger.info(f"Average Duration per User: {avg_duration:.2f} seconds")
            
            # 输出详细结果
            logger.info("\nDetailed Results:")
            for result in self.results:
                logger.info(f"User {result['user_id']}: {result['status']} - Duration: {result['duration']:.2f}s")
                if result['status'] == 'failed':
                    logger.info(f"Error: {result['error']}")
                
        finally:
            await self.close_session()

def main():
    test = ConcurrentTest()
    asyncio.run(test.run_concurrent_test())

if __name__ == "__main__":
    main() 
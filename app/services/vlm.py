import os
from openai import AsyncOpenAI
from fastapi import HTTPException
import json
import base64
import asyncio
from typing import AsyncGenerator
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 创建信号量来限制并发请求数
semaphore = asyncio.Semaphore(5)  # 最多允许5个并发请求

async def vlm(base64_image: str, user_question: str) -> AsyncGenerator[str, None]:
    """异步VLM服务"""
    async with semaphore:  # 使用信号量控制并发
        try:
            # 初始化OpenAI客户端
            client = AsyncOpenAI(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url=os.getenv("DASHSCOPE_BASE_URL"),
            )

            # 检测图片类型
            image_bytes = base64.b64decode(base64_image)
            if image_bytes.startswith(b'\xff\xd8'):
                mime_type = "image/jpeg"
            elif image_bytes.startswith(b'\x89PNG'):
                mime_type = "image/png"
            elif image_bytes.startswith(b'BM'):
                mime_type = "image/bmp"
            elif image_bytes.startswith(b'II') or image_bytes.startswith(b'MM'):
                mime_type = "image/tiff"
            elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:12]:
                mime_type = "image/webp"
            elif image_bytes.startswith(b'\x00\x00\x01\x00'):
                mime_type = "image/x-icon"
            elif image_bytes.startswith(b'\x00\x00\x02\x00'):
                mime_type = "image/x-icon"
            elif image_bytes.startswith(b'\x00\x00\x01\x00'):
                mime_type = "image/x-icns"
            elif image_bytes.startswith(b'\x00\x00\x01\x00'):
                mime_type = "image/x-sgi"
            elif image_bytes.startswith(b'\x00\x00\x00\x0c'):
                mime_type = "image/jp2"
            else:
                raise ValueError("Unsupported image format. Supported formats: BMP, DIB, ICNS, ICO, JPEG, JPEG2000, PNG, SGI, TIFF, WEBP")

            # 构建消息列表
            messages = [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "你是一个算法解题助手"}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                        },
                        {"type": "text", "text": user_question},
                    ],
                },
            ]

            # 发起异步ChatCompletion请求
            completion = await client.chat.completions.create(
                model="qwen-omni-turbo",
                messages=messages,
                modalities=["text"],
                stream=True,
                stream_options={"include_usage": True},
            )

            # 处理流式响应
            async for chunk in completion:
                if chunk.choices:
                    content = chunk.choices[0].delta.content
                    if content:
                        message = {
                            "role": "assistant",
                            "content": content,
                        }
                        json_message = json.dumps(message)
                        yield f"event: message\ndata: {json_message}\n\n"
                else:
                    if hasattr(chunk, 'usage'):
                        yield f"event: usage\ndata: {chunk.usage}\n\n"
                    yield "event: done\ndata: \n\n"

        except Exception as e:
            logger.error(f"Error in VLM processing: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error querying chat completion: {str(e)}")
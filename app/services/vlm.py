import os
from openai import OpenAI
from fastapi import HTTPException


def vlm(base64_image, user_question):

    try:
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
        )

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
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                    {"type": "text", "text": user_question},
                ],
            },
        ]

        # 发起ChatCompletion请求
        completion = client.chat.completions.create(
            model="qwen-omni-turbo",
            messages=messages,
            modalities=["text"],
            stream=True,
            stream_options={"include_usage": True},
        )

        # 处理流式响应并格式化为SSE格式
        for chunk in completion:
            if chunk.choices:
                yield f"data: {chunk.choices[0].delta}\n\n"
            else:
                yield f"data: {chunk.usage}\n\n"

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying chat completion: {str(e)}")
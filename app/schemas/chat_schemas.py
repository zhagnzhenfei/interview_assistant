from pydantic import BaseModel

# 定义请求体的 Pydantic 模型
class VLMRequest(BaseModel):
    image_path: str
    programming_language: str
from pydantic import BaseModel, Field

# 定义请求体的 Pydantic 模型
class VLMRequest(BaseModel):
    image_path: str
    programming_language: str

class ChatSubmitRequest(BaseModel):
    """聊天提交请求模型"""
    image_url: str = Field(..., description="图片URL路径")
    programming_language: str = Field(..., description="编程语言")

class ChatSubmitResponse(BaseModel):
    """聊天提交响应模型"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
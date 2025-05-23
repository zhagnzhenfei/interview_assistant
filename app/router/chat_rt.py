from fastapi import APIRouter, HTTPException, Security, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from services.vlm import vlm
from services.redis_service import redis_service
from services.auth import access_security
from services.accounts import update_balance, get_balance_by_user_id, pre_charge_balance, refund_balance
from fastapi_jwt import JwtAuthorizationCredentials
from schemas.chat_schemas import ChatSubmitRequest, ChatSubmitResponse
import base64
import logging
import os
import uuid
import aiofiles
from dotenv import load_dotenv  # 需要安装 python-dotenv
from typing import AsyncGenerator
import asyncio
import json

# 加载环境变量
load_dotenv()

router = APIRouter()

# 从环境变量获取服务费用
SERVICE_FEE = float(os.getenv("SERVICE_FEE", "1.00"))  # 默认1元

@router.get("/hello")
def hello_world():
    return {"message": "Hello, World!"}

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploaded_images") 
@router.post("/upload_image", include_in_schema=True)  
async def upload_image(
    image: UploadFile = File(...),
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    try:
        # 检查用户余额
        user_id = credentials.subject.get("user_id")
        balance_info = get_balance_by_user_id(str(user_id))
        current_balance = float(balance_info["balance"])
        
        if current_balance < SERVICE_FEE:
            raise HTTPException(
                status_code=400, 
                detail=f"余额不足，当前余额：{current_balance}，服务费用：{SERVICE_FEE}"
            )
        
        # 确保上传目录存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # 生成唯一文件名
        file_ext = os.path.splitext(image.filename)[1]
        filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # 异步保存文件
        content = await image.read()
        async with aiofiles.open(file_path, mode='wb') as f:
            await f.write(content)
            
        # 生成图片URL
        image_url = f"/images/{filename}"
        return JSONResponse(content={"image_url": image_url})
        
    except HTTPException as e:
        raise
    except Exception as e:
        logging.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

async def process_vlm_stream(base64_image: str, user_question: str, task_id: str, user_id: str) -> AsyncGenerator[str, None]:
    """处理VLM流式响应"""
    try:
        # 预扣费用
        pre_charge_balance(
            user_id=int(user_id),
            amount=SERVICE_FEE,
            task_id=task_id
        )
        
        async for chunk in vlm(base64_image, user_question):
            yield chunk
            # 添加小延迟避免过快输出
            await asyncio.sleep(0.01)
            
        # 流式响应完成后，确认扣费
        try:
            new_balance = update_balance(
                user_id=int(user_id),
                amount=-SERVICE_FEE,  # 负数表示扣费
                trans_type="扣费",
                desc=f"VLM服务费用 - 任务ID: {task_id}"
            )
            logging.info(f"服务费用扣除成功 | 用户：{user_id} | 扣除金额：{SERVICE_FEE} | 剩余余额：{new_balance}")
        except Exception as e:
            logging.error(f"服务费用扣除失败：{str(e)}", exc_info=True)
            # 这里我们不抛出异常，因为服务已经完成
            
        # 更新任务状态为已完成
        await redis_service.update_task_status(task_id, "completed")
            
    except Exception as e:
        logging.error(f"Error in VLM processing: {str(e)}")
        # 发生错误时，退还预扣的费用
        try:
            refund_balance(
                user_id=int(user_id),
                amount=SERVICE_FEE,
                task_id=task_id
            )
            logging.info(f"预扣费用退还成功 | 用户：{user_id} | 退还金额：{SERVICE_FEE}")
        except Exception as refund_error:
            logging.error(f"预扣费用退还失败：{str(refund_error)}", exc_info=True)
            
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        # 发生错误时，更新任务状态为失败
        await redis_service.update_task_status(task_id, "failed", str(e))

@router.get("/chat_with_vlm/stream/{task_id}")
async def stream_chat(
    task_id: str, 
    background_tasks: BackgroundTasks,
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    try:
        # 获取任务信息
        task = await redis_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # 验证任务是否属于当前用户
        user_id = credentials.subject.get("user_id")
        if task.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this task")
        
        if task["status"] == "cancelled":
            raise HTTPException(status_code=400, detail="Task was cancelled")
            
        # 更新任务状态为处理中
        await redis_service.update_task_status(task_id, "processing")
            
        # 从URL中提取文件名
        filename = os.path.basename(task["image_url"])
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Image not found")
            
        # 异步读取图片并转换为Base64
        async with aiofiles.open(file_path, "rb") as f:
            image_content = await f.read()
        base64_image = base64.b64encode(image_content).decode("utf-8")

        user_question = f"""
        请仔细分析图片中的算法题目，并按照以下格式用 {task["programming_language"]} 语言提供解决方案：

        ### 解题思路
        - 分析问题的关键点
        - 提供清晰的解题步骤
        - 说明算法的时间和空间复杂度
        
        ### 代码实现
        ```{task["programming_language"]}
        // 在这里实现具体代码
        // 每行代码都添加清晰的注释
        ```
        """

        # 设置正确的响应头
        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }

        # 创建SSE响应
        return StreamingResponse(
            content=process_vlm_stream(base64_image, user_question, task_id, user_id),
            media_type="text/event-stream",
            headers=headers
        )

    except HTTPException as e:
        raise
    except Exception as e:
        # 更新任务状态为失败
        await redis_service.update_task_status(task_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.on_event("startup")
async def startup_event():
    await redis_service.connect()

@router.on_event("shutdown")
async def shutdown_event():
    await redis_service.disconnect()

@router.post("/chat_with_vlm/submit", response_model=ChatSubmitResponse)
async def submit_chat(
    request: ChatSubmitRequest,
    background_tasks: BackgroundTasks = None,
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    try:
        task_id = str(uuid.uuid4())
        
        # 创建任务
        await redis_service.create_task(task_id, {
            "image_url": request.image_url,
            "programming_language": request.programming_language,
            "user_id": credentials.subject.get("user_id")  # 添加用户ID到任务信息中
        })
        
        return ChatSubmitResponse(task_id=task_id, status="pending")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/chat_with_vlm/status/{task_id}")
async def get_task_status(
    task_id: str,
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    """获取任务状态"""
    task = await redis_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 验证任务是否属于当前用户
    if task.get("user_id") != credentials.subject.get("user_id"):
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
        
    return task

@router.post("/chat_with_vlm/cancel/{task_id}")
async def cancel_task(
    task_id: str,
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    """取消任务"""
    task = await redis_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # 验证任务是否属于当前用户
    if task.get("user_id") != credentials.subject.get("user_id"):
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")
        
    success = await redis_service.cancel_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel task")
        
    # 如果任务被取消，退还预扣的费用
    try:
        refund_balance(
            user_id=int(task.get("user_id")),
            amount=SERVICE_FEE,
            task_id=task_id
        )
        logging.info(f"任务取消，预扣费用退还成功 | 用户：{task.get('user_id')} | 退还金额：{SERVICE_FEE}")
    except Exception as e:
        logging.error(f"任务取消，预扣费用退还失败：{str(e)}", exc_info=True)
        
    return {"status": "cancelled"}
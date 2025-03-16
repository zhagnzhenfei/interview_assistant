
from fastapi import APIRouter, HTTPException, Security, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from services.vlm import  vlm
from services.auth import access_security
from fastapi_jwt import JwtAuthorizationCredentials
import base64
import logging

router = APIRouter()


@router.post("/chat_with_vlm/")
async def chat_with_vlm(image: UploadFile = File(...), 
                        programming_language: str = Form(...)
                                # credentials: JwtAuthorizationCredentials = Security(access_security),
                                ):

    try:
        # user_id = str(credentials.subject.get("user_id"))
        # if not user_id:
        #     raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        # TODO: 查询余额

        user_question = f"""
        这是一道算法题，请你仔细查看图片内容，理解其中的问题或任务。请按照 {programming_language} 语言编写代码来解决问题要求：
        1.先描述题目内容（确认理解正确）。
        2.提供解题思路。
        3.给出具体的答案或者代码实现，使用。
        4.如果是编程题，需要解释代码逻辑。
        """
        
        # 读取上传的文件内容并转换为 Base64
        image_content = await image.read()
        base64_image = base64.b64encode(image_content).decode("utf-8")
        logging.info(f"Base64 image length: {len(base64_image)}")  # 调试日志

        # 创建SSE响应
        return StreamingResponse(
            content=vlm(base64_image, user_question),
            media_type="text/event-stream",
        )

    except HTTPException as e:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
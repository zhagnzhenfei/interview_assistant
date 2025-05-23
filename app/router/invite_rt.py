from fastapi import APIRouter, HTTPException, Security
from pydantic import BaseModel
import os
from typing import List
import logging
from services.auth import access_security
from fastapi_jwt import JwtAuthorizationCredentials

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

class InviteCodeRequest(BaseModel):
    code: str

class InviteCodeResponse(BaseModel):
    is_valid: bool
    message: str

# 从环境变量获取有效的邀请码列表
def get_valid_invite_codes() -> List[str]:
    invite_codes = os.getenv("VALID_INVITE_CODES", "")
    return [code.strip() for code in invite_codes.split(",") if code.strip()]

@router.post("/verify-invite-code", response_model=InviteCodeResponse)
async def verify_invite_code(
    request: InviteCodeRequest,
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    """
    验证邀请码是否有效
    """
    try:
        # 验证用户token
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        valid_codes = get_valid_invite_codes()
        if not valid_codes:
            logger.warning("No valid invite codes configured")
            return InviteCodeResponse(
                is_valid=False,
                message="Invite code system is not properly configured"
            )
        
        if request.code in valid_codes:
            return InviteCodeResponse(
                is_valid=True,
                message="Invite code is valid"
            )
        else:
            return InviteCodeResponse(
                is_valid=False,
                message="Invalid invite code"
            )
            
    except Exception as e:
        logger.error(f"Error verifying invite code: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 
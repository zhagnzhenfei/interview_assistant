from fastapi import APIRouter, HTTPException, status, Request, Depends
from schemas.sms_auth import SMSRequest, VerifyCodeRequest, SMSResponse, TokenResponse
from services.sms_service import sms_service
from utils.logger import logger

router = APIRouter(prefix="/sms")

@router.post("/send", response_model=SMSResponse)
async def send_verification_code(request_data: SMSRequest, request: Request):
    """
    发送短信验证码
    
    - **phone_number**: 手机号码
    """
    try:
        # 调用服务发送验证码
        success, message = await sms_service.send_verification_code(
            request_data.phone_number, 
            request
        )
        
        # 返回响应
        return SMSResponse(success=success, message=message)
    
    except Exception as e:
        # 记录错误日志
        logger.error(f"Error sending verification code: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送验证码失败，请稍后重试"
        )

@router.post("/verify", response_model=TokenResponse)
async def verify_sms_code(request_data: VerifyCodeRequest):
    """
    验证短信验证码并登录
    
    - **phone_number**: 手机号码
    - **code**: 验证码
    """
    try:
        # 记录请求参数
        logger.info(f"Verifying SMS code for phone number: {request_data.phone_number}")
        
        # 调用服务验证验证码并登录
        token = await sms_service.login_with_code(
            request_data.phone_number,
            request_data.code
        )
        
        # 记录验证结果
        if not token:
            logger.warning(f"Verification failed for phone number: {request_data.phone_number}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="验证码不正确或已过期"
            )
        
        # 登录成功，记录日志
        logger.info(f"Successfully verified and logged in user with phone number: {request_data.phone_number}")
        
        # 登录成功，返回Token
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=172800  # 2天
        )
    
    except HTTPException:
        # 直接抛出已经处理的HTTP异常
        raise
    
    except Exception as e:
        # 记录错误日志
        logger.error(f"Error verifying SMS code for phone number {request_data.phone_number}: {str(e)}", exc_info=True)
        # 返回错误响应
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证失败，请稍后重试"
        ) 
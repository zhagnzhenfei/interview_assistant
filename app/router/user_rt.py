from fastapi import APIRouter, HTTPException, status
from services.auth import AuthError
from schemas.user import UserCreate, UserResponse, UserLogin, WxLoginRequest
from fastapi import Depends
from sqlalchemy.orm import Session
from utils.database import get_db
from services.auth import auth_service
from utils.logger import logger
from schemas.sms_auth import TokenResponse

router = APIRouter()

# 用户认证接口
@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin):
    try:
        # 调用 auth_service 进行认证
        token = auth_service.authenticate(request.username, request.password)
        return TokenResponse(access_token=token, token_type="bearer")
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )

# 用户注册接口
@router.post("/register", response_model=UserResponse)
async def register(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    try:
        return await auth_service.register_user(db, user)
    except AuthError as e:
        # 返回具体的认证错误信息
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except ValueError as e:
        # 返回参数验证错误
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        # 记录意外错误
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error, please try again later"
        )

@router.post("/wx-login", response_model=TokenResponse)
async def wx_login(request: WxLoginRequest):
    """
    小程序登录接口
    """
    try:
        # 调用 auth_service 进行小程序登录
        token, user = await auth_service.wx_login(request.code)
        return TokenResponse(access_token=token, token_type="bearer")
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during wx login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )
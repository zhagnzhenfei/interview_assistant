from utils.database import get_db
from models.user import User
from utils.password import verify_password, hash_password
from sqlalchemy.exc import SQLAlchemyError
from fastapi_jwt import JwtAccessBearerCookie
import secrets
from datetime import timedelta, datetime
import os
from models.account import Account
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from schemas.user import UserCreate, UserResponse
import logging
import httpx
from typing import Optional, Tuple
from fastapi import HTTPException
from fastapi_jwt import JwtAuthorizationCredentials

# 定义自定义异常类
class AuthError(Exception):
    """认证相关的异常"""
    pass

load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

# JWT配置
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default_secret_key') + 'happy'

# 从请求头或cookie中读取访问令牌（优先从请求头读取）
access_security = JwtAccessBearerCookie(
    secret_key=JWT_SECRET_KEY,
    auto_error=True,
    access_expires_delta=timedelta(days=2)  # 访问令牌有效期为2天
)

# 获取默认余额配置
DEFAULT_BALANCE = float(os.getenv("DEFAULT_BALANCE", "4.90"))

class AuthService:
    @staticmethod
    async def get_user_by_username(db: Session, username: str) -> User:
        """根据用户名获取用户"""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def create_token(user_id: int, user_name: str, salting: str = ""):
        # 生成token的主体部分，包含用户名和随机盐值
        subject = {
            "user_id": user_id,
            "user_name": user_name,
            "salting": secrets.token_hex(16)
        }
        
        # 创建新的访问令牌
        access_token = access_security.create_access_token(subject=subject)
        
        return access_token

    @staticmethod
    def authenticate(username: str, password: str) -> str:
        """
        认证用户
        
        Args:
            username (str): 用户名
            password (str): 明文密码
        
        Returns:
            str: 认证成功返回token，失败返回None
        
        Raises:
            AuthError: 认证失败时抛出
        """
        db = next(get_db())
        try:
            # 查询用户
            user = db.query(User).filter(User.username == username).first()
            
            if not user:
                raise AuthError("用户名或密码错误")
            
            # 验证密码
            if not verify_password(password, user.password_hash):
                raise AuthError("用户名或密码错误")
            
            return AuthService.create_token(user.id, user.username)
        
        except SQLAlchemyError as e:
            logger.error(f"Database error during authentication: {str(e)}")
            raise AuthError("认证失败，请稍后重试") from e
        finally:
            db.close()

    @staticmethod
    async def register_user(db: Session, user: UserCreate) -> User:
        try:
            # 检查用户名是否已存在
            existing_user = db.query(User).filter(User.username == user.username).first()
            if existing_user:
                raise AuthError("用户名已被注册，请使用其他用户名")

            # 创建新用户
            hashed_password = hash_password(user.password)
            db_user = User(
                username=user.username,
                password_hash=hashed_password,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(db_user)
            db.flush()

            # 创建用户账户，使用环境变量中的默认余额
            account = Account(
                user_id=db_user.id,
                balance=DEFAULT_BALANCE,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(account)
            db.commit()
            db.refresh(db_user)
            
            return db_user
            
        except AuthError as e:
            db.rollback()
            logger.warning(f"Registration failed: {str(e)}")
            raise
        except ValueError as e:
            db.rollback()
            logger.warning(f"Invalid registration data: {str(e)}")
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
            raise AuthError("注册失败，请稍后重试")

    @staticmethod
    async def wx_login(code: str) -> Tuple[str, User]:
        """
        处理小程序登录
        
        Args:
            code (str): 小程序登录时获取的 code
            
        Returns:
            Tuple[str, User]: 返回 (token, user) 元组
            
        Raises:
            AuthError: 登录失败时抛出
        """
        try:
            # 获取小程序配置
            appid = os.getenv('WX_APPID')
            secret = os.getenv('WX_SECRET')
            
            if not appid or not secret:
                raise AuthError("小程序配置信息不完整")

            # 调用微信接口获取 openid 和 session_key
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.mch.weixin.qq.com/sns/jscode2session",
                    params={
                        "appid": appid,
                        "secret": secret,
                        "js_code": code,
                        "grant_type": "authorization_code"
                    }
                )
                
                if response.status_code != 200:
                    raise AuthError("微信登录失败")
                    
                result = response.json()
                
                if "errcode" in result and result["errcode"] != 0:
                    raise AuthError(f"微信登录失败: {result.get('errmsg', '未知错误')}")
                
                openid = result.get("openid")
                session_key = result.get("session_key")
                
                if not openid or not session_key:
                    raise AuthError("获取用户信息失败")

            # 获取数据库会话
            db = next(get_db())
            try:
                # 查找或创建用户
                user = db.query(User).filter(User.openid == openid).first()
                
                if not user:
                    # 生成一个基于 openid 的用户名
                    username = f"wx_{openid[:8]}"
                    # 确保用户名唯一
                    while db.query(User).filter(User.username == username).first():
                        username = f"wx_{openid[:8]}_{secrets.token_hex(4)}"
                    
                    # 创建新用户
                    user = User(
                        username=username,
                        password_hash=hash_password(secrets.token_hex(16)),  # 生成随机密码
                        openid=openid,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(user)
                    db.flush()
                    
                    # 创建用户账户，使用环境变量中的默认余额
                    account = Account(
                        user_id=user.id,
                        balance=DEFAULT_BALANCE,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    db.add(account)
                    db.commit()
                    db.refresh(user)
                
                # 生成 token
                token = AuthService.create_token(user.id, user.username)
                
                return token, user
                
            finally:
                db.close()
                
        except httpx.RequestError as e:
            logger.error(f"Request error during wx login: {str(e)}")
            raise AuthError("网络请求失败，请稍后重试")
        except Exception as e:
            logger.error(f"Unexpected error during wx login: {str(e)}", exc_info=True)
            raise AuthError("登录失败，请稍后重试")

# 创建 AuthService 实例
auth_service = AuthService()
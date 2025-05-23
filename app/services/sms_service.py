import random
import re
import time
from typing import Optional, Tuple
import logging
from datetime import datetime, timedelta, UTC, timezone
import os
from dotenv import load_dotenv
from fastapi import Request, HTTPException, status
import secrets

# 导入Redis服务
from services.redis_service import redis_service
from utils.database import get_db
from models.user import User
from services.auth import AuthService
# 导入腾讯云短信服务
from services.tencent_sms import tencent_sms_client
from utils.password import hash_password

load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

# 配置常量
SMS_CODE_LENGTH = 4  # 验证码长度
SMS_CODE_EXPIRY = 300  # 验证码过期时间（秒）
SMS_SEND_INTERVAL = 60  # 发送间隔（秒）
MAX_SMS_PER_IP_DAY = 20  # 每个IP每天最大发送次数
MAX_SMS_PER_PHONE_DAY = 10  # 每个手机号每天最大发送次数
DEFAULT_BALANCE = float(os.getenv("DEFAULT_BALANCE", "4.90"))  # 默认赠送金额

# 短信服务类型：mock或tencent
SMS_SERVICE_TYPE = os.getenv("SMS_SERVICE_TYPE", "mock")

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

class SMSService:
    @staticmethod
    def validate_phone_number(phone_number: str) -> bool:
        """
        验证手机号格式是否正确
        中国大陆手机号格式: 1开头的11位数字
        """
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone_number))

    @staticmethod
    def generate_verification_code(length: int = SMS_CODE_LENGTH) -> str:
        """
        生成指定长度的数字验证码
        """
        # 生成随机数字验证码
        digits = "0123456789"
        return ''.join(random.choice(digits) for _ in range(length))

    @staticmethod
    async def check_ip_limit(ip_address: str) -> bool:
        """
        检查IP是否达到发送限制
        """
        # Redis键格式: ip_limit:{ip_address}
        key = f"ip_limit:{ip_address}"
        
        # 获取当前计数
        count = await redis_service.redis.get(key)
        
        if count is None:
            # 如果不存在，设置初始计数为1，并设置24小时过期
            await redis_service.redis.set(key, 1, ex=86400)
            return True
        
        # 如果存在，检查是否达到限制
        if int(count) >= MAX_SMS_PER_IP_DAY:
            logger.warning(f"IP {ip_address} has reached the daily SMS limit")
            return False
        
        # 没有达到限制，计数加1
        await redis_service.redis.incr(key)
        return True

    @staticmethod
    async def check_phone_frequency(phone_number: str) -> Tuple[bool, str]:
        """
        检查手机号是否可以发送验证码
        返回 (是否可发送, 原因)
        """
        # 验证手机号格式
        if not SMSService.validate_phone_number(phone_number):
            return False, "手机号格式不正确"
        
        # Redis键格式: sms_limit:{phone_number}
        limit_key = f"sms_limit:{phone_number}"
        count_key = f"sms_count:{phone_number}"
        
        # 获取上次发送时间
        last_send_time = await redis_service.redis.get(limit_key)
        
        if last_send_time is not None:
            # 计算距离上次发送的时间间隔
            time_diff = int(time.time()) - int(last_send_time)
            if time_diff < SMS_SEND_INTERVAL:
                wait_time = SMS_SEND_INTERVAL - time_diff
                return False, f"请稍后再试，{wait_time}秒后可再次发送"
        
        # 检查当日发送次数
        count = await redis_service.redis.get(count_key)
        if count is not None and int(count) >= MAX_SMS_PER_PHONE_DAY:
            return False, "手机号当日发送验证码次数已达上限"
        
        return True, ""

    @staticmethod
    async def store_verification_code(phone_number: str, code: str) -> None:
        """
        在Redis中存储验证码
        """
        # Redis键格式: sms_code:{phone_number}
        code_key = f"sms_code:{phone_number}"
        limit_key = f"sms_limit:{phone_number}"
        count_key = f"sms_count:{phone_number}"
        
        # 存储验证码，设置过期时间
        await redis_service.redis.set(code_key, code, ex=SMS_CODE_EXPIRY)
        
        # 更新发送时间记录
        await redis_service.redis.set(limit_key, int(time.time()), ex=SMS_SEND_INTERVAL*2)
        
        # 更新发送次数
        count = await redis_service.redis.get(count_key)
        if count is None:
            # 如果不存在，设置为1，24小时过期
            await redis_service.redis.set(count_key, 1, ex=86400)
        else:
            # 递增计数，保持原有过期时间
            await redis_service.redis.incr(count_key)

    @staticmethod
    async def verify_code(phone_number: str, code: str) -> bool:
        """
        验证用户输入的验证码是否正确
        """
        if not SMSService.validate_phone_number(phone_number) or not code:
            return False
        
        # Redis键格式: sms_code:{phone_number}
        code_key = f"sms_code:{phone_number}"
        
        # 获取存储的验证码
        stored_code = await redis_service.redis.get(code_key)
        
        # 验证码不存在或不匹配
        if stored_code is None or stored_code != code:
            return False
        
        # 验证成功后删除验证码，防止重复使用
        await redis_service.redis.delete(code_key)
        return True

    @staticmethod
    async def send_sms(phone_number: str, code: str) -> bool:
        """
        使用腾讯云发送短信验证码
        """
        try:
            # 调用腾讯云短信服务
            success, result = tencent_sms_client.send_verification_code(phone_number, code)
            if not success:
                logger.error(f"Failed to send SMS via Tencent Cloud: {result}")
            return success
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False

    @staticmethod
    async def send_verification_code(phone_number: str, request: Request) -> Tuple[bool, str]:
        """
        发送验证码的完整流程
        """
        # 获取客户端IP
        client_ip = request.client.host
        
        # 检查IP限制
        if not await SMSService.check_ip_limit(client_ip):
            return False, "请求过于频繁，请稍后再试"
        
        # 检查手机号发送频率
        can_send, reason = await SMSService.check_phone_frequency(phone_number)
        if not can_send:
            return False, reason
        
        # 生成验证码
        code = SMSService.generate_verification_code()
        
        # 打印验证码到日志
        logger.info(f"Generated verification code for {phone_number}: {code}")
        
        # 存储验证码
        await SMSService.store_verification_code(phone_number, code)
        
        # 发送短信
        if await SMSService.send_sms(phone_number, code):
            # 更新发送次数和记录
            return True, "验证码已发送"
        else:
            # 发送失败，删除存储的验证码
            await redis_service.redis.delete(f"sms_code:{phone_number}")
            return False, "验证码发送失败，请稍后重试"
    
    @staticmethod
    async def login_with_code(phone_number: str, code: str) -> Optional[str]:
        """
        使用验证码登录，如果用户不存在则自动注册
        返回JWT Token或None
        """
        # 验证验证码
        if not await SMSService.verify_code(phone_number, code):
            return None
        
        # 获取数据库连接
        db = next(get_db())
        try:
            # 查询用户是否存在
            user = db.query(User).filter(User.phone_number == phone_number).first()
            
            if not user:
                # 生成随机密码
                random_password = secrets.token_urlsafe(16)
                # 用户不存在，创建新用户
                user = User(
                    username=f"user_{phone_number}",  # 使用手机号作为用户名前缀
                    password_hash=hash_password(random_password),  # 设置随机密码的哈希值
                    phone_number=phone_number,
                    created_at=datetime.now(BEIJING_TZ),
                    updated_at=datetime.now(BEIJING_TZ)
                )
                db.add(user)
                db.flush()  # 获取用户ID
                
                # 创建用户账户
                from models.account import Account
                account = Account(
                    user_id=user.id,
                    balance=DEFAULT_BALANCE,  # 从环境变量获取初始余额
                    created_at=datetime.now(BEIJING_TZ),
                    updated_at=datetime.now(BEIJING_TZ)
                )
                db.add(account)
                db.commit()
                db.refresh(user)
            else:
                db.commit()
            
            # 生成JWT Token
            token = AuthService.create_token(user.id, user.username)
            return token
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in login_with_code: {str(e)}")
            return None
        finally:
            db.close()

# 创建服务实例
sms_service = SMSService() 
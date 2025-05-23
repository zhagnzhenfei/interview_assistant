import json
import os
from typing import Dict, List, Union, Tuple
import logging
from dotenv import load_dotenv
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models

load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)

class TencentSmsClient:
    """腾讯云短信服务客户端"""
    
    def __init__(self):
        # 从环境变量获取配置
        self.secret_id = os.getenv("TENCENT_SECRET_ID", "")
        self.secret_key = os.getenv("TENCENT_SECRET_KEY", "")
        self.app_id = os.getenv("TENCENT_SMS_APP_ID", "")
        self.sign_name = os.getenv("TENCENT_SMS_SIGN_NAME", "")
        self.region = os.getenv("TENCENT_REGION", "ap-beijing")  # 默认使用北京区域
        
        # 默认的短信模板ID，例如验证码模板
        self.template_ids = {
            "verification_code": os.getenv("TENCENT_SMS_TEMPLATE_ID_VERIFICATION", ""),
            "notification": os.getenv("TENCENT_SMS_TEMPLATE_ID_NOTIFICATION", "")
        }
        
        self._client = None
    
    def _get_client(self) -> sms_client.SmsClient:
        """获取或初始化SMS客户端"""
        if self._client is None:
            try:
                # 实例化认证对象
                cred = credential.Credential(self.secret_id, self.secret_key)
                
                # 实例化http选项
                http_profile = HttpProfile()
                http_profile.endpoint = "sms.tencentcloudapi.com"
                
                # 实例化client选项
                client_profile = ClientProfile()
                client_profile.httpProfile = http_profile
                
                # 实例化SMS客户端，使用指定地区
                self._client = sms_client.SmsClient(cred, self.region, client_profile)
            except Exception as e:
                logger.error(f"Failed to initialize Tencent SMS client: {str(e)}")
                raise
        
        return self._client
    
    def send_sms(self, 
                 phone_numbers: Union[str, List[str]], 
                 template_params: List[str],
                 template_id: str = None,
                 template_type: str = "verification_code") -> Tuple[bool, Dict]:
        """
        发送短信
        
        Args:
            phone_numbers: 手机号码，单个号码或号码列表
            template_params: 模板参数列表，例如['1234', '5'] 表示验证码1234，有效期5分钟
            template_id: 模板ID，如果为None则使用预设的模板
            template_type: 模板类型，默认为verification_code
        
        Returns:
            (是否成功, 响应数据)
        """
        if not template_id:
            template_id = self.template_ids.get(template_type, "")
            if not template_id:
                logger.error(f"No template ID found for type: {template_type}")
                return False, {"error": "Template ID not configured"}
        
        # 确保phone_numbers是列表
        if isinstance(phone_numbers, str):
            phone_numbers = [phone_numbers]
        
        # 为国内手机号添加+86前缀（如果没有）
        formatted_phones = []
        for phone in phone_numbers:
            if not phone.startswith("+"):
                phone = f"+86{phone}"
            formatted_phones.append(phone)
        
        try:
            # 构造请求对象
            req = models.SendSmsRequest()
            
            # 按照官方示例直接构造参数字典
            params = {
                "PhoneNumberSet": formatted_phones,
                "SmsSdkAppId": self.app_id,
                "SignName": self.sign_name,
                "TemplateId": template_id,
                "TemplateParamSet": template_params
            }
            
            # 使用官方示例一致的JSON处理方式
            req.from_json_string(json.dumps(params))
            
            # 发送请求
            client = self._get_client()
            response = client.SendSms(req)
            
            # 解析响应
            result = json.loads(response.to_json_string())
            
            # 检查发送状态
            send_status_set = result.get("SendStatusSet", [])
            all_success = all(item.get("Code") == "Ok" for item in send_status_set)
            
            if all_success:
                logger.info(f"SMS sent successfully to {formatted_phones}")
                return True, result
            else:
                failed_numbers = [item.get("PhoneNumber") for item in send_status_set if item.get("Code") != "Ok"]
                logger.warning(f"Failed to send SMS to {failed_numbers}: {result}")
                return False, result
                
        except TencentCloudSDKException as err:
            logger.error(f"Tencent Cloud SDK error: {str(err)}")
            return False, {"error": str(err)}
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {str(e)}")
            return False, {"error": str(e)}
    
    def send_verification_code(self, phone_number: str, code: str, expire_minutes: str = "5") -> Tuple[bool, Dict]:
        """
        发送验证码短信
        
        Args:
            phone_number: 手机号码
            code: 验证码
            expire_minutes: 过期时间（分钟），仅作为业务逻辑参数，不传递给模板
        
        Returns:
            (是否成功, 响应数据)
        """
        return self.send_sms(
            phone_number, 
            [code],
            template_type="verification_code"
        )
    
    def send_notification(self, phone_number: str, params: List[str]) -> Tuple[bool, Dict]:
        """
        发送通知短信
        
        Args:
            phone_number: 手机号码
            params: 模板参数列表
        
        Returns:
            (是否成功, 响应数据)
        """
        return self.send_sms(
            phone_number,
            params,
            template_type="notification"
        )

# 创建全局实例
tencent_sms_client = TencentSmsClient()
# -*- coding: utf-8 -*-

import json
import os
import logging
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

class SmsService:
    def __init__(self):
        """初始化短信服务
        从环境变量获取腾讯云认证信息
        """
        self.secret_id = os.getenv("TENCENT_SECRET_ID")
        self.secret_key = os.getenv("TENCENT_SECRET_KEY")
        self.sms_sdk_app_id = os.getenv("TENCENT_SMS_SDK_APP_ID")
        self.template_id = os.getenv("TENCENT_SMS_TEMPLATE_ID")
        self.sign_name = os.getenv("TENCENT_SMS_SIGN_NAME")
        self.region = os.getenv("TENCENT_REGION", "ap-beijing")
        
        if not all([self.secret_id, self.secret_key, self.sms_sdk_app_id, self.template_id, self.sign_name]):
            logger.warning("腾讯云SMS服务配置不完整，短信功能可能无法正常使用")
    
    def send_sms(self, phone_numbers, template_param_set):
        """发送短信
        
        Args:
            phone_numbers (list): 手机号码列表，例如 ["+8613711112222", "+8613833334444"]
            template_param_set (list): 模板参数列表，例如 ["123456", "5"] 表示验证码为123456，有效期5分钟
            
        Returns:
            dict: 发送结果
        """
        try:
            # 实例化认证对象
            cred = credential.Credential(self.secret_id, self.secret_key)
            
            # 实例化http选项
            http_profile = HttpProfile()
            http_profile.endpoint = "sms.tencentcloudapi.com"
            
            # 实例化client选项
            client_profile = ClientProfile()
            client_profile.httpProfile = http_profile
            
            # 实例化SMS客户端
            client = sms_client.SmsClient(cred, self.region, client_profile)
            
            # 实例化请求对象
            req = models.SendSmsRequest()
            
            # 构造请求参数
            params = {
                "PhoneNumberSet": phone_numbers,
                "SmsSdkAppId": self.sms_sdk_app_id,
                "SignName": self.sign_name,
                "TemplateId": self.template_id,
                "TemplateParamSet": template_param_set
            }
            
            req.from_json_string(json.dumps(params))
            
            # 发送请求并获取响应
            resp = client.SendSms(req)
            result = json.loads(resp.to_json_string())
            
            logger.info(f"短信发送结果: {result}")
            return result
            
        except TencentCloudSDKException as err:
            logger.error(f"短信发送失败: {err}")
            return {"error": str(err)}
        except Exception as e:
            logger.error(f"短信发送过程中发生未知错误: {e}")
            return {"error": str(e)}
    
    def send_verification_code(self, phone_number, code, expire_minutes=5):
        """发送验证码短信
        
        Args:
            phone_number (str): 手机号码，例如 "+8613711112222"
            code (str): 验证码，例如 "123456"
            expire_minutes (int): 验证码有效期，单位分钟
            
        Returns:
            dict: 发送结果
        """
        # 构造参数
        phone_numbers = [phone_number]
        template_param_set = [code, str(expire_minutes)]
        
        return self.send_sms(phone_numbers, template_param_set)

# 创建短信服务单例
sms_service = SmsService() 
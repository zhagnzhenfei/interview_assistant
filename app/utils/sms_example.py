"""
短信服务使用示例
"""

from utils.sms import sms_service

def example_send_verification_code():
    """
    发送验证码示例
    """
    # 发送验证码到指定手机号
    phone_number = "+8613800138000"  # 替换为实际手机号
    code = "123456"  # 验证码
    expire_minutes = 5  # 有效期（分钟）
    
    result = sms_service.send_verification_code(phone_number, code, expire_minutes)
    
    if "error" in result:
        print(f"发送失败: {result['error']}")
    else:
        print(f"发送成功: {result}")

def example_send_batch_sms():
    """
    批量发送短信示例
    """
    # 批量发送短信
    phone_numbers = ["+8613800138000", "+8613900139000"]  # 替换为实际手机号列表
    template_params = ["123456", "5"]  # 模板参数
    
    result = sms_service.send_sms(phone_numbers, template_params)
    
    if "error" in result:
        print(f"发送失败: {result['error']}")
    else:
        print(f"发送成功: {result}")

if __name__ == "__main__":
    # 使用前请确保已在环境变量中设置好腾讯云的配置信息
    # 可以通过修改 .env 文件添加以下配置:
    # TENCENT_SECRET_ID=your_secret_id_here
    # TENCENT_SECRET_KEY=your_secret_key_here
    # TENCENT_SMS_SDK_APP_ID=your_sms_sdk_app_id_here
    # TENCENT_SMS_TEMPLATE_ID=your_template_id_here
    # TENCENT_SMS_SIGN_NAME=your_sign_name_here
    # TENCENT_REGION=ap-beijing
    
    # 发送验证码示例
    example_send_verification_code()
    
    # 批量发送短信示例
    # example_send_batch_sms() 
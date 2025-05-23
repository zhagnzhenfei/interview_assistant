import pytest
import json
from unittest.mock import patch, MagicMock
from services.tencent_sms import TencentSmsClient

# 模拟腾讯云SMS客户端响应
class MockSendSmsResponse:
    def __init__(self, success=True, phone_numbers=None):
        self.success = success
        self.phone_numbers = phone_numbers or ["13800138000"]
        
    def to_json_string(self):
        if self.success:
            send_status = [{"Code": "Ok", "PhoneNumber": phone} for phone in self.phone_numbers]
        else:
            send_status = [{"Code": "Failed", "PhoneNumber": phone, "Message": "Mock failure"} for phone in self.phone_numbers]
        
        return json.dumps({
            "SendStatusSet": send_status
        })

@pytest.fixture
def mock_tencent_client():
    """创建一个带有测试配置的腾讯云SMS客户端"""
    client = TencentSmsClient()
    # 设置测试配置
    client.secret_id = "test_secret_id"
    client.secret_key = "test_secret_key"
    client.app_id = "test_app_id"
    client.sign_name = "测试签名"
    client.region = "ap-guangzhou"
    client.template_ids = {
        "verification_code": "1000000",
        "notification": "1000001"
    }
    return client

def test_init_client():
    """测试初始化客户端"""
    client = TencentSmsClient()
    assert client._client is None
    assert hasattr(client, 'secret_id')
    assert hasattr(client, 'secret_key')
    assert hasattr(client, 'app_id')
    assert hasattr(client, 'sign_name')
    assert hasattr(client, 'template_ids')

@patch('services.tencent_sms.sms_client.SmsClient')
@patch('services.tencent_sms.credential.Credential')
def test_get_client(mock_credential, mock_sms_client, mock_tencent_client):
    """测试获取SMS客户端实例"""
    # 设置模拟行为
    mock_cred_instance = MagicMock()
    mock_credential.return_value = mock_cred_instance
    mock_client_instance = MagicMock()
    mock_sms_client.return_value = mock_client_instance
    
    # 调用获取客户端方法
    client = mock_tencent_client._get_client()
    
    # 验证调用
    mock_credential.assert_called_once_with(
        mock_tencent_client.secret_id, 
        mock_tencent_client.secret_key
    )
    mock_sms_client.assert_called_once()
    assert client == mock_client_instance
    
    # 再次调用应该返回缓存的客户端
    mock_credential.reset_mock()
    mock_sms_client.reset_mock()
    
    client2 = mock_tencent_client._get_client()
    assert client2 == mock_client_instance
    mock_credential.assert_not_called()
    mock_sms_client.assert_not_called()

@patch('services.tencent_sms.sms_client.SmsClient.SendSms')
@patch('services.tencent_sms.models.SendSmsRequest')
def test_send_sms_success(mock_request, mock_send_sms, mock_tencent_client):
    """测试成功发送短信"""
    # 设置模拟行为
    mock_req_instance = MagicMock()
    mock_request.return_value = mock_req_instance
    mock_response = MockSendSmsResponse(success=True)
    mock_send_sms.return_value = mock_response
    
    # 调用发送短信方法
    success, result = mock_tencent_client.send_sms(
        "13800138000",
        ["1234", "5"],
        template_id="1000000"
    )
    
    # 验证结果
    assert success is True
    assert "SendStatusSet" in result
    mock_request.assert_called_once()
    mock_req_instance.from_json_string.assert_called_once()
    mock_send_sms.assert_called_once_with(mock_req_instance)

@patch('services.tencent_sms.sms_client.SmsClient.SendSms')
@patch('services.tencent_sms.models.SendSmsRequest')
def test_send_sms_failure(mock_request, mock_send_sms, mock_tencent_client):
    """测试发送短信失败"""
    # 设置模拟行为
    mock_req_instance = MagicMock()
    mock_request.return_value = mock_req_instance
    mock_response = MockSendSmsResponse(success=False)
    mock_send_sms.return_value = mock_response
    
    # 调用发送短信方法
    success, result = mock_tencent_client.send_sms(
        "13800138000",
        ["1234", "5"],
        template_id="1000000"
    )
    
    # 验证结果
    assert success is False
    assert "SendStatusSet" in result
    mock_request.assert_called_once()
    mock_req_instance.from_json_string.assert_called_once()
    mock_send_sms.assert_called_once_with(mock_req_instance)

@patch('services.tencent_sms.sms_client.SmsClient.SendSms')
def test_send_sms_exception(mock_send_sms, mock_tencent_client):
    """测试发送短信异常"""
    # 设置模拟行为
    from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
    mock_send_sms.side_effect = TencentCloudSDKException("RequestId", "模拟异常")
    
    # 调用发送短信方法
    success, result = mock_tencent_client.send_sms(
        "13800138000",
        ["1234", "5"],
        template_id="1000000"
    )
    
    # 验证结果
    assert success is False
    assert "error" in result
    assert "模拟异常" in result["error"]

@patch('services.tencent_sms.TencentSmsClient.send_sms')
def test_send_verification_code(mock_send_sms, mock_tencent_client):
    """测试发送验证码"""
    # 设置模拟行为
    mock_send_sms.return_value = (True, {"SendStatusSet": [{"Code": "Ok"}]})
    
    # 调用发送验证码方法
    success, result = mock_tencent_client.send_verification_code("13800138000", "1234")
    
    # 验证结果
    assert success is True
    mock_send_sms.assert_called_once_with(
        "13800138000",
        ["1234", "5"],
        template_type="verification_code"
    )

@patch('services.tencent_sms.TencentSmsClient.send_sms')
def test_phone_number_formatting(mock_send_sms, mock_tencent_client):
    """测试手机号格式化"""
    # 设置模拟行为
    mock_send_sms.return_value = (True, {})
    
    # 测试不同格式的手机号
    mock_tencent_client.send_verification_code("13800138000", "1234")  # 不带前缀
    args, kwargs = mock_send_sms.call_args
    assert "+86" in kwargs.get("phone_numbers", [""])[0]
    
    mock_send_sms.reset_mock()
    mock_tencent_client.send_verification_code("+8613800138000", "1234")  # 带前缀
    args, kwargs = mock_send_sms.call_args
    assert kwargs.get("phone_numbers", [""])[0] == "+8613800138000"

# 运行测试
if __name__ == "__main__":
    pytest.main(["-xvs", "test_tencent_sms.py"]) 
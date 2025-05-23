import base64
import time
import random
import string
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv
load_dotenv()

class WxPaySign:
    def __init__(self, mch_id: str = None, private_key_path: str = None, cert_serial_no: str = None):
        """
        初始化微信支付签名工具类
        
        Args:
            mch_id: 商户号，如果为None则从环境变量获取
            private_key_path: 商户私钥文件路径，如果为None则从环境变量获取
            cert_serial_no: 证书序列号，如果为None则从环境变量获取
        """
        self.mch_id = mch_id or os.getenv('WXPAY_MCH_ID')
        self.cert_serial_no = cert_serial_no or os.getenv('WXPAY_CERT_SERIAL_NO')
        private_key_path = private_key_path or os.getenv('WXPAY_PRIVATE_KEY_PATH')
        
        if not all([self.mch_id, private_key_path, self.cert_serial_no]):
            raise ValueError("Missing required environment variables: WXPAY_MCH_ID, WXPAY_PRIVATE_KEY_PATH, WXPAY_CERT_SERIAL_NO")
        
        # 读取私钥文件
        try:
            with open(private_key_path, 'rb') as f:
                key_data = f.read()
                
            # 尝试加载 PKCS#1 格式的私钥
            try:
                self.private_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
            except ValueError as e:
                # 如果失败，尝试转换为 PKCS#8 格式
                try:
                    # 读取 PKCS#1 格式的私钥
                    private_key = serialization.load_pem_private_key(
                        key_data,
                        password=None,
                        backend=default_backend()
                    )
                    # 转换为 PKCS#8 格式
                    pkcs8_key = private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    )
                    # 加载 PKCS#8 格式的私钥
                    self.private_key = serialization.load_pem_private_key(
                        pkcs8_key,
                        password=None,
                        backend=default_backend()
                    )
                except Exception as e:
                    raise ValueError(f"Failed to load private key: {str(e)}. Please ensure the key is in correct PEM format.")
                    
        except FileNotFoundError:
            raise FileNotFoundError(f"Private key file not found: {private_key_path}")
        except Exception as e:
            raise Exception(f"Error loading private key: {str(e)}")
    
    def generate_nonce_str(self, length: int = 32) -> str:
        """生成随机字符串"""
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def sign(self, message: str) -> str:
        """
        使用SHA256 with RSA签名
        
        Args:
            message: 待签名字符串
            
        Returns:
            Base64编码的签名值
        """
        try:
            signature = self.private_key.sign(
                message.encode('utf-8'),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            raise Exception(f"Error signing message: {str(e)}")
    
    def generate_authorization(self, method: str, url: str, body: str = '') -> str:
        """
        生成微信支付API v3的Authorization头
        
        Args:
            method: HTTP请求方法（GET, POST等）
            url: 请求URL（不包含域名）
            body: 请求体（POST请求时需要）
            
        Returns:
            Authorization头的值
        """
        timestamp = str(int(time.time()))
        nonce_str = self.generate_nonce_str()
        
        # 构造签名串
        sign_str = f"{method}\n{url}\n{timestamp}\n{nonce_str}\n{body}\n"
        
        # 计算签名值
        signature = self.sign(sign_str)
        
        # 构造Authorization头
        auth = f'WECHATPAY2-SHA256-RSA2048 mchid="{self.mch_id}",nonce_str="{nonce_str}",signature="{signature}",timestamp="{timestamp}",serial_no="{self.cert_serial_no}"'
        
        return auth
    
    def generate_jsapi_sign(self, app_id: str = None, prepay_id: str = None) -> dict:
        """
        生成JSAPI调起支付的签名
        
        Args:
            app_id: 小程序/公众号的appid，如果为None则从环境变量获取
            prepay_id: 预支付交易会话标识
            
        Returns:
            包含所有必要参数的字典
        """
        app_id = app_id or os.getenv('WXPAY_APP_ID')
        if not app_id:
            raise ValueError("Missing required environment variable: WXPAY_APP_ID")
        if not prepay_id:
            raise ValueError("prepay_id is required")
            
        timestamp = str(int(time.time()))
        nonce_str = self.generate_nonce_str()
        
        # 构造签名串
        sign_str = f"{app_id}\n{timestamp}\n{nonce_str}\nprepay_id={prepay_id}\n"
        
        # 计算签名值
        pay_sign = self.sign(sign_str)
        
        return {
            "appId": app_id,
            "timeStamp": timestamp,
            "nonceStr": nonce_str,
            "package": f"prepay_id={prepay_id}",
            "signType": "RSA",
            "paySign": pay_sign
        }

if __name__ == "__main__":
    # 测试代码
    wxpay = WxPaySign()
    
    # 测试生成Authorization头
    method = "POST"
    url = "/v3/pay/transactions/jsapi"
    body = '{"appid":"wxd678efh567hg6787","mchid":"1900007291","description":"Image形象店-深圳腾大-QQ公仔","out_trade_no":"1217752501201407033233368018","notify_url":"https://www.weixin.qq.com/wxpay/pay.php","amount":{"total":100,"currency":"CNY"},"payer":{"openid":"oUpF8uMuAJO_M2pxb1Q9zNjWeS6o"}}'
    
    auth = wxpay.generate_authorization(method, url, body)
    print("Authorization:", auth) 
import os
import json
import time
from utils.wxpay import WxPaySign
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_jsapi_pay():
    """测试JSAPI支付签名"""
    wxpay = WxPaySign()
    
    # 从环境变量获取appid
    app_id = os.getenv('WXPAY_APP_ID')
    if not app_id:
        print("Error: WXPAY_APP_ID not found in environment variables")
        return
        
    # 测试用的prepay_id（实际使用时需要从统一下单接口获取）
    prepay_id = "wx201410272009395522657a690389285100"
    
    # 生成调起支付参数
    pay_params = wxpay.generate_jsapi_sign(app_id=app_id, prepay_id=prepay_id)
    
    print("\n=== JSAPI支付参数 ===")
    print(json.dumps(pay_params, indent=2, ensure_ascii=False))

def test_api_request():
    """测试API请求签名"""
    wxpay = WxPaySign()
    
    # 测试统一下单接口
    method = "POST"
    url = "/v3/pay/transactions/jsapi"
    body = {
        "appid": os.getenv('WXPAY_APP_ID'),
        "mchid": os.getenv('WXPAY_MCH_ID'),
        "description": "测试商品",
        "out_trade_no": "TEST" + str(int(time.time())),
        "notify_url": "https://www.weixin.qq.com/wxpay/pay.php",
        "amount": {
            "total": 100,
            "currency": "CNY"
        },
        "payer": {
            "openid": "oUpF8uMuAJO_M2pxb1Q9zNjWeS6o"
        }
    }
    
    # 生成Authorization头
    auth = wxpay.generate_authorization(
        method=method,
        url=url,
        body=json.dumps(body)
    )
    
    print("\n=== API请求签名 ===")
    print("Method:", method)
    print("URL:", url)
    print("Body:", json.dumps(body, indent=2, ensure_ascii=False))
    print("Authorization:", auth)

if __name__ == "__main__":
    # 检查必要的环境变量
    required_vars = ['WXPAY_MCH_ID', 'WXPAY_PRIVATE_KEY_PATH', 'WXPAY_CERT_SERIAL_NO', 'WXPAY_APP_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Error: Missing required environment variables:", missing_vars)
        print("Please set these variables in your .env file")
    else:
        print("=== 环境变量检查通过 ===")
        print("商户号:", os.getenv('WXPAY_MCH_ID'))
        print("证书序列号:", os.getenv('WXPAY_CERT_SERIAL_NO'))
        print("AppID:", os.getenv('WXPAY_APP_ID'))
        print("私钥路径:", os.getenv('WXPAY_PRIVATE_KEY_PATH'))
        
        # 运行测试
        test_jsapi_pay()
        test_api_request() 
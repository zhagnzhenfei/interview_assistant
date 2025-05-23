from utils.wxpay import WxPaySign

# 方式1：使用环境变量
wxpay = WxPaySign()

# 生成签名
params = wxpay.generate_jsapi_sign(prepay_id='wx201410272009395522657a690389285100')
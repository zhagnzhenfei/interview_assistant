from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class GoodsDetail(BaseModel):
    merchant_goods_id: str
    wechatpay_goods_id: Optional[str] = None
    goods_name: str
    quantity: int
    unit_price: int

class Detail(BaseModel):
    cost_price: Optional[int] = None
    invoice_id: Optional[str] = None
    goods_detail: Optional[List[GoodsDetail]] = None

class StoreInfo(BaseModel):
    id: str
    name: str
    area_code: str
    address: str

class SceneInfo(BaseModel):
    payer_client_ip: str
    device_id: Optional[str] = None
    store_info: Optional[StoreInfo] = None

class SettleInfo(BaseModel):
    profit_sharing: bool = False

class PaymentRequest(BaseModel):
    description: str
    out_trade_no: str
    time_expire: Optional[str] = None
    attach: Optional[str] = None
    notify_url: str
    goods_tag: Optional[str] = None
    support_fapiao: Optional[bool] = False
    amount: dict
    payer: dict
    detail: Optional[Detail] = None
    scene_info: Optional[SceneInfo] = None
    settle_info: Optional[SettleInfo] = None

class OrderAmount(BaseModel):
    """订单金额信息"""
    total: int  # 订单总金额，单位为分
    payer_total: Optional[int] = None  # 用户支付金额
    currency: str = "CNY"  # 货币类型
    payer_currency: Optional[str] = None  # 用户支付币种

class OrderPayer(BaseModel):
    """支付者信息"""
    openid: str  # 用户在商户appid下的唯一标识

class OrderPromotionDetail(BaseModel):
    """优惠功能"""
    coupon_id: str  # 券ID
    name: str  # 优惠名称
    scope: str  # 优惠范围
    type: str  # 优惠类型
    amount: int  # 优惠券面额
    stock_id: str  # 活动ID
    wechatpay_contribute: int  # 微信出资
    merchant_contribute: int  # 商户出资
    other_contribute: int  # 其他出资
    currency: str  # 优惠币种
    goods_detail: Optional[List[dict]] = None  # 单品列表

class OrderQueryResponse(BaseModel):
    """订单查询响应"""
    appid: str  # 公众账号ID
    mchid: str  # 商户号
    out_trade_no: str  # 商户订单号
    transaction_id: str  # 微信支付订单号
    trade_type: str  # 交易类型
    trade_state: str  # 交易状态
    trade_state_desc: str  # 交易状态描述
    bank_type: Optional[str] = None  # 银行类型
    attach: Optional[str] = None  # 商户数据包
    success_time: Optional[str] = None  # 支付完成时间
    payer: Optional[OrderPayer] = None  # 支付者信息
    amount: Optional[OrderAmount] = None  # 订单金额信息
    scene_info: Optional[dict] = None  # 场景信息
    promotion_detail: Optional[List[OrderPromotionDetail]] = None  # 优惠功能

class CloseOrderRequest(BaseModel):
    """关闭订单请求"""
    mchid: str  # 商户号

class RefundGoodsDetail(BaseModel):
    """退款商品信息"""
    merchant_goods_id: str  # 商户侧商品编码
    wechatpay_goods_id: Optional[str] = None  # 微信侧商品编码
    goods_name: str  # 商品名称
    unit_price: int  # 商品单价
    refund_amount: int  # 商品退款金额
    refund_quantity: int  # 商品退货数量

class RefundAmount(BaseModel):
    """退款金额信息"""
    refund: int  # 退款金额
    total: int  # 原订单金额
    currency: str = "CNY"  # 退款币种
    from_account: Optional[List[dict]] = None  # 退款出资账户及金额

class RefundRequest(BaseModel):
    """退款请求"""
    transaction_id: Optional[str] = None  # 微信支付订单号
    out_trade_no: Optional[str] = None  # 商户订单号
    out_refund_no: str  # 商户退款单号
    reason: Optional[str] = None  # 退款原因
    notify_url: Optional[str] = None  # 退款结果回调url
    funds_account: Optional[str] = None  # 退款资金来源
    amount: RefundAmount  # 退款金额信息
    goods_detail: Optional[List[RefundGoodsDetail]] = None  # 退款商品信息

class RefundResponse(BaseModel):
    """退款响应"""
    refund_id: str  # 微信支付退款单号
    out_refund_no: str  # 商户退款单号
    transaction_id: str  # 微信支付订单号
    out_trade_no: str  # 商户订单号
    channel: str  # 退款渠道
    user_received_account: str  # 退款入账账户
    success_time: Optional[str] = None  # 退款成功时间
    create_time: str  # 退款创建时间
    status: str  # 退款状态
    funds_account: Optional[str] = None  # 资金账户
    amount: dict  # 金额信息
    promotion_detail: Optional[List[dict]] = None  # 优惠退款信息

class AbnormalRefundRequest(BaseModel):
    """异常退款请求"""
    out_refund_no: str  # 商户退款单号
    type: str  # 异常退款处理方式：USER_BANK_CARD-退款到用户银行卡，MERCHANT_BANK_CARD-退款至交易商户银行账户
    bank_type: Optional[str] = None  # 开户银行，退款至用户银行卡时必填
    bank_account: Optional[str] = None  # 收款银行卡号，退款至用户银行卡时必填
    real_name: Optional[str] = None  # 收款用户姓名，退款至用户银行卡时必填

class TradeBillResponse(BaseModel):
    """交易账单响应"""
    hash_type: str  # 哈希类型，固定为SHA1
    hash_value: str  # 账单文件的SHA1摘要值
    download_url: str  # 下载地址，5min内有效

class FundFlowBillResponse(BaseModel):
    """资金账单响应"""
    hash_type: str  # 哈希类型，固定为SHA1
    hash_value: str  # 账单文件的SHA1摘要值
    download_url: str  # 下载地址，5min内有效 
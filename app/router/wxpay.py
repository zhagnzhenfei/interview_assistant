from fastapi import APIRouter, HTTPException, Request, Query, Response, Depends, Security
from pydantic import BaseModel
from typing import Optional, List
from utils.wxpay import WxPaySign
import httpx
import os
from dotenv import load_dotenv
from app.schemas.wxpay import (
    PaymentRequest, 
    OrderQueryResponse, 
    CloseOrderRequest,
    RefundRequest,
    RefundResponse,
    AbnormalRefundRequest,
    TradeBillResponse,
    FundFlowBillResponse
)
from services.auth import access_security
from fastapi_jwt import JwtAuthorizationCredentials
from sqlalchemy.orm import Session
from utils.database import get_db
from models.account import Account
from models.transaction import Transaction
from services.order import get_order_by_number
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

router = APIRouter(prefix="/wxpay", tags=["微信支付"])

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

@router.post("/transactions/jsapi")
async def create_jsapi_order(
    request: PaymentRequest,
    db: Session = Depends(get_db),
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    """
    创建JSAPI/小程序支付订单
    """
    try:
        # 验证用户身份
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 获取商户配置
        mch_id = os.getenv('WXPAY_MCH_ID')
        app_id = os.getenv('WXPAY_APP_ID')
        
        if not mch_id or not app_id:
            raise HTTPException(status_code=500, detail="商户配置信息不完整")

        # 构建请求体
        body = {
            "appid": app_id,
            "mchid": mch_id,
            **request.dict(exclude_none=True)
        }

        # 生成签名
        wxpay = WxPaySign()
        method = "POST"
        url = "/v3/pay/transactions/jsapi"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=body
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi",
                json=body,
                headers={
                    "Authorization": auth,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            result = response.json()
            
            # 生成调起支付的参数
            pay_params = wxpay.generate_jsapi_sign(
                app_id=app_id,
                prepay_id=result["prepay_id"]
            )

            return {
                "code": 0,
                "message": "success",
                "data": {
                    "prepay_id": result["prepay_id"],
                    "pay_params": pay_params
                }
            }

    except Exception as e:
        logger.error(f"Error creating jsapi order: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notify")
async def pay_notify(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    支付结果通知
    """
    try:
        # 获取通知数据
        data = await request.body()
        
        # 验证签名
        wxpay = WxPaySign()
        if not wxpay.verify_notify_signature(data, request.headers):
            raise HTTPException(status_code=400, detail="Invalid signature")

        # 解密通知数据
        notify_data = wxpay.decrypt_notify_data(data)
        
        # 处理支付结果
        if notify_data.get("trade_state") == "SUCCESS":
            # 获取订单信息
            order_number = notify_data.get("out_trade_no")
            order = await get_order_by_number(db, order_number)
            
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            
            # 更新订单状态
            order.status = "paid"
            order.paid_at = datetime.utcnow()
            
            # 增加用户账户余额
            account = db.query(Account).filter(Account.user_id == order.user_id).first()
            if account:
                account.balance += order.amount
                db.add(account)
            
            # 创建交易记录
            transaction = Transaction(
                account_id=account.id,
                amount=order.amount,
                transaction_type="充值",
                balance_after=account.balance,
                description=f"微信支付充值 - 订单号: {order_number}"
            )
            db.add(transaction)
            
            db.commit()
            
            return {"code": "SUCCESS", "message": "OK"}
        else:
            return {"code": "FAIL", "message": "支付未完成"}

    except Exception as e:
        logger.error(f"Error processing payment notification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/id/{transaction_id}", response_model=OrderQueryResponse)
async def query_order_by_transaction_id(
    transaction_id: str,
    db: Session = Depends(get_db),
    credentials: JwtAuthorizationCredentials = Security(access_security)
):
    """
    根据微信支付订单号查询订单
    """
    try:
        # 验证用户身份
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        mch_id = os.getenv('WXPAY_MCH_ID')
        if not mch_id:
            raise HTTPException(status_code=500, detail="商户配置信息不完整")

        # 生成签名
        wxpay = WxPaySign()
        method = "GET"
        url = f"/v3/pay/transactions/id/{transaction_id}"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=""  # GET请求没有请求体
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.mch.weixin.qq.com/v3/pay/transactions/id/{transaction_id}",
                params={"mchid": mch_id},
                headers={
                    "Authorization": auth,
                    "Accept": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/out-trade-no/{out_trade_no}", response_model=OrderQueryResponse)
async def query_order_by_out_trade_no(out_trade_no: str):
    """
    根据商户订单号查询订单
    """
    try:
        mch_id = os.getenv('WXPAY_MCH_ID')
        if not mch_id:
            raise HTTPException(status_code=500, detail="商户配置信息不完整")

        # 生成签名
        wxpay = WxPaySign()
        method = "GET"
        url = f"/v3/pay/transactions/out-trade-no/{out_trade_no}"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=""  # GET请求没有请求体
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.mch.weixin.qq.com/v3/pay/transactions/out-trade-no/{out_trade_no}",
                params={"mchid": mch_id},
                headers={
                    "Authorization": auth,
                    "Accept": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transactions/out-trade-no/{out_trade_no}/close")
async def close_order(out_trade_no: str, request: CloseOrderRequest):
    """
    关闭订单
    """
    try:
        mch_id = os.getenv('WXPAY_MCH_ID')
        if not mch_id:
            raise HTTPException(status_code=500, detail="商户配置信息不完整")

        # 验证商户号
        if request.mchid != mch_id:
            raise HTTPException(status_code=400, detail="商户号不匹配")

        # 生成签名
        wxpay = WxPaySign()
        method = "POST"
        url = f"/v3/pay/transactions/out-trade-no/{out_trade_no}/close"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=request.json()
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.mch.weixin.qq.com/v3/pay/transactions/out-trade-no/{out_trade_no}/close",
                json=request.dict(),
                headers={
                    "Authorization": auth,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 204:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return {"code": 0, "message": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refund/domestic/refunds", response_model=RefundResponse)
async def create_refund(request: RefundRequest):
    """
    申请退款
    """
    try:
        # 验证必填参数
        if not request.transaction_id and not request.out_trade_no:
            raise HTTPException(status_code=400, detail="transaction_id和out_trade_no必须二选一")

        # 生成签名
        wxpay = WxPaySign()
        method = "POST"
        url = "/v3/refund/domestic/refunds"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=request.json()
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mch.weixin.qq.com/v3/refund/domestic/refunds",
                json=request.dict(),
                headers={
                    "Authorization": auth,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/refund/domestic/refunds/{out_refund_no}", response_model=RefundResponse)
async def query_refund(out_refund_no: str):
    """
    查询单笔退款
    """
    try:
        # 生成签名
        wxpay = WxPaySign()
        method = "GET"
        url = f"/v3/refund/domestic/refunds/{out_refund_no}"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=""  # GET请求没有请求体
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.mch.weixin.qq.com/v3/refund/domestic/refunds/{out_refund_no}",
                headers={
                    "Authorization": auth,
                    "Accept": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refund/domestic/refunds/{refund_id}/apply-abnormal-refund", response_model=RefundResponse)
async def apply_abnormal_refund(refund_id: str, request: AbnormalRefundRequest):
    """
    发起异常退款
    """
    try:
        # 验证必填参数
        if request.type == "USER_BANK_CARD":
            if not request.bank_type or not request.bank_account or not request.real_name:
                raise HTTPException(status_code=400, detail="退款至用户银行卡时，银行类型、银行卡号和用户姓名为必填项")

        # 生成签名
        wxpay = WxPaySign()
        method = "POST"
        url = f"/v3/refund/domestic/refunds/{refund_id}/apply-abnormal-refund"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=request.json()
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.mch.weixin.qq.com/v3/refund/domestic/refunds/{refund_id}/apply-abnormal-refund",
                json=request.dict(),
                headers={
                    "Authorization": auth,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Wechatpay-Serial": os.getenv('WXPAY_CERT_SERIAL_NO', '')  # 添加证书序列号
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bill/tradebill", response_model=TradeBillResponse)
async def get_trade_bill(
    bill_date: str = Query(..., description="账单日期，格式yyyy-MM-DD"),
    bill_type: str = Query("ALL", description="账单类型：ALL-所有订单，SUCCESS-成功支付的订单，REFUND-退款订单"),
    tar_type: Optional[str] = Query(None, description="压缩类型：GZIP-返回.gzip格式的压缩文件")
):
    """
    申请交易账单
    """
    try:
        # 验证账单类型
        if bill_type not in ["ALL", "SUCCESS", "REFUND"]:
            raise HTTPException(status_code=400, detail="无效的账单类型")

        # 验证压缩类型
        if tar_type and tar_type != "GZIP":
            raise HTTPException(status_code=400, detail="无效的压缩类型")

        # 构建查询参数
        params = {"bill_date": bill_date, "bill_type": bill_type}
        if tar_type:
            params["tar_type"] = tar_type

        # 生成签名
        wxpay = WxPaySign()
        method = "GET"
        url = "/v3/bill/tradebill"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=""  # GET请求没有请求体
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.mch.weixin.qq.com/v3/bill/tradebill",
                params=params,
                headers={
                    "Authorization": auth,
                    "Accept": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bill/fundflowbill", response_model=FundFlowBillResponse)
async def get_fund_flow_bill(
    bill_date: str = Query(..., description="账单日期，格式yyyy-MM-DD"),
    account_type: str = Query("BASIC", description="资金账户类型：BASIC-基本账户，OPERATION-运营账户，FEES-手续费账户"),
    tar_type: Optional[str] = Query(None, description="压缩类型：GZIP-返回.gzip格式的压缩文件")
):
    """
    申请资金账单
    """
    try:
        # 验证账户类型
        if account_type not in ["BASIC", "OPERATION", "FEES"]:
            raise HTTPException(status_code=400, detail="无效的资金账户类型")

        # 验证压缩类型
        if tar_type and tar_type != "GZIP":
            raise HTTPException(status_code=400, detail="无效的压缩类型")

        # 构建查询参数
        params = {"bill_date": bill_date, "account_type": account_type}
        if tar_type:
            params["tar_type"] = tar_type

        # 生成签名
        wxpay = WxPaySign()
        method = "GET"
        url = "/v3/bill/fundflowbill"
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=""  # GET请求没有请求体
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.mch.weixin.qq.com/v3/bill/fundflowbill",
                params=params,
                headers={
                    "Authorization": auth,
                    "Accept": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bill/download")
async def download_bill(download_url: str):
    """
    下载账单文件
    """
    try:
        # 生成签名
        wxpay = WxPaySign()
        method = "GET"
        url = download_url.replace("https://api.mch.weixin.qq.com", "")  # 移除域名部分
        
        # 生成Authorization头
        auth = wxpay.generate_authorization(
            method=method,
            url=url,
            body=""  # GET请求没有请求体
        )

        # 发送请求到微信支付API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                download_url,
                headers={
                    "Authorization": auth,
                    "Accept": "application/json"
                }
            )

            if response.status_code != 200:
                error_detail = response.json()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"微信支付接口调用失败: {error_detail}"
                )

            # 获取响应头中的Content-Type
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            
            # 返回文件内容
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f"attachment; filename=bill_{os.path.basename(download_url)}"
                }
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
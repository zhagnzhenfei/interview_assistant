from fastapi import APIRouter, HTTPException, Security
from schemas.accounts_schemas import RechargeRequest, DeductRequest, TransactionResponse
from services.accounts import update_balance, get_balance_by_user_id, list_transactions
from fastapi_jwt import JwtAuthorizationCredentials
from services.auth import access_security
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

################
# 充值
################
@router.post("/accounts/recharge")
def recharge(request: RechargeRequest,
             credentials: JwtAuthorizationCredentials = Security(access_security),
             ):

    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        new_balance = update_balance(
            user_id=user_id,
            amount=abs(request.amount),  # 确保正数
            trans_type="充值",
            desc=request.description
        )
        return {"success": True, "msg": "充值成功", "balance": new_balance}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器错误")

################
# 扣费
################
@router.post("/accounts/deduct")
def deduct(request: DeductRequest,
           credentials: JwtAuthorizationCredentials = Security(access_security),
           ):
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        new_balance = update_balance(
            user_id=user_id,
            amount=-abs(request.amount),  # 确保负数
            trans_type="扣费",
            desc=request.description
        )
        return {"success": True, "msg": "支付成功", "balance": new_balance}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器错误")


################
# 查询账号余额
################
@router.get("/accounts/balance")
def get_balance(credentials: JwtAuthorizationCredentials = Security(access_security),):
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        return get_balance_by_user_id(user_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="服务器错误")


################
# 查询交易记录
################

@router.get("/accounts/transactions")
def get_transactions(
    page: int = 1,
    page_size: int = 10,
    credentials: JwtAuthorizationCredentials = Security(access_security),
):
    logger.info(
        f"开始查询交易记录 | 用户：{credentials.subject.get('user_id')} | 页码：{page} | 每页大小：{page_size}"
    )
    try:
        user_id = str(credentials.subject.get("user_id"))
        if not user_id:
            logger.warning("未获取到用户ID | 认证信息无效")
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")

        # 参数校验
        if page < 1 or page_size < 1 or page_size > 100:
            logger.warning(f"无效的分页参数 | 页码：{page} | 每页大小：{page_size}")
            raise HTTPException(status_code=400, detail="无效的分页参数")

        logger.debug(f"查询交易记录 | 用户：{user_id} | 页码：{page} | 每页大小：{page_size}")
        transactions = list_transactions(user_id, page, page_size)

        logger.info(f"成功查询到交易记录 | 用户：{user_id} | 记录数：{len(transactions)}")
        return [TransactionResponse(**t.__dict__) for t in transactions]

    except HTTPException as e:
        logger.warning(f"业务异常 | 状态码：{e.status_code} | 详情：{e.detail}")
        raise
    except Exception as e:
        logger.error(
            f"查询交易记录失败 | 错误类型：{type(e).__name__} | 详情：{str(e)}",
            exc_info=True
        )
        raise HTTPException(status_code=500, detail="服务器错误")
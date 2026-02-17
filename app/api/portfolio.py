"""
投资组合 API 路由

提供投资组合管理、持仓管理、交易记录和收益分析接口。
"""
from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.portfolio_service import PortfolioService
from app.db.database import session_scope
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# 请求/响应模型
# ============================================

class PortfolioCreate(BaseModel):
    """创建投资组合请求"""
    name: str
    description: Optional[str] = None
    initial_capital: float
    user_id: Optional[int] = None


class PortfolioUpdate(BaseModel):
    """更新投资组合请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class PortfolioResponse(BaseModel):
    """投资组合响应"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    initial_capital: float
    current_value: float
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PositionResponse(BaseModel):
    """持仓响应"""
    id: int
    stock_code: str
    stock_name: Optional[str]
    position_type: str
    quantity: float
    cost_price: float
    current_price: Optional[float]
    total_cost: float
    market_value: Optional[float]
    profit_loss: Optional[float]
    profit_loss_pct: Optional[float]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PositionUpdate(BaseModel):
    """更新持仓请求"""
    current_price: float


class TransactionCreate(BaseModel):
    """创建交易记录请求"""
    stock_code: str
    stock_name: Optional[str] = None
    transaction_type: str
    quantity: float
    price: float
    trade_date: Optional[str] = None
    commission: float = 0.0
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    """交易记录响应"""
    id: int
    stock_code: str
    stock_name: Optional[str]
    transaction_type: str
    quantity: float
    price: float
    amount: float
    commission: float
    trade_date: str
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class PortfolioHistoryResponse(BaseModel):
    """投资组合历史记录响应"""
    id: int
    total_value: float
    cash_balance: float
    position_value: float
    total_cost: float
    profit_loss: float
    profit_loss_pct: float
    record_date: str
    created_at: str

    class Config:
        from_attributes = True


class ReturnsResponse(BaseModel):
    """收益响应"""
    initial_capital: float
    current_value: float
    cash_balance: float
    position_value: float
    total_cost: float
    profit_loss: float
    profit_loss_pct: float


class PortfolioReportResponse(BaseModel):
    """投资组合分析报告响应"""
    portfolio: Dict[str, Any]
    returns: Dict[str, Any]
    positions: List[Dict[str, Any]]
    total_positions: int
    history_count: int


# ============================================
# 依赖函数
# ============================================

async def get_portfolio_service_dep(db: AsyncSession = Depends(get_db)) -> PortfolioService:
    """获取投资组合服务实例"""
    return PortfolioService(db)


# ============================================
# 投资组合 API 端点
# ============================================

@router.post("", response_model=PortfolioResponse)
async def create_portfolio(
    portfolio: PortfolioCreate,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    创建投资组合
    """
    try:
        new_portfolio = await service.create_portfolio(
            user_id=portfolio.user_id or 1,  # 默认用户ID
            name=portfolio.name,
            description=portfolio.description,
            initial_capital=portfolio.initial_capital,
        )
        return PortfolioResponse(
            id=new_portfolio.id,
            user_id=new_portfolio.user_id,
            name=new_portfolio.name,
            description=new_portfolio.description,
            initial_capital=new_portfolio.initial_capital,
            current_value=new_portfolio.current_value,
            status=new_portfolio.status,
            created_at=new_portfolio.created_at.isoformat(),
            updated_at=new_portfolio.updated_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"创建投资组合失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建投资组合失败: {str(e)}")


@router.get("", response_model=List[PortfolioResponse])
async def get_portfolios(
    status: Optional[str] = Query(None, description="状态过滤"),
    user_id: Optional[int] = Query(None, description="用户ID"),
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    获取用户的所有投资组合
    """
    try:
        portfolios = await service.get_user_portfolios(
            user_id=user_id or 1,  # 默认用户ID
            status=status,
        )
        return [
            PortfolioResponse(
                id=p.id,
                user_id=p.user_id,
                name=p.name,
                description=p.description,
                initial_capital=p.initial_capital,
                current_value=p.current_value,
                status=p.status,
                created_at=p.created_at.isoformat(),
                updated_at=p.updated_at.isoformat(),
            )
            for p in portfolios
        ]
    except Exception as e:
        logger.error(f"获取投资组合列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取投资组合列表失败: {str(e)}")


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    user_id: Optional[int] = Query(None, description="用户ID"),
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    获取投资组合详情
    """
    portfolio = await service.get_portfolio(
        portfolio_id=portfolio_id,
        user_id=user_id or 1,
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    return PortfolioResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        description=portfolio.description,
        initial_capital=portfolio.initial_capital,
        current_value=portfolio.current_value,
        status=portfolio.status,
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
    )


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    portfolio_update: PortfolioUpdate,
    user_id: Optional[int] = Query(None, description="用户ID"),
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    更新投资组合
    """
    portfolio = await service.update_portfolio(
        portfolio_id=portfolio_id,
        user_id=user_id or 1,
        name=portfolio_update.name,
        description=portfolio_update.description,
        status=portfolio_update.status,
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    return PortfolioResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        description=portfolio.description,
        initial_capital=portfolio.initial_capital,
        current_value=portfolio.current_value,
        status=portfolio.status,
        created_at=portfolio.created_at.isoformat(),
        updated_at=portfolio.updated_at.isoformat(),
    )


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    user_id: Optional[int] = Query(None, description="用户ID"),
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    删除投资组合
    """
    success = await service.delete_portfolio(
        portfolio_id=portfolio_id,
        user_id=user_id or 1,
    )
    if not success:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    return {"message": "投资组合删除成功"}


# ============================================
# 持仓 API 端点
# ============================================

@router.get("/{portfolio_id}/positions", response_model=List[PositionResponse])
async def get_positions(
    portfolio_id: int,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    获取投资组合的所有持仓
    """
    positions = await service.get_portfolio_positions(portfolio_id)
    return [
        PositionResponse(
            id=p.id,
            stock_code=p.stock_code,
            stock_name=p.stock_name,
            position_type=p.position_type,
            quantity=p.quantity,
            cost_price=p.cost_price,
            current_price=p.current_price,
            total_cost=p.total_cost,
            market_value=p.market_value,
            profit_loss=p.profit_loss,
            profit_loss_pct=p.profit_loss_pct,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in positions
    ]


@router.put("/{portfolio_id}/positions/{stock_code}", response_model=PositionResponse)
async def update_position(
    portfolio_id: int,
    stock_code: str,
    position_update: PositionUpdate,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    更新持仓的当前价格
    """
    position = await service.get_position(portfolio_id, stock_code)
    if not position:
        raise HTTPException(status_code=404, detail="持仓不存在")

    position.current_price = position_update.current_price
    if position.quantity > 0:
        position.market_value = position.current_price * position.quantity
        position.profit_loss = position.market_value - position.total_cost
        position.profit_loss_pct = (position.profit_loss / position.total_cost * 100) if position.total_cost > 0 else 0

    await service.db.commit()
    await service.db.refresh(position)

    return PositionResponse(
        id=position.id,
        stock_code=position.stock_code,
        stock_name=position.stock_name,
        position_type=position.position_type,
        quantity=position.quantity,
        cost_price=position.cost_price,
        current_price=position.current_price,
        total_cost=position.total_cost,
        market_value=position.market_value,
        profit_loss=position.profit_loss,
        profit_loss_pct=position.profit_loss_pct,
        created_at=position.created_at.isoformat(),
        updated_at=position.updated_at.isoformat(),
    )


# ============================================
# 交易记录 API 端点
# ============================================

@router.post("/{portfolio_id}/transactions", response_model=TransactionResponse)
async def add_transaction(
    portfolio_id: int,
    transaction: TransactionCreate,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    添加交易记录
    """
    try:
        trade_date = transaction.trade_date or date.today().strftime("%Y-%m-%d")

        new_transaction = await service.add_transaction(
            portfolio_id=portfolio_id,
            stock_code=transaction.stock_code,
            stock_name=transaction.stock_name,
            transaction_type=transaction.transaction_type,
            quantity=transaction.quantity,
            price=transaction.price,
            trade_date=trade_date,
            commission=transaction.commission,
            notes=transaction.notes,
        )

        return TransactionResponse(
            id=new_transaction.id,
            stock_code=new_transaction.stock_code,
            stock_name=new_transaction.stock_name,
            transaction_type=new_transaction.transaction_type,
            quantity=new_transaction.quantity,
            price=new_transaction.price,
            amount=new_transaction.amount,
            commission=new_transaction.commission,
            trade_date=new_transaction.trade_date,
            notes=new_transaction.notes,
            created_at=new_transaction.created_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"添加交易记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加交易记录失败: {str(e)}")


@router.get("/{portfolio_id}/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    portfolio_id: int,
    stock_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    获取交易记录列表
    """
    transactions = await service.get_portfolio_transactions(
        portfolio_id=portfolio_id,
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        TransactionResponse(
            id=t.id,
            stock_code=t.stock_code,
            stock_name=t.stock_name,
            transaction_type=t.transaction_type,
            quantity=t.quantity,
            price=t.price,
            amount=t.amount,
            commission=t.commission,
            trade_date=t.trade_date,
            notes=t.notes,
            created_at=t.created_at.isoformat(),
        )
        for t in transactions
    ]


# ============================================
# 收益计算 API 端点
# ============================================

@router.get("/{portfolio_id}/returns", response_model=ReturnsResponse)
async def get_returns(
    portfolio_id: int,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    获取投资组合收益
    """
    returns = await service.calculate_returns(portfolio_id)
    if not returns:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    return ReturnsResponse(**returns)


@router.post("/{portfolio_id}/update-value")
async def update_portfolio_value(
    portfolio_id: int,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    更新投资组合价值
    """
    portfolio = await service.update_portfolio_value(portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    return {"message": "投资组合价值更新成功", "current_value": portfolio.current_value}


# ============================================
# 历史记录 API 端点
# ============================================

@router.get("/{portfolio_id}/history", response_model=List[PortfolioHistoryResponse])
async def get_portfolio_history(
    portfolio_id: int,
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    获取投资组合历史记录
    """
    history = await service.get_portfolio_history(
        portfolio_id=portfolio_id,
        start_date=start_date,
        end_date=end_date,
    )

    return [
        PortfolioHistoryResponse(
            id=h.id,
            total_value=h.total_value,
            cash_balance=h.cash_balance,
            position_value=h.position_value,
            total_cost=h.total_cost,
            profit_loss=h.profit_loss,
            profit_loss_pct=h.profit_loss_pct,
            record_date=h.record_date,
            created_at=h.created_at.isoformat(),
        )
        for h in history
    ]


@router.post("/{portfolio_id}/history")
async def add_portfolio_history(
    portfolio_id: int,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    添加投资组合历史快照
    """
    portfolio = await service.get_portfolio(portfolio_id, 0)
    if not portfolio:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    returns = await service.calculate_returns(portfolio_id)

    history = await service.add_history(
        portfolio_id=portfolio_id,
        total_value=returns.get("current_value", 0),
        cash_balance=returns.get("cash_balance", 0),
        position_value=returns.get("position_value", 0),
        total_cost=returns.get("total_cost", 0),
        profit_loss=returns.get("profit_loss", 0),
        profit_loss_pct=returns.get("profit_loss_pct", 0),
    )

    return {
        "message": "历史记录添加成功",
        "id": history.id,
        "record_date": history.record_date,
    }


# ============================================
# 分析报告 API 端点
# ============================================

@router.get("/{portfolio_id}/report", response_model=PortfolioReportResponse)
async def get_portfolio_report(
    portfolio_id: int,
    service: PortfolioService = Depends(get_portfolio_service_dep),
):
    """
    获取投资组合分析报告
    """
    report = await service.generate_portfolio_report(portfolio_id)
    if not report:
        raise HTTPException(status_code=404, detail="投资组合不存在")

    return PortfolioReportResponse(**report)

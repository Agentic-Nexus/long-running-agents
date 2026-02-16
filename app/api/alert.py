"""
预警 API 路由

提供预警规则管理和预警记录查询接口。
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.alert_service import get_alert_service
from app.db.database import session_scope
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ============================================
# 请求/响应模型
# ============================================

class AlertRuleCreate(BaseModel):
    """创建预警规则请求"""
    name: str
    stock_code: str
    alert_type: str
    threshold: Dict[str, Any]
    user_id: Optional[str] = None
    notes: Optional[str] = None


class AlertRuleUpdate(BaseModel):
    """更新预警规则请求"""
    name: Optional[str] = None
    threshold: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AlertRuleResponse(BaseModel):
    """预警规则响应"""
    id: int
    name: str
    stock_code: str
    alert_type: str
    threshold: Dict[str, Any]
    status: str
    user_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class AlertRecordResponse(BaseModel):
    """预警记录响应"""
    id: int
    rule_id: int
    trigger_price: Optional[float] = None
    trigger_change_pct: Optional[float] = None
    trigger_volume: Optional[float] = None
    trigger_turnover_rate: Optional[float] = None
    message: str
    is_read: bool
    is_handled: bool
    triggered_at: str
    handled_at: Optional[str] = None

    class Config:
        from_attributes = True


class AlertStatsResponse(BaseModel):
    """预警统计响应"""
    total_rules: int
    active_rules: int
    paused_rules: int
    total_records: int
    unread_count: int


# ============================================
# API 端点
# ============================================

@router.post("/rules", response_model=AlertRuleResponse)
async def create_alert_rule(rule: AlertRuleCreate):
    """
    创建预警规则

    预警类型:
    - price_above: 价格高于指定值
    - price_below: 价格低于指定值
    - change_up: 涨幅超过指定值
    - change_down: 跌幅超过指定值
    - volume_spike: 成交量异动（超过近N日平均的倍数）
    - turnover_spike: 换手率异动（超过近N日平均的倍数）

    阈值格式:
    - price_above/below: {"price": 100.0}
    - change_up/down: {"change_percent": 5.0}
    - volume_spike: {"volume_ratio": 2.0, "days": 5}
    - turnover_spike: {"turnover_ratio": 1.5, "days": 5}
    """
    try:
        service = get_alert_service()
        with session_scope() as session:
            new_rule = await service.create_alert_rule(
                session=session,
                name=rule.name,
                stock_code=rule.stock_code,
                alert_type=rule.alert_type,
                threshold=rule.threshold,
                user_id=rule.user_id,
                notes=rule.notes,
            )
            return AlertRuleResponse(
                id=new_rule.id,
                name=new_rule.name,
                stock_code=new_rule.stock_code,
                alert_type=new_rule.alert_type,
                threshold=new_rule.threshold,
                status=new_rule.status,
                user_id=new_rule.user_id,
                notes=new_rule.notes,
                created_at=new_rule.created_at.isoformat(),
                updated_at=new_rule.updated_at.isoformat(),
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建预警规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建预警规则失败: {str(e)}")


@router.get("/rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    stock_code: Optional[str] = Query(None, description="股票代码"),
    alert_type: Optional[str] = Query(None, description="预警类型"),
    status: Optional[str] = Query(None, description="预警状态"),
    user_id: Optional[str] = Query(None, description="用户ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取预警规则列表"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            rules = await service.get_alert_rules(
                session=session,
                stock_code=stock_code,
                alert_type=alert_type,
                status=status,
                user_id=user_id,
                limit=limit,
                offset=offset,
            )
            return [
                AlertRuleResponse(
                    id=r.id,
                    name=r.name,
                    stock_code=r.stock_code,
                    alert_type=r.alert_type,
                    threshold=r.threshold,
                    status=r.status,
                    user_id=r.user_id,
                    notes=r.notes,
                    created_at=r.created_at.isoformat(),
                    updated_at=r.updated_at.isoformat(),
                )
                for r in rules
            ]
    except Exception as e:
        logger.error(f"获取预警规则列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预警规则列表失败: {str(e)}")


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(rule_id: int):
    """获取单个预警规则详情"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            rule = await service.get_alert_rule_by_id(session, rule_id)
            if not rule:
                raise HTTPException(status_code=404, detail=f"预警规则不存在: {rule_id}")
            return AlertRuleResponse(
                id=rule.id,
                name=rule.name,
                stock_code=rule.stock_code,
                alert_type=rule.alert_type,
                threshold=rule.threshold,
                status=rule.status,
                user_id=rule.user_id,
                notes=rule.notes,
                created_at=rule.created_at.isoformat(),
                updated_at=rule.updated_at.isoformat(),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取预警规则详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预警规则详情失败: {str(e)}")


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: int, rule: AlertRuleUpdate):
    """更新预警规则"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            updated_rule = await service.update_alert_rule(
                session=session,
                rule_id=rule_id,
                name=rule.name,
                threshold=rule.threshold,
                status=rule.status,
                notes=rule.notes,
            )
            if not updated_rule:
                raise HTTPException(status_code=404, detail=f"预警规则不存在: {rule_id}")
            return AlertRuleResponse(
                id=updated_rule.id,
                name=updated_rule.name,
                stock_code=updated_rule.stock_code,
                alert_type=updated_rule.alert_type,
                threshold=updated_rule.threshold,
                status=updated_rule.status,
                user_id=updated_rule.user_id,
                notes=updated_rule.notes,
                created_at=updated_rule.created_at.isoformat(),
                updated_at=updated_rule.updated_at.isoformat(),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新预警规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新预警规则失败: {str(e)}")


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(rule_id: int):
    """删除预警规则"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            success = await service.delete_alert_rule(session, rule_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"预警规则不存在: {rule_id}")
            return {"message": "预警规则已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除预警规则失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除预警规则失败: {str(e)}")


@router.post("/rules/{rule_id}/toggle")
async def toggle_alert_rule(rule_id: int, active: bool = True):
    """启用/暂停预警规则"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            updated_rule = await service.toggle_alert_rule(session, rule_id, active)
            if not updated_rule:
                raise HTTPException(status_code=404, detail=f"预警规则不存在: {rule_id}")
            return {
                "message": f"预警规则已{'启用' if active else '暂停'}",
                "status": updated_rule.status,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换预警规则状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换预警规则状态失败: {str(e)}")


@router.post("/check")
async def check_alerts():
    """手动触发预警检查"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            triggered_alerts = await service.check_all_alerts(session)
            return {
                "checked": True,
                "triggered_count": len(triggered_alerts),
                "alerts": [
                    {
                        "id": a.id,
                        "rule_id": a.rule_id,
                        "message": a.message,
                        "triggered_at": a.triggered_at.isoformat(),
                    }
                    for a in triggered_alerts
                ],
            }
    except Exception as e:
        logger.error(f"预警检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"预警检查失败: {str(e)}")


@router.get("/records", response_model=List[AlertRecordResponse])
async def get_alert_records(
    rule_id: Optional[int] = Query(None, description="预警规则ID"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    is_read: Optional[bool] = Query(None, description="已读状态"),
    is_handled: Optional[bool] = Query(None, description="处理状态"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """获取预警记录列表"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            records = await service.get_alert_records(
                session=session,
                rule_id=rule_id,
                stock_code=stock_code,
                is_read=is_read,
                is_handled=is_handled,
                limit=limit,
                offset=offset,
            )
            return [
                AlertRecordResponse(
                    id=r.id,
                    rule_id=r.rule_id,
                    trigger_price=r.trigger_price,
                    trigger_change_pct=r.trigger_change_pct,
                    trigger_volume=r.trigger_volume,
                    trigger_turnover_rate=r.trigger_turnover_rate,
                    message=r.message,
                    is_read=r.is_read,
                    is_handled=r.is_handled,
                    triggered_at=r.triggered_at.isoformat(),
                    handled_at=r.handled_at.isoformat() if r.handled_at else None,
                )
                for r in records
            ]
    except Exception as e:
        logger.error(f"获取预警记录列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预警记录列表失败: {str(e)}")


@router.post("/records/{record_id}/read")
async def mark_alert_as_read(record_id: int):
    """标记预警记录为已读"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            success = await service.mark_alert_as_read(session, record_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"预警记录不存在: {record_id}")
            return {"message": "预警记录已标记为已读"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记已读失败: {e}")
        raise HTTPException(status_code=500, detail=f"标记已读失败: {str(e)}")


@router.post("/records/{record_id}/handle")
async def mark_alert_as_handled(record_id: int):
    """标记预警记录为已处理"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            success = await service.mark_alert_as_handled(session, record_id)
            if not success:
                raise HTTPException(status_code=404, detail=f"预警记录不存在: {record_id}")
            return {"message": "预警记录已标记为已处理"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"标记处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"标记处理失败: {str(e)}")


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats():
    """获取预警统计信息"""
    try:
        service = get_alert_service()
        with session_scope() as session:
            # 获取规则统计
            all_rules = await service.get_alert_rules(session, limit=1000)
            active_rules = [r for r in all_rules if r.status == "active"]
            paused_rules = [r for r in all_rules if r.status == "paused"]

            # 获取未读数量
            unread_count = await service.get_unread_count(session)

            # 获取记录统计
            all_records = await service.get_alert_records(session, limit=1000)

            return AlertStatsResponse(
                total_rules=len(all_rules),
                active_rules=len(active_rules),
                paused_rules=len(paused_rules),
                total_records=len(all_records),
                unread_count=unread_count,
            )
    except Exception as e:
        logger.error(f"获取预警统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取预警统计失败: {str(e)}")


# ============================================
# 根路由
# ============================================

@router.get("/")
async def alerts_root():
    """预警API根路由"""
    return {
        "message": "Alert API",
        "version": "1.0.0",
        "endpoints": {
            "create_rule": "POST /api/v1/alerts/rules - 创建预警规则",
            "list_rules": "GET /api/v1/alerts/rules - 获取预警规则列表",
            "get_rule": "GET /api/v1/alerts/rules/{id} - 获取预警规则详情",
            "update_rule": "PUT /api/v1/alerts/rules/{id} - 更新预警规则",
            "delete_rule": "DELETE /api/v1/alerts/rules/{id} - 删除预警规则",
            "toggle_rule": "POST /api/v1/alerts/rules/{id}/toggle - 启用/暂停预警规则",
            "check_alerts": "POST /api/v1/alerts/check - 手动触发预警检查",
            "list_records": "GET /api/v1/alerts/records - 获取预警记录列表",
            "mark_read": "POST /api/v1/alerts/records/{id}/read - 标记已读",
            "mark_handled": "POST /api/v1/alerts/records/{id}/handle - 标记已处理",
            "stats": "GET /api/v1/alerts/stats - 获取预警统计",
        },
    }

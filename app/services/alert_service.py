"""
预警服务模块

提供预警规则管理、预警检查和预警通知功能：
- 预警规则创建、更新、删除
- 预警触发检查
- 预警历史记录
- 预警通知推送
"""
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_engine
from app.models.alert import AlertRule, AlertRecord, AlertType, AlertStatus
from app.services.stock_service import get_stock_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AlertService:
    """预警服务类"""

    def __init__(self):
        """初始化预警服务"""
        self.engine = get_engine()
        self.stock_service = get_stock_service()
        self._notification_callbacks: List[Callable] = []

    def register_notification_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        注册预警通知回调函数

        Args:
            callback: 回调函数，接收预警记录作为参数
        """
        self._notification_callbacks.append(callback)

    async def _notify(self, alert_record: AlertRecord, rule: AlertRule):
        """触发通知回调"""
        alert_data = {
            "id": alert_record.id,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "stock_code": rule.stock_code,
            "alert_type": rule.alert_type,
            "message": alert_record.message,
            "trigger_price": alert_record.trigger_price,
            "trigger_change_pct": alert_record.trigger_change_pct,
            "trigger_volume": alert_record.trigger_volume,
            "triggered_at": alert_record.triggered_at.isoformat() if alert_record.triggered_at else None,
        }

        for callback in self._notification_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Notification callback error: {e}")

    # ==================== 预警规则管理 ====================

    async def create_alert_rule(
        self,
        session: AsyncSession,
        name: str,
        stock_code: str,
        alert_type: str,
        threshold: Dict[str, Any],
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> AlertRule:
        """
        创建预警规则

        Args:
            session: 数据库会话
            name: 预警名称
            stock_code: 股票代码
            alert_type: 预警类型
            threshold: 阈值配置
            user_id: 用户ID
            notes: 备注

        Returns:
            AlertRule 对象
        """
        # 验证预警类型
        try:
            AlertType(alert_type)
        except ValueError:
            raise ValueError(f"Invalid alert type: {alert_type}")

        rule = AlertRule(
            name=name,
            stock_code=stock_code,
            alert_type=alert_type,
            threshold=threshold,
            user_id=user_id,
            status=AlertStatus.ACTIVE.value,
            notes=notes,
        )

        session.add(rule)
        await session.commit()
        await session.refresh(rule)

        logger.info(f"Created alert rule: {rule.id} - {name} for {stock_code}")
        return rule

    async def get_alert_rules(
        self,
        session: AsyncSession,
        stock_code: Optional[str] = None,
        alert_type: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AlertRule]:
        """
        获取预警规则列表

        Args:
            session: 数据库会话
            stock_code: 股票代码过滤
            alert_type: 预警类型过滤
            status: 状态过滤
            user_id: 用户ID过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            AlertRule 列表
        """
        stmt = select(AlertRule)

        conditions = []
        if stock_code:
            conditions.append(AlertRule.stock_code == stock_code)
        if alert_type:
            conditions.append(AlertRule.alert_type == alert_type)
        if status:
            conditions.append(AlertRule.status == status)
        if user_id:
            conditions.append(AlertRule.user_id == user_id)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(AlertRule.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_alert_rule_by_id(
        self,
        session: AsyncSession,
        rule_id: int,
    ) -> Optional[AlertRule]:
        """
        根据ID获取预警规则

        Args:
            session: 数据库会话
            rule_id: 预警规则ID

        Returns:
            AlertRule 对象或 None
        """
        stmt = select(AlertRule).where(AlertRule.id == rule_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_alert_rule(
        self,
        session: AsyncSession,
        rule_id: int,
        name: Optional[str] = None,
        threshold: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[AlertRule]:
        """
        更新预警规则

        Args:
            session: 数据库会话
            rule_id: 预警规则ID
            name: 预警名称
            threshold: 阈值配置
            status: 状态
            notes: 备注

        Returns:
            更新后的 AlertRule 对象或 None
        """
        rule = await self.get_alert_rule_by_id(session, rule_id)
        if not rule:
            return None

        if name is not None:
            rule.name = name
        if threshold is not None:
            rule.threshold = threshold
        if status is not None:
            rule.status = status
        if notes is not None:
            rule.notes = notes

        rule.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(rule)

        logger.info(f"Updated alert rule: {rule_id}")
        return rule

    async def delete_alert_rule(
        self,
        session: AsyncSession,
        rule_id: int,
    ) -> bool:
        """
        删除预警规则

        Args:
            session: 数据库会话
            rule_id: 预警规则ID

        Returns:
            是否成功删除
        """
        rule = await self.get_alert_rule_by_id(session, rule_id)
        if not rule:
            return False

        await session.delete(rule)
        await session.commit()

        logger.info(f"Deleted alert rule: {rule_id}")
        return True

    async def toggle_alert_rule(
        self,
        session: AsyncSession,
        rule_id: int,
        active: bool,
    ) -> Optional[AlertRule]:
        """
        启用/暂停预警规则

        Args:
            session: 数据库会话
            rule_id: 预警规则ID
            active: 是否启用

        Returns:
            更新后的 AlertRule 对象或 None
        """
        status = AlertStatus.ACTIVE.value if active else AlertStatus.PAUSED.value
        return await self.update_alert_rule(session, rule_id, status=status)

    # ==================== 预警检查 ====================

    async def check_alert(
        self,
        session: AsyncSession,
        rule: AlertRule,
    ) -> Optional[AlertRecord]:
        """
        检查单个预警规则是否触发

        Args:
            session: 数据库会话
            rule: 预警规则

        Returns:
            AlertRecord 对象或 None（未触发时）
        """
        try:
            alert_type = AlertType(rule.alert_type)
        except ValueError:
            logger.warning(f"Unknown alert type: {rule.alert_type}")
            return None

        # 获取股票实时行情
        quote = self.stock_service.get_stock_quote(rule.stock_code)
        if not quote:
            logger.warning(f"Cannot get quote for {rule.stock_code}")
            return None

        price = quote.get("price", 0)
        change_pct = quote.get("change_percent", 0)
        volume = quote.get("volume", 0)
        amount = quote.get("amount", 0)

        # 获取历史成交量数据用于异动判断
        kline_data = None
        if alert_type in [AlertType.VOLUME_SPIKE, AlertType.TURNOVER_SPIKE]:
            threshold_days = rule.threshold.get("days", 5)
            kline_data = self.stock_service.get_kline_data(
                symbol=rule.stock_code,
                period="daily",
                start_date=None,
                end_date=None,
                adjust=""
            )
            if not kline_data or len(kline_data) < threshold_days:
                logger.warning(f"Insufficient kline data for {rule.stock_code}")
                return None

        # 根据预警类型判断是否触发
        triggered = False
        message = ""

        if alert_type == AlertType.PRICE_ABOVE:
            target_price = rule.threshold.get("price", 0)
            if price >= target_price:
                triggered = True
                message = f"股票 {rule.stock_code} 当前价格 {price:.2f} 超过目标价格 {target_price:.2f}"

        elif alert_type == AlertType.PRICE_BELOW:
            target_price = rule.threshold.get("price", 0)
            if price <= target_price:
                triggered = True
                message = f"股票 {rule.stock_code} 当前价格 {price:.2f} 低于目标价格 {target_price:.2f}"

        elif alert_type == AlertType.CHANGE_UP:
            target_change = rule.threshold.get("change_percent", 0)
            if change_pct >= target_change:
                triggered = True
                message = f"股票 {rule.stock_code} 涨幅 {change_pct:.2f}% 超过目标涨幅 {target_change:.2f}%"

        elif alert_type == AlertType.CHANGE_DOWN:
            target_change = rule.threshold.get("change_percent", 0)
            if change_pct <= -target_change:
                triggered = True
                message = f"股票 {rule.stock_code} 跌幅 {abs(change_pct):.2f}% 超过目标跌幅 {target_change:.2f}%"

        elif alert_type == AlertType.VOLUME_SPIKE:
            threshold_ratio = rule.threshold.get("volume_ratio", 2.0)
            threshold_days = rule.threshold.get("days", 5)

            # 计算近期平均成交量
            recent_volumes = [float(k.get("volume", 0)) for k in kline_data[:threshold_days]]
            if recent_volumes:
                avg_volume = sum(recent_volumes) / len(recent_volumes)
                if avg_volume > 0 and volume >= avg_volume * threshold_ratio:
                    triggered = True
                    message = f"股票 {rule.stock_code} 成交量 {volume:.0f} 超过近 {threshold_days} 日平均 {avg_volume:.0f} 的 {threshold_ratio:.1f} 倍"

        elif alert_type == AlertType.TURNOVER_SPIKE:
            threshold_ratio = rule.threshold.get("turnover_ratio", 1.5)
            threshold_days = rule.threshold.get("days", 5)

            # 计算近期平均换手率
            recent_turnover = [float(k.get("turnover_rate", 0)) for k in kline_data[:threshold_days]]
            if recent_turnover:
                avg_turnover = sum(recent_turnover) / len(recent_turnover)
                # 获取当前换手率
                current_turnover = kline_data[0].get("turnover_rate", 0) if kline_data else 0
                if avg_turnover > 0 and current_turnover >= avg_turnover * threshold_ratio:
                    triggered = True
                    message = f"股票 {rule.stock_code} 换手率 {current_turnover:.2f}% 超过近 {threshold_days} 日平均 {avg_turnover:.2f}% 的 {threshold_ratio:.1f} 倍"

        if triggered:
            # 创建预警记录
            alert_record = AlertRecord(
                rule_id=rule.id,
                trigger_price=price,
                trigger_change_pct=change_pct,
                trigger_volume=volume,
                message=message,
            )

            session.add(alert_record)
            await session.commit()
            await session.refresh(alert_record)

            logger.info(f"Alert triggered: {rule.id} - {message}")

            # 触发通知回调
            await self._notify(alert_record, rule)

            return alert_record

        return None

    async def check_all_alerts(
        self,
        session: AsyncSession,
    ) -> List[AlertRecord]:
        """
        检查所有活跃预警规则

        Args:
            session: 数据库会话

        Returns:
            触发预警记录列表
        """
        # 获取所有活跃的预警规则
        stmt = select(AlertRule).where(AlertRule.status == AlertStatus.ACTIVE.value)
        result = await session.execute(stmt)
        rules = list(result.scalars().all())

        triggered_alerts = []
        for rule in rules:
            try:
                alert_record = await self.check_alert(session, rule)
                if alert_record:
                    triggered_alerts.append(alert_record)
            except Exception as e:
                logger.error(f"Error checking alert {rule.id}: {e}")

        return triggered_alerts

    # ==================== 预警记录查询 ====================

    async def get_alert_records(
        self,
        session: AsyncSession,
        rule_id: Optional[int] = None,
        stock_code: Optional[str] = None,
        is_read: Optional[bool] = None,
        is_handled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AlertRecord]:
        """
        获取预警记录列表

        Args:
            session: 数据库会话
            rule_id: 预警规则ID过滤
            stock_code: 股票代码过滤
            is_read: 已读状态过滤
            is_handled: 已处理状态过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            AlertRecord 列表
        """
        stmt = select(AlertRecord)

        conditions = []
        if rule_id:
            conditions.append(AlertRecord.rule_id == rule_id)
        if is_read is not None:
            conditions.append(AlertRecord.is_read == is_read)
        if is_handled is not None:
            conditions.append(AlertRecord.is_handled == is_handled)

        if stock_code:
            # 关联 AlertRule 进行过滤
            stmt = stmt.join(AlertRule).where(AlertRule.stock_code == stock_code)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(AlertRecord.triggered_at.desc()).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def mark_alert_as_read(
        self,
        session: AsyncSession,
        record_id: int,
    ) -> bool:
        """
        标记预警记录为已读

        Args:
            session: 数据库会话
            record_id: 预警记录ID

        Returns:
            是否成功
        """
        stmt = select(AlertRecord).where(AlertRecord.id == record_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return False

        record.is_read = True
        await session.commit()
        return True

    async def mark_alert_as_handled(
        self,
        session: AsyncSession,
        record_id: int,
    ) -> bool:
        """
        标记预警记录为已处理

        Args:
            session: 数据库会话
            record_id: 预警记录ID

        Returns:
            是否成功
        """
        stmt = select(AlertRecord).where(AlertRecord.id == record_id)
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return False

        record.is_handled = True
        record.handled_at = datetime.utcnow()
        await session.commit()
        return True

    async def get_unread_count(
        self,
        session: AsyncSession,
    ) -> int:
        """
        获取未读预警数量

        Args:
            session: 数据库会话

        Returns:
            未读预警数量
        """
        stmt = select(func.count(AlertRecord.id)).where(
            and_(
                AlertRecord.is_read == False,
                AlertRecord.is_handled == False,
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0


# 全局预警服务实例
_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """
    获取全局预警服务实例

    Returns:
        AlertService 实例
    """
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service

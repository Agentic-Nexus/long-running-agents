"""
预警服务测试用例

测试预警规则管理、预警检查和预警记录功能。
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.alert_service import AlertService
from app.models.alert import AlertRule, AlertRecord, AlertType, AlertStatus


class TestAlertService:
    """预警服务测试类"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = Mock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        session.add = Mock()
        return session

    @pytest.fixture
    def alert_service(self):
        """创建预警服务实例"""
        return AlertService()

    def test_alert_types(self):
        """测试预警类型枚举"""
        assert AlertType.PRICE_ABOVE.value == "price_above"
        assert AlertType.PRICE_BELOW.value == "price_below"
        assert AlertType.CHANGE_UP.value == "change_up"
        assert AlertType.CHANGE_DOWN.value == "change_down"
        assert AlertType.VOLUME_SPIKE.value == "volume_spike"
        assert AlertType.TURNOVER_SPIKE.value == "turnover_spike"

    def test_alert_status(self):
        """测试预警状态枚举"""
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.TRIGGERED.value == "triggered"
        assert AlertStatus.PAUSED.value == "paused"
        assert AlertStatus.EXPIRED.value == "expired"

    @pytest.mark.asyncio
    async def test_create_alert_rule(self, alert_service, mock_session):
        """测试创建预警规则"""
        # 创建模拟的 AlertRule 返回值
        mock_rule = AlertRule(
            id=1,
            name="Test Alert",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
            status="active",
            user_id="test_user",
            notes="Test note",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟 session.execute 返回值
        mock_result = Mock()
        mock_result.scalar_one = Mock(return_value=mock_rule)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # 执行创建
        rule = await alert_service.create_alert_rule(
            session=mock_session,
            name="Test Alert",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
            user_id="test_user",
            notes="Test note",
        )

        assert rule.name == "Test Alert"
        assert rule.stock_code == "600000"
        assert rule.alert_type == "price_above"
        assert rule.threshold == {"price": 100.0}

    @pytest.mark.asyncio
    async def test_create_alert_rule_invalid_type(self, alert_service, mock_session):
        """测试创建预警规则时无效的预警类型"""
        with pytest.raises(ValueError):
            await alert_service.create_alert_rule(
                session=mock_session,
                name="Test Alert",
                stock_code="600000",
                alert_type="invalid_type",
                threshold={"price": 100.0},
            )

    @pytest.mark.asyncio
    async def test_check_price_above_alert_triggered(self, alert_service, mock_session):
        """测试价格高于预警触发"""
        # 创建预警规则
        rule = AlertRule(
            id=1,
            name="价格预警",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 10.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 模拟股票服务返回的价格
        mock_quote = {
            "code": "600000",
            "name": "浦发银行",
            "price": 12.5,
            "change_percent": 2.5,
            "volume": 1000000,
            "amount": 10000000,
        }

        with patch.object(alert_service.stock_service, 'get_stock_quote', return_value=mock_quote):
            with patch.object(alert_service, '_notify', new_callable=AsyncMock):
                result = await alert_service.check_alert(mock_session, rule)

                assert result is not None
                assert "超过目标价格" in result.message
                assert result.trigger_price == 12.5

    @pytest.mark.asyncio
    async def test_check_price_above_alert_not_triggered(self, alert_service, mock_session):
        """测试价格高于预警未触发"""
        rule = AlertRule(
            id=1,
            name="价格预警",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 15.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_quote = {
            "code": "600000",
            "name": "浦发银行",
            "price": 12.5,
            "change_percent": 2.5,
            "volume": 1000000,
            "amount": 10000000,
        }

        with patch.object(alert_service.stock_service, 'get_stock_quote', return_value=mock_quote):
            result = await alert_service.check_alert(mock_session, rule)

            assert result is None

    @pytest.mark.asyncio
    async def test_check_change_up_alert_triggered(self, alert_service, mock_session):
        """测试涨幅预警触发"""
        rule = AlertRule(
            id=2,
            name="涨幅预警",
            stock_code="600000",
            alert_type="change_up",
            threshold={"change_percent": 3.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_quote = {
            "code": "600000",
            "name": "浦发银行",
            "price": 10.3,
            "change_percent": 5.0,
            "volume": 1000000,
            "amount": 10000000,
        }

        with patch.object(alert_service.stock_service, 'get_stock_quote', return_value=mock_quote):
            with patch.object(alert_service, '_notify', new_callable=AsyncMock):
                result = await alert_service.check_alert(mock_session, rule)

                assert result is not None
                assert "涨幅" in result.message
                assert result.trigger_change_pct == 5.0

    @pytest.mark.asyncio
    async def test_check_change_down_alert_triggered(self, alert_service, mock_session):
        """测试跌幅预警触发"""
        rule = AlertRule(
            id=3,
            name="跌幅预警",
            stock_code="600000",
            alert_type="change_down",
            threshold={"change_percent": 3.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_quote = {
            "code": "600000",
            "name": "浦发银行",
            "price": 9.7,
            "change_percent": -5.0,
            "volume": 1000000,
            "amount": 10000000,
        }

        with patch.object(alert_service.stock_service, 'get_stock_quote', return_value=mock_quote):
            with patch.object(alert_service, '_notify', new_callable=AsyncMock):
                result = await alert_service.check_alert(mock_session, rule)

                assert result is not None
                assert "跌幅" in result.message
                assert result.trigger_change_pct == -5.0


class TestAlertModels:
    """预警模型测试类"""

    def test_alert_rule_model(self):
        """测试预警规则模型"""
        rule = AlertRule(
            id=1,
            name="测试预警",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
            status="active",
        )

        assert rule.id == 1
        assert rule.name == "测试预警"
        assert rule.stock_code == "600000"
        assert rule.alert_type == "price_above"
        assert rule.threshold == {"price": 100.0}
        assert rule.status == "active"

    def test_alert_record_model(self):
        """测试预警记录模型"""
        record = AlertRecord(
            id=1,
            rule_id=1,
            trigger_price=105.5,
            trigger_change_pct=5.5,
            trigger_volume=2000000,
            message="股票 600000 当前价格 105.5 超过目标价格 100.0",
            is_read=False,
            is_handled=False,
            triggered_at=datetime.utcnow(),
        )

        assert record.id == 1
        assert record.rule_id == 1
        assert record.trigger_price == 105.5
        assert record.is_read is False
        assert record.is_handled is False

    def test_threshold_formats(self):
        """测试不同预警类型的阈值格式"""
        # 价格预警
        rule1 = AlertRule(
            name="价格高于",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert rule1.threshold["price"] == 100.0

        # 涨幅预警
        rule2 = AlertRule(
            name="涨幅预警",
            stock_code="600000",
            alert_type="change_up",
            threshold={"change_percent": 5.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert rule2.threshold["change_percent"] == 5.0

        # 成交量异动预警
        rule3 = AlertRule(
            name="成交量异动",
            stock_code="600000",
            alert_type="volume_spike",
            threshold={"volume_ratio": 2.0, "days": 5},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert rule3.threshold["volume_ratio"] == 2.0
        assert rule3.threshold["days"] == 5

        # 换手率异动预警
        rule4 = AlertRule(
            name="换手率异动",
            stock_code="600000",
            alert_type="turnover_spike",
            threshold={"turnover_ratio": 1.5, "days": 5},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert rule4.threshold["turnover_ratio"] == 1.5
        assert rule4.threshold["days"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

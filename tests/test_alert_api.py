"""
预警 API 测试用例

测试预警 API 端点功能。
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from fastapi.testclient import TestClient
from fastapi import HTTPException


class TestAlertAPI:
    """预警 API 测试类"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        session.commit = Mock()
        session.refresh = Mock()
        session.add = Mock()
        session.delete = Mock()
        return session

    @pytest.fixture
    def mock_alert_service(self):
        """创建模拟的预警服务"""
        service = Mock()

        # 模拟创建预警规则
        service.create_alert_rule = AsyncMock(return_value=Mock(
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
        ))

        # 模拟获取预警规则列表
        service.get_alert_rules = AsyncMock(return_value=[
            Mock(
                id=1,
                name="Test Alert",
                stock_code="600000",
                alert_type="price_above",
                threshold={"price": 100.0},
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        ])

        # 模拟获取单个预警规则
        service.get_alert_rule_by_id = AsyncMock(return_value=Mock(
            id=1,
            name="Test Alert",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))

        # 模拟更新预警规则
        service.update_alert_rule = AsyncMock(return_value=Mock(
            id=1,
            name="Updated Alert",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 150.0},
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))

        # 模拟删除预警规则
        service.delete_alert_rule = AsyncMock(return_value=True)

        # 模拟切换预警规则状态
        service.toggle_alert_rule = AsyncMock(return_value=Mock(
            id=1,
            name="Test Alert",
            status="active",
        ))

        # 模拟检查所有预警
        service.check_all_alerts = AsyncMock(return_value=[])

        # 模拟获取预警记录
        service.get_alert_records = AsyncMock(return_value=[])

        # 模拟标记已读
        service.mark_alert_as_read = AsyncMock(return_value=True)

        # 模拟标记已处理
        service.mark_alert_as_handled = AsyncMock(return_value=True)

        # 模拟获取未读数量
        service.get_unread_count = AsyncMock(return_value=0)

        return service


class TestAlertRuleEndpoints:
    """测试预警规则端点"""

    def test_alert_rule_create_request_model(self):
        """测试创建预警规则请求模型"""
        from app.api.alert import AlertRuleCreate

        rule = AlertRuleCreate(
            name="价格预警",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
        )

        assert rule.name == "价格预警"
        assert rule.stock_code == "600000"
        assert rule.alert_type == "price_above"
        assert rule.threshold == {"price": 100.0}

    def test_alert_rule_update_request_model(self):
        """测试更新预警规则请求模型"""
        from app.api.alert import AlertRuleUpdate

        rule = AlertRuleUpdate(
            name="新名称",
            threshold={"price": 150.0},
        )

        assert rule.name == "新名称"
        assert rule.threshold == {"price": 150.0}

    def test_alert_rule_response_model(self):
        """测试预警规则响应模型"""
        from app.api.alert import AlertRuleResponse

        response = AlertRuleResponse(
            id=1,
            name="Test Alert",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
            status="active",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        assert response.id == 1
        assert response.name == "Test Alert"
        assert response.stock_code == "600000"
        assert response.alert_type == "price_above"

    def test_alert_record_response_model(self):
        """测试预警记录响应模型"""
        from app.api.alert import AlertRecordResponse

        response = AlertRecordResponse(
            id=1,
            rule_id=1,
            trigger_price=105.5,
            trigger_change_pct=5.5,
            message="测试消息",
            is_read=False,
            is_handled=False,
            triggered_at="2024-01-01T00:00:00",
        )

        assert response.id == 1
        assert response.rule_id == 1
        assert response.trigger_price == 105.5
        assert response.is_read is False

    def test_alert_stats_response_model(self):
        """测试预警统计响应模型"""
        from app.api.alert import AlertStatsResponse

        stats = AlertStatsResponse(
            total_rules=10,
            active_rules=8,
            paused_rules=2,
            total_records=50,
            unread_count=5,
        )

        assert stats.total_rules == 10
        assert stats.active_rules == 8
        assert stats.unread_count == 5


class TestAlertTypes:
    """测试预警类型"""

    def test_valid_alert_types(self):
        """测试有效的预警类型"""
        valid_types = [
            "price_above",
            "price_below",
            "change_up",
            "change_down",
            "volume_spike",
            "turnover_spike",
        ]

        for alert_type in valid_types:
            from app.models.alert import AlertType
            assert AlertType(alert_type).value == alert_type

    def test_invalid_alert_type(self):
        """测试无效的预警类型"""
        from app.models.alert import AlertType

        with pytest.raises(ValueError):
            AlertType("invalid_type")


class TestAlertThresholdFormats:
    """测试预警阈值格式"""

    def test_price_threshold_format(self):
        """测试价格预警阈值格式"""
        from app.api.alert import AlertRuleCreate

        # 价格高于
        rule = AlertRuleCreate(
            name="价格高于",
            stock_code="600000",
            alert_type="price_above",
            threshold={"price": 100.0},
        )
        assert "price" in rule.threshold

        # 价格低于
        rule = AlertRuleCreate(
            name="价格低于",
            stock_code="600000",
            alert_type="price_below",
            threshold={"price": 50.0},
        )
        assert "price" in rule.threshold

    def test_change_threshold_format(self):
        """测试涨跌幅预警阈值格式"""
        from app.api.alert import AlertRuleCreate

        # 涨幅高于
        rule = AlertRuleCreate(
            name="涨幅高于",
            stock_code="600000",
            alert_type="change_up",
            threshold={"change_percent": 5.0},
        )
        assert "change_percent" in rule.threshold

        # 跌幅高于
        rule = AlertRuleCreate(
            name="跌幅高于",
            stock_code="600000",
            alert_type="change_down",
            threshold={"change_percent": 3.0},
        )
        assert "change_percent" in rule.threshold

    def test_volume_threshold_format(self):
        """测试成交量异动预警阈值格式"""
        from app.api.alert import AlertRuleCreate

        rule = AlertRuleCreate(
            name="成交量异动",
            stock_code="600000",
            alert_type="volume_spike",
            threshold={"volume_ratio": 2.0, "days": 5},
        )
        assert "volume_ratio" in rule.threshold
        assert "days" in rule.threshold

    def test_turnover_threshold_format(self):
        """测试换手率异动预警阈值格式"""
        from app.api.alert import AlertRuleCreate

        rule = AlertRuleCreate(
            name="换手率异动",
            stock_code="600000",
            alert_type="turnover_spike",
            threshold={"turnover_ratio": 1.5, "days": 5},
        )
        assert "turnover_ratio" in rule.threshold
        assert "days" in rule.threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

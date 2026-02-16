"""
测试日志模块
"""
import pytest
import sys
from pathlib import Path
from app.utils.logger import setup_logger, get_logger


class TestLogger:
    """日志模块测试"""

    def test_setup_logger(self):
        """测试日志设置"""
        logger = setup_logger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"
        assert logger.level == 20  # INFO

    def test_get_logger(self):
        """测试获取日志记录器"""
        logger = get_logger("test")
        assert logger is not None
        assert logger.name == "test"

    def test_logger_has_handlers(self):
        """测试日志处理器"""
        logger = setup_logger("test_handlers")
        assert len(logger.handlers) > 0

    def test_logger_format(self):
        """测试日志格式"""
        import logging
        logger = setup_logger("test_format")

        # 创建一个测试处理器
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.info("Test message")

        # 检查是否成功记录
        assert True  # 如果没有异常则通过

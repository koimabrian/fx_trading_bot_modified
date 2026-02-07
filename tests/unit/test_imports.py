# tests/test_imports.py
"""Test core module imports."""


def test_mt5_connector_import():
    """Test MT5 connector import."""
    from src.mt5_connector import MT5Connector
    assert MT5Connector is not None


def test_database_import():
    """Test database import."""
    from src.database.db_manager import DatabaseManager
    assert DatabaseManager is not None


def test_strategy_manager_import():
    """Test strategy manager import."""
    from src.strategy_manager import StrategyManager
    assert StrategyManager is not None

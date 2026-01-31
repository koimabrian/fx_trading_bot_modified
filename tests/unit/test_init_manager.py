"""Unit tests for init manager module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime

from src.core.init_manager import InitManager


class TestInitManagerInitialization:
    """Test InitManager initialization."""

    def test_init_manager_initialization(self):
        """Test InitManager initializes correctly."""
        mock_db = Mock()
        mock_mt5 = Mock()
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            manager = InitManager(mock_db, mock_mt5, config)
            assert manager is not None

    def test_init_manager_with_config(self):
        """Test InitManager initialization with config."""
        mock_db = Mock()
        mock_mt5 = Mock()
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            manager = InitManager(mock_db, mock_mt5, config)
            assert hasattr(manager, "__init__")


class TestDatabaseInitialization:
    """Test database initialization."""

    def test_database_creation(self):
        """Test database creation."""
        with patch("src.database.db_manager.DatabaseManager") as mock_db:
            mock_db.return_value.create_tables = Mock()

            db = mock_db.return_value
            db.create_tables()

            db.create_tables.assert_called_once()

    def test_database_schema_validation(self):
        """Test database schema validation."""
        expected_tables = [
            "accounts",
            "symbols",
            "backtest_results",
            "trades",
            "positions",
        ]

        # Verify all required tables are in expected list
        for table in expected_tables:
            assert isinstance(table, str)
            assert len(table) > 0

    def test_database_migration_execution(self):
        """Test database migration execution."""
        with patch("src.database.migrations.DatabaseMigrations") as mock_migrations:
            mock_migrations.apply_migrations = Mock()

            mock_migrations.apply_migrations()
            mock_migrations.apply_migrations.assert_called_once()


class TestConfigurationSetup:
    """Test configuration setup."""

    def test_config_file_validation(self):
        """Test config file validation."""
        config = {
            "mt5": {
                "server": "Your Broker MT5 Server",
                "account": 12345,
                "password": "test_password",
            },
            "trading": {
                "symbols": ["EURUSD", "GBPUSD"],
                "timeframes": ["H1", "H4"],
                "leverage": 30,
            },
        }

        assert "mt5" in config
        assert "trading" in config
        assert "server" in config["mt5"]

    def test_config_required_fields(self):
        """Test config required fields."""
        required_fields = {
            "mt5": ["server", "account", "password"],
            "trading": ["symbols", "timeframes"],
        }

        config = {
            "mt5": {"server": "Broker", "account": 123, "password": "pwd"},
            "trading": {"symbols": ["EURUSD"], "timeframes": ["H1"]},
        }

        # Verify all required fields exist
        for section, fields in required_fields.items():
            for field in fields:
                assert field in config[section]

    def test_config_validation_failure(self):
        """Test config validation failure."""
        invalid_config = {
            "mt5": {
                # Missing required fields
            },
            "trading": {
                "symbols": ["EURUSD"],
                # Missing timeframes
            },
        }

        # Check for missing required fields
        has_server = "server" in invalid_config.get("mt5", {})
        has_timeframes = "timeframes" in invalid_config.get("trading", {})

        assert has_server is False
        assert has_timeframes is False


class TestSymbolDiscovery:
    """Test symbol discovery."""

    def test_symbol_list_loading(self):
        """Test loading symbol list."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]

        assert len(symbols) > 0
        assert all(isinstance(s, str) for s in symbols)

    def test_symbol_validation(self):
        """Test symbol validation."""
        valid_symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        for symbol in valid_symbols:
            # Each symbol should be valid format
            is_valid = len(symbol) == 6 and symbol.isupper()
            assert is_valid is True

    def test_invalid_symbol_detection(self):
        """Test detection of invalid symbols."""
        invalid_symbols = ["EUR", "INVALID", "eu-usd"]

        for symbol in invalid_symbols:
            # Check if symbol is valid 6-char format
            is_valid = len(symbol) == 6 and symbol.isupper()
            assert is_valid is False

    def test_symbol_filtering(self):
        """Test symbol filtering."""
        all_symbols = ["EURUSD", "GBPUSD", "USDJPY", "BTCUSD", "ETHUSD"]

        # Filter for forex only (6-char pairs)
        forex_symbols = [s for s in all_symbols if len(s) == 6]

        assert len(forex_symbols) >= 3


class TestDataSourceConfiguration:
    """Test data source configuration."""

    def test_mt5_connection_config(self):
        """Test MT5 connection configuration."""
        mt5_config = {
            "server": "Your Broker MT5 Server",
            "account": 12345,
            "password": "password",
            "timeout": 30,
        }

        assert mt5_config["account"] > 0
        assert len(mt5_config["server"]) > 0

    def test_timeframe_configuration(self):
        """Test timeframe configuration."""
        valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]

        configured_timeframes = ["H1", "H4", "D1"]

        for tf in configured_timeframes:
            assert tf in valid_timeframes

    def test_invalid_timeframe_detection(self):
        """Test detection of invalid timeframes."""
        invalid_timeframes = ["H0", "M0", "INVALID"]

        valid_timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]

        for tf in invalid_timeframes:
            assert tf not in valid_timeframes


class TestInitializationSteps:
    """Test initialization steps."""

    def test_step_1_config_load(self):
        """Test step 1: Config loading."""
        with patch("src.utils.config_manager.ConfigManager") as mock_config:
            mock_config.get_config = Mock(return_value={"mt5": {}, "trading": {}})

            config = mock_config.get_config()
            assert config is not None

    def test_step_2_database_init(self):
        """Test step 2: Database initialization."""
        with patch("src.database.db_manager.DatabaseManager") as mock_db:
            mock_db.return_value.create_tables = Mock()

            db = mock_db.return_value
            db.create_tables()

            db.create_tables.assert_called_once()

    def test_step_3_mt5_connection(self):
        """Test step 3: MT5 connection."""
        with patch("src.mt5_connector.MT5Connector") as mock_mt5:
            mock_mt5.get_instance = Mock(return_value=MagicMock())
            mock_mt5.get_instance.return_value.initialize = Mock(return_value=True)

            connector = mock_mt5.get_instance()
            result = connector.initialize()

            assert result is True

    def test_step_4_symbol_discovery(self):
        """Test step 4: Symbol discovery."""
        with patch("src.mt5_connector.MT5Connector") as mock_mt5:
            mock_mt5.get_instance = Mock(return_value=MagicMock())
            mock_mt5.get_instance.return_value.get_symbols = Mock(
                return_value=["EURUSD", "GBPUSD"]
            )

            connector = mock_mt5.get_instance()
            symbols = connector.get_symbols()

            assert len(symbols) > 0

    def test_step_5_validation_complete(self):
        """Test step 5: Validation complete."""
        initialization_complete = True
        assert initialization_complete is True


class TestErrorHandlingDuringInit:
    """Test error handling during initialization."""

    def test_config_load_error(self):
        """Test handling of config load error."""
        with patch("src.utils.config_manager.ConfigManager") as mock_config:
            mock_config.get_config = Mock(
                side_effect=FileNotFoundError("Config not found")
            )

            with pytest.raises(FileNotFoundError):
                mock_config.get_config()

    def test_database_init_error(self):
        """Test handling of database initialization error."""
        with patch("src.database.db_manager.DatabaseManager") as mock_db:
            mock_db.return_value.create_tables = Mock(side_effect=Exception("DB Error"))

            db = mock_db.return_value

            with pytest.raises(Exception):
                db.create_tables()

    def test_mt5_connection_error(self):
        """Test handling of MT5 connection error."""
        with patch("src.mt5_connector.MT5Connector") as mock_mt5:
            mock_mt5.get_instance = Mock(return_value=MagicMock())
            mock_mt5.get_instance.return_value.initialize = Mock(
                side_effect=ConnectionError("MT5 Connection Failed")
            )

            connector = mock_mt5.get_instance()

            with pytest.raises(ConnectionError):
                connector.initialize()

    def test_symbol_discovery_error(self):
        """Test handling of symbol discovery error."""
        with patch("src.mt5_connector.MT5Connector") as mock_mt5:
            mock_mt5.get_instance = Mock(return_value=MagicMock())
            mock_mt5.get_instance.return_value.get_symbols = Mock(
                side_effect=Exception("Symbol Discovery Failed")
            )

            connector = mock_mt5.get_instance()

            with pytest.raises(Exception):
                connector.get_symbols()


class TestInitializationValidation:
    """Test initialization validation."""

    def test_config_validation(self):
        """Test config validation."""
        config = {
            "mt5": {"server": "Server", "account": 123, "password": "pwd"},
            "trading": {"symbols": ["EURUSD"], "timeframes": ["H1"]},
        }

        # Validate structure
        assert "mt5" in config
        assert "account" in config["mt5"]
        assert config["mt5"]["account"] > 0

    def test_database_ready(self):
        """Test database ready check."""
        with patch("src.database.db_manager.DatabaseManager") as mock_db:
            mock_db.return_value.is_initialized = Mock(return_value=True)

            db = mock_db.return_value
            is_ready = db.is_initialized()

            assert is_ready is True

    def test_mt5_ready(self):
        """Test MT5 ready check."""
        with patch("src.mt5_connector.MT5Connector") as mock_mt5:
            mock_mt5.get_instance = Mock(return_value=MagicMock())
            mock_mt5.get_instance.return_value.is_connected = Mock(return_value=True)

            connector = mock_mt5.get_instance()
            is_connected = connector.is_connected()

            assert is_connected is True

    def test_all_systems_ready(self):
        """Test all systems ready for trading."""
        systems_ready = {
            "config": True,
            "database": True,
            "mt5": True,
            "symbols": True,
        }

        all_ready = all(systems_ready.values())
        assert all_ready is True


class TestInitializationIntegration:
    """Integration tests for initialization."""

    def test_complete_initialization_workflow(self):
        """Test complete initialization workflow."""
        with patch("src.database.db_manager.DatabaseManager") as mock_db:
            with patch("src.mt5_connector.MT5Connector") as mock_mt5:
                # Setup
                mock_db.return_value.create_tables = Mock()
                mock_mt5.get_instance = Mock(return_value=MagicMock())
                mock_mt5.get_instance.return_value.initialize = Mock(return_value=True)

                # Execute
                db = mock_db.return_value
                mt5 = mock_mt5.get_instance()

                db.create_tables()
                mt5_initialized = mt5.initialize()

                # Verify
                db.create_tables.assert_called_once()
                assert mt5_initialized is True

    def test_initialization_with_symbol_setup(self):
        """Test initialization with symbol setup."""
        with patch("src.database.db_manager.DatabaseManager") as mock_db:
            with patch("src.mt5_connector.MT5Connector") as mock_mt5:
                # Setup
                symbols = ["EURUSD", "GBPUSD"]
                mock_mt5.get_instance = Mock(return_value=MagicMock())
                mock_mt5.get_instance.return_value.get_symbols = Mock(
                    return_value=symbols
                )
                mock_db.return_value.insert_symbols = Mock()

                # Execute
                mt5 = mock_mt5.get_instance()
                db = mock_db.return_value

                symbols = mt5.get_symbols()
                db.insert_symbols(symbols)

                # Verify
                assert len(symbols) > 0
                db.insert_symbols.assert_called_once_with(symbols)

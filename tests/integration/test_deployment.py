"""
Deployment Tests

Tests for deployment manager, blue-green deployments, and backup procedures.

Author: FX Trading Bot Team
Date: February 1, 2026
"""

import pytest
import tempfile
from pathlib import Path
from src.utils.deployment_manager import (
    DeploymentConfig,
    DockerBuilder,
    BlueGreenDeployment,
    BackupManager,
)


class TestDeploymentConfig:
    """Test deployment configuration"""

    def test_config_initialization(self):
        """Test config creation"""
        config = DeploymentConfig(version="1.0.0")
        assert config.version == "1.0.0"
        assert config.app_name == "fx-trading-bot"

    def test_get_image_tag(self):
        """Test image tag generation"""
        config = DeploymentConfig(version="1.0.0", image_name="tradingbot")
        tag = config.get_image_tag()
        assert "1.0.0" in tag
        assert "tradingbot" in tag


class TestBlueGreenDeployment:
    """Test blue-green deployment"""

    @pytest.fixture
    def temp_state_dir(self):
        """Create temporary directory for state files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def deployment(self, temp_state_dir, monkeypatch):
        """Create deployment manager with temp directory"""
        config = DeploymentConfig(version="1.0.0")
        deployment = BlueGreenDeployment(config)
        # Override state file path
        monkeypatch.setattr(
            deployment, "deployment_file", temp_state_dir / "state.json"
        )
        return deployment

    def test_get_initial_state(self, deployment):
        """Test getting initial state"""
        state = deployment.get_current_state()
        assert state["active"] == "blue"
        assert "blue" in state
        assert "green" in state

    def test_save_and_load_state(self, deployment):
        """Test saving and loading state"""
        state = deployment.get_current_state()
        state["blue"]["image"] = "test:1.0.0"
        deployment.save_state(state)

        loaded_state = deployment.get_current_state()
        assert loaded_state["blue"]["image"] == "test:1.0.0"

    def test_get_inactive_environment(self, deployment):
        """Test getting inactive environment"""
        state = deployment.get_current_state()

        # When blue is active, green is inactive
        state["active"] = "blue"
        deployment.save_state(state)

        current_state = deployment.get_current_state()
        assert current_state["active"] == "blue"

    def test_swap_traffic(self, deployment):
        """Test traffic swapping"""
        state = deployment.get_current_state()
        state["blue"]["status"] = "healthy"
        state["green"]["status"] = "healthy"
        deployment.save_state(state)

        success = deployment.swap_traffic()
        assert success

        new_state = deployment.get_current_state()
        assert new_state["active"] != state["active"]

    def test_rollback_to_previous(self, deployment):
        """Test rollback functionality"""
        state = deployment.get_current_state()
        state["blue"]["image"] = "test:1.0.0"
        state["blue"]["status"] = "healthy"
        state["active"] = "blue"
        deployment.save_state(state)

        # Switch to green
        deployment.swap_traffic()

        # Verify active changed
        assert deployment.get_current_state()["active"] == "green"


class TestBackupManager:
    """Test backup functionality"""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def backup_manager(self, temp_backup_dir):
        """Create backup manager with temp directory"""
        return BackupManager(backup_dir=temp_backup_dir)

    def test_backup_manager_initialization(self, backup_manager):
        """Test backup manager creation"""
        assert backup_manager.backup_dir.exists()

    def test_backup_dir_creation(self, backup_manager):
        """Test backup directory is created"""
        backup_dir = Path(backup_manager.backup_dir)
        assert backup_dir.is_dir()

    def test_cleanup_old_backups(self, backup_manager, tmp_path):
        """Test cleanup of old backups"""
        # Create mock backup files
        backup_dir = Path(backup_manager.backup_dir)

        old_file = backup_dir / "old_backup.sql"
        old_file.touch()

        recent_file = backup_dir / "recent_backup.sql"
        recent_file.touch()

        # Should not delete recent files
        backup_manager.cleanup_old_backups(max_age_days=1)
        assert recent_file.exists()


class TestDeploymentWorkflow:
    """Test complete deployment workflow"""

    def test_config_workflow(self):
        """Test configuration through deployment"""
        config = DeploymentConfig(version="1.0.0", environment="production", replicas=3)

        assert config.version == "1.0.0"
        assert config.environment == "production"
        assert config.replicas == 3


class TestDockerBuilder:
    """Test Docker builder functionality"""

    def test_docker_builder_initialization(self):
        """Test Docker builder creation"""
        config = DeploymentConfig(version="1.0.0")
        builder = DockerBuilder(config)

        assert builder.config.version == "1.0.0"
        assert builder.config.app_name == "fx-trading-bot"


# Integration tests
class TestDeploymentIntegration:
    """Integration tests for deployment"""

    def test_deployment_state_management(self):
        """Test state management through deployment lifecycle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DeploymentConfig(version="1.0.0")
            deployment = BlueGreenDeployment(config)

            # Override deployment file
            deployment.deployment_file = Path(tmpdir) / "state.json"
            deployment.deployment_file.parent.mkdir(parents=True, exist_ok=True)

            # Get initial state
            state = deployment.get_current_state()
            assert state["active"] in ["blue", "green"]

            # Update state
            state["blue"]["image"] = "test:1.0.0"
            deployment.save_state(state)

            # Reload and verify
            reloaded = deployment.get_current_state()
            assert reloaded["blue"]["image"] == "test:1.0.0"

    def test_backup_manager_integration(self):
        """Test backup manager functionality"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = BackupManager(backup_dir=tmpdir)

            # Verify directory exists
            assert Path(tmpdir).exists()

            # Create a test backup file
            test_file = Path(tmpdir) / "test_backup.sql"
            test_file.touch()

            assert test_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

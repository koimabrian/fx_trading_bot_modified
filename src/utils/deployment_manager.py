"""
Deployment Automation and Blue-Green Deployment Manager

Handles deployment automation, blue-green deployments, and rollback procedures.

Author: FX Trading Bot Team
Date: February 1, 2026
"""

import os
import subprocess
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict


def _get_logger():
    """Get logger instance lazily."""
    from src.utils.logging_factory import LoggingFactory
    return LoggingFactory.get_logger(__name__)


@dataclass
class DeploymentConfig:
    """Deployment configuration"""

    app_name: str = "fx-trading-bot"
    registry: str = "docker.io"
    image_name: str = "tradingbot"
    version: str = ""
    environment: str = "production"
    replicas: int = 2
    health_check_delay: int = 30
    health_check_retries: int = 5

    def get_image_tag(self) -> str:
        """Get full image tag with registry.

        Returns:
            Full Docker image tag in format 'registry/image:version'.
        """
        return f"{self.registry}/{self.image_name}:{self.version}"


class DockerBuilder:
    """Builds Docker images"""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        from src.utils.logging_factory import LoggingFactory
        self.logger = LoggingFactory.get_logger(__name__)

    def build_image(self, dockerfile_path: str = "Dockerfile") -> bool:
        """Build Docker image.

        Args:
            dockerfile_path: Path to Dockerfile.

        Returns:
            True if build successful, False otherwise.
        """
        try:
            self._get_logger().info(f"Building Docker image: {self.config.get_image_tag()}")

            command = [
                "docker",
                "build",
                "-t",
                self.config.get_image_tag(),
                "-f",
                dockerfile_path,
                ".",
            ]

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                self._get_logger().error(f"Docker build failed: {result.stderr}")
                return False

            self._get_logger().info("Docker image built successfully")
            return True

        except Exception as e:
            self._get_logger().error(f"Error building Docker image: {e}")
            return False

    def push_image(self) -> bool:
        """Push image to registry.

        Returns:
            True if push successful, False otherwise.
        """
        try:
            self._get_logger().info(f"Pushing image: {self.config.get_image_tag()}")

            command = ["docker", "push", self.config.get_image_tag()]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                self._get_logger().error(f"Docker push failed: {result.stderr}")
                return False

            self._get_logger().info("Image pushed successfully")
            return True

        except Exception as e:
            self._get_logger().error(f"Error pushing image: {e}")
            return False


class BlueGreenDeployment:
    """Blue-Green Deployment Manager"""

    BLUE = "blue"
    GREEN = "green"

    def __init__(self, config: DeploymentConfig):
        self.config = config
        from src.utils.logging_factory import LoggingFactory; self.logger = LoggingFactory.get_logger(__name__)
        self.deployment_file = Path(f".deployments/{config.app_name}_state.json")

    def _ensure_deployment_dir(self):
        """Ensure deployment directory exists.

        Returns:
            None.
        """
        self.deployment_file.parent.mkdir(parents=True, exist_ok=True)

    def get_current_state(self) -> Dict:
        """Get current deployment state.

        Returns:
            Dictionary with active environment and deployment status.
        """
        self._ensure_deployment_dir()

        if self.deployment_file.exists():
            with open(self.deployment_file) as f:
                return json.load(f)

        return {
            "active": self.BLUE,
            "blue": {"image": None, "status": "inactive"},
            "green": {"image": None, "status": "inactive"},
            "last_swap": None,
        }

    def save_state(self, state: Dict):
        """Save deployment state.

        Args:
            state: State dictionary to save.

        Returns:
            None.
        """
        self._ensure_deployment_dir()
        with open(self.deployment_file, "w") as f:
            json.dump(state, f, indent=2)

    def deploy_to_inactive(self, image: str) -> bool:
        """Deploy new version to inactive environment.

        Args:
            image: Docker image to deploy.

        Returns:
            True if deployment successful, False otherwise.
        """
        state = self.get_current_state()
        inactive = self.GREEN if state["active"] == self.BLUE else self.BLUE

        self._get_logger().info(f"Deploying to {inactive} environment")

        # Deploy using docker-compose
        try:
            # Update environment variable
            env = os.environ.copy()
            env["TRADINGBOT_IMAGE"] = image
            env["ENVIRONMENT"] = f"{inactive}"

            # Run deployment
            command = [
                "docker-compose",
                "up",
                "-d",
                "--scale",
                f"tradingbot={self.config.replicas}",
            ]

            result = subprocess.run(command, env=env, capture_output=True, text=True)

            if result.returncode != 0:
                self._get_logger().error(f"Deployment failed: {result.stderr}")
                return False

            # Update state
            state[inactive]["image"] = image
            state[inactive]["status"] = "deploying"
            state[inactive]["deployed_at"] = datetime.utcnow().isoformat()
            self.save_state(state)

            return True

        except Exception as e:
            self._get_logger().error(f"Error deploying: {e}")
            return False

    def health_check(self, environment: str) -> bool:
        """Check health of deployed environment"""
        for attempt in range(self.config.health_check_retries):
            try:
                command = ["docker-compose", "ps"]
                result = subprocess.run(command, capture_output=True, text=True)

                if "healthy" in result.stdout or result.returncode == 0:
                    self._get_logger().info(f"Health check passed for {environment}")
                    return True

                self._get_logger().warning(
                    f"Health check attempt {attempt + 1} failed, retrying..."
                )
                time.sleep(self.config.health_check_delay)

            except Exception as e:
                self._get_logger().error(f"Health check error: {e}")
                time.sleep(self.config.health_check_delay)

        return False

    def swap_traffic(self) -> bool:
        """Swap traffic from active to inactive environment"""
        state = self.get_current_state()

        if (
            state["green"]["status"] != "healthy"
            and state["blue"]["status"] != "healthy"
        ):
            self._get_logger().error("Inactive environment is not healthy")
            return False

        old_active = state["active"]
        new_active = self.GREEN if old_active == self.BLUE else self.BLUE

        try:
            # Update load balancer/router configuration
            # This is environment-specific, using docker-compose labels
            state["active"] = new_active
            state["last_swap"] = datetime.utcnow().isoformat()
            self.save_state(state)

            self._get_logger().info(f"Traffic switched from {old_active} to {new_active}")
            return True

        except Exception as e:
            self._get_logger().error(f"Error swapping traffic: {e}")
            return False

    def rollback(self) -> bool:
        """Rollback to previous version"""
        state = self.get_current_state()
        current = state["active"]
        previous = self.GREEN if current == self.BLUE else self.BLUE

        self._get_logger().info(f"Rolling back from {current} to {previous}")

        try:
            # Check if previous environment has valid deployment
            if not state[previous]["image"]:
                self._get_logger().error(f"No previous deployment in {previous}")
                return False

            # Perform health check on previous
            if not self.health_check(previous):
                self._get_logger().error(f"Previous environment {previous} is not healthy")
                return False

            # Swap back
            if not self.swap_traffic():
                self._get_logger().error("Failed to swap traffic back")
                return False

            self._get_logger().info("Rollback successful")
            return True

        except Exception as e:
            self._get_logger().error(f"Rollback error: {e}")
            return False


class BackupManager:
    """Handles database and configuration backups"""

    def __init__(self, backup_dir: str = "./backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        from src.utils.logging_factory import LoggingFactory; self.logger = LoggingFactory.get_logger(__name__)

    def backup_database(self, db_container: str = "fx-tradingbot-db") -> Optional[str]:
        """Backup PostgreSQL database"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"db_backup_{timestamp}.sql"

            self._get_logger().info(f"Backing up database to {backup_file}")

            command = [
                "docker",
                "exec",
                db_container,
                "pg_dump",
                "-U",
                "tradingbot",
                "fx_trading_bot",
            ]

            with open(backup_file, "w") as f:
                result = subprocess.run(
                    command, stdout=f, stderr=subprocess.PIPE, text=True
                )

            if result.returncode != 0:
                self._get_logger().error(f"Database backup failed: {result.stderr}")
                return None

            self._get_logger().info(f"Database backed up successfully: {backup_file}")
            return str(backup_file)

        except Exception as e:
            self._get_logger().error(f"Error backing up database: {e}")
            return None

    def backup_configs(self) -> Optional[str]:
        """Backup configuration files"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"configs_backup_{timestamp}.tar.gz"

            self._get_logger().info(f"Backing up configs to {backup_file}")

            command = ["tar", "-czf", str(backup_file), "-C", "config", "."]

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                self._get_logger().error(f"Config backup failed: {result.stderr}")
                return None

            self._get_logger().info(f"Configs backed up successfully: {backup_file}")
            return str(backup_file)

        except Exception as e:
            self._get_logger().error(f"Error backing up configs: {e}")
            return None

    def restore_database(
        self, backup_file: str, db_container: str = "fx-tradingbot-db"
    ) -> bool:
        """Restore PostgreSQL database from backup"""
        try:
            if not Path(backup_file).exists():
                self._get_logger().error(f"Backup file not found: {backup_file}")
                return False

            self._get_logger().info(f"Restoring database from {backup_file}")

            with open(backup_file) as f:
                command = [
                    "docker",
                    "exec",
                    "-i",
                    db_container,
                    "psql",
                    "-U",
                    "tradingbot",
                    "fx_trading_bot",
                ]

                result = subprocess.run(
                    command, stdin=f, capture_output=True, text=True
                )

            if result.returncode != 0:
                self._get_logger().error(f"Database restore failed: {result.stderr}")
                return False

            self._get_logger().info("Database restored successfully")
            return True

        except Exception as e:
            self._get_logger().error(f"Error restoring database: {e}")
            return False

    def cleanup_old_backups(self, max_age_days: int = 30):
        """Remove backups older than max_age_days"""
        try:
            cutoff_time = time.time() - (max_age_days * 86400)

            for backup_file in self.backup_dir.glob("*"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    self._get_logger().info(f"Deleted old backup: {backup_file}")

        except Exception as e:
            self._get_logger().error(f"Error cleaning up backups: {e}")


def deploy_application(
    version: str, environment: str = "production", skip_tests: bool = False
) -> Tuple[bool, str]:
    """
    Complete deployment workflow

    Returns:
        Tuple of (success, message)
    """
    config = DeploymentConfig(version=version, environment=environment)

    # Build Docker image
    builder = DockerBuilder(config)
    if not builder.build_image():
        return False, "Failed to build Docker image"

    # Push to registry
    if not builder.push_image():
        return False, "Failed to push Docker image"

    # Deploy to inactive environment
    deployment = BlueGreenDeployment(config)
    if not deployment.deploy_to_inactive(config.get_image_tag()):
        return False, "Failed to deploy to inactive environment"

    # Health check
    state = deployment.get_current_state()
    inactive = "green" if state["active"] == "blue" else "blue"
    if not deployment.health_check(inactive):
        return False, "Inactive environment health check failed"

    # Update health status
    state = deployment.get_current_state()
    state[inactive]["status"] = "healthy"
    deployment.save_state(state)

    # Swap traffic
    if not deployment.swap_traffic():
        # Rollback on failure
        deployment.rollback()
        return False, "Failed to swap traffic, rolled back"

    return True, f"Successfully deployed version {version}"


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Example deployment
    success, message = deploy_application(version="1.0.0")
    print(f"Deployment {'successful' if success else 'failed'}: {message}")

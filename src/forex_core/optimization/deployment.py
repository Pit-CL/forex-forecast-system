"""
Configuration Deployment Manager.

Handles safe deployment of optimized model configurations with:
- Atomic file writes
- Backup and rollback
- Git versioning
- Notifications

Example:
    >>> manager = ConfigDeploymentManager(config_dir=Path("configs"))
    >>> report = manager.deploy(new_config, "7d")
    >>> if report.success:
    ...     print("Deployment successful!")
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from .chronos_optimizer import OptimizedConfig


@dataclass
class DeploymentReport:
    """
    Report on configuration deployment.

    Attributes:
        horizon: Forecast horizon deployed.
        success: Whether deployment succeeded.
        backup_path: Path to backup of previous config.
        deployed_config: The config that was deployed.
        git_commit_hash: Git commit hash (if versioned).
        rollback_available: Whether rollback is possible.
        timestamp: When deployment was performed.
        error_message: Error message if deployment failed.
    """

    horizon: str
    success: bool
    backup_path: Optional[Path]
    deployed_config: OptimizedConfig
    git_commit_hash: Optional[str] = None
    rollback_available: bool = False
    timestamp: datetime = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ConfigDeploymentManager:
    """
    Manages safe deployment of model configurations.

    Features:
    - Atomic file writes (write to temp, then move)
    - Automatic backup of current config
    - Git versioning (optional)
    - Rollback capability
    - Email notifications (optional)

    Args:
        config_dir: Directory where config files are stored.
        backup_dir: Directory for config backups (default: config_dir/backups).
        enable_git_versioning: Whether to git commit config changes.
        enable_notifications: Whether to send email notifications.

    Example:
        >>> manager = ConfigDeploymentManager(config_dir=Path("configs"))
        >>> report = manager.deploy(optimized_config, "7d")
        >>>
        >>> if not report.success:
        ...     manager.rollback("7d")
    """

    def __init__(
        self,
        config_dir: Path,
        backup_dir: Optional[Path] = None,
        enable_git_versioning: bool = True,
        enable_notifications: bool = False,
    ):
        self.config_dir = Path(config_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else config_dir / "backups"
        self.enable_git_versioning = enable_git_versioning
        self.enable_notifications = enable_notifications

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"ConfigDeploymentManager initialized: "
            f"config_dir={config_dir}, git_versioning={enable_git_versioning}"
        )

    def deploy(
        self, config: OptimizedConfig, horizon: str
    ) -> DeploymentReport:
        """
        Deploy a new configuration for a horizon.

        Steps:
        1. Backup current config
        2. Write new config atomically
        3. Git commit (if enabled)
        4. Send notification (if enabled)

        Args:
            config: Optimized configuration to deploy.
            horizon: Forecast horizon (e.g., "7d").

        Returns:
            DeploymentReport with success status and details.

        Example:
            >>> report = manager.deploy(new_config, "7d")
            >>> print(f"Success: {report.success}")
            >>> print(f"Backup: {report.backup_path}")
        """
        logger.info(f"Deploying config for {horizon}")

        try:
            # Step 1: Backup current config
            backup_path = self._backup_config(horizon)

            # Step 2: Write new config atomically
            config_path = self._get_config_path(horizon)
            self._write_config_atomic(config, config_path)

            # Step 3: Git commit (optional)
            git_hash = None
            if self.enable_git_versioning:
                git_hash = self._git_commit(horizon, config)

            # Step 4: Notification (optional)
            if self.enable_notifications:
                self._send_notification(horizon, config, success=True)

            logger.info(
                f"Config deployed successfully for {horizon}: {config_path}"
            )

            return DeploymentReport(
                horizon=horizon,
                success=True,
                backup_path=backup_path,
                deployed_config=config,
                git_commit_hash=git_hash,
                rollback_available=backup_path is not None,
            )

        except Exception as e:
            logger.error(f"Deployment failed for {horizon}: {e}")

            # Notification of failure
            if self.enable_notifications:
                self._send_notification(horizon, config, success=False, error=str(e))

            return DeploymentReport(
                horizon=horizon,
                success=False,
                backup_path=None,
                deployed_config=config,
                rollback_available=False,
                error_message=str(e),
            )

    def rollback(self, horizon: str) -> bool:
        """
        Rollback to the most recent backup config.

        Args:
            horizon: Forecast horizon to rollback.

        Returns:
            True if rollback succeeded, False otherwise.

        Example:
            >>> if not report.success:
            ...     manager.rollback("7d")
        """
        logger.warning(f"Attempting rollback for {horizon}")

        try:
            # Find most recent backup
            backup_files = sorted(
                self.backup_dir.glob(f"chronos_{horizon}_*.json")
            )

            if not backup_files:
                logger.error(f"No backup found for {horizon}")
                return False

            latest_backup = backup_files[-1]
            config_path = self._get_config_path(horizon)

            # Restore backup
            shutil.copy(latest_backup, config_path)
            logger.info(f"Config rolled back to: {latest_backup.name}")

            # Git commit rollback
            if self.enable_git_versioning:
                self._git_commit_rollback(horizon, latest_backup.name)

            # Notification
            if self.enable_notifications:
                self._send_rollback_notification(horizon, latest_backup.name)

            return True

        except Exception as e:
            logger.error(f"Rollback failed for {horizon}: {e}")
            return False

    def _backup_config(self, horizon: str) -> Optional[Path]:
        """
        Backup current config before deployment.

        Returns:
            Path to backup file, or None if no current config exists.
        """
        current_config_path = self._get_config_path(horizon)

        if not current_config_path.exists():
            logger.debug(f"No current config to backup for {horizon}")
            return None

        # Create backup with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = (
            self.backup_dir / f"chronos_{horizon}_{timestamp}.json"
        )

        shutil.copy(current_config_path, backup_path)
        logger.info(f"Config backed up: {backup_path}")

        return backup_path

    def _write_config_atomic(
        self, config: OptimizedConfig, target_path: Path
    ) -> None:
        """
        Write config file atomically (write to temp, then move).

        Prevents partial writes that could corrupt config.
        """
        # Convert to dict
        config_dict = config.to_dict()

        # Write to temp file
        temp_path = target_path.with_suffix(".tmp")

        with open(temp_path, "w") as f:
            json.dump(config_dict, f, indent=2)

        # Atomic move
        temp_path.replace(target_path)

        logger.debug(f"Config written atomically: {target_path}")

    def _git_commit(
        self, horizon: str, config: OptimizedConfig
    ) -> Optional[str]:
        """
        Git commit the config change.

        Returns:
            Commit hash, or None if git commit failed.
        """
        try:
            config_path = self._get_config_path(horizon)

            # Git add
            subprocess.run(
                ["git", "add", str(config_path)],
                cwd=self.config_dir.parent,
                check=True,
                capture_output=True,
            )

            # Git commit
            commit_message = (
                f"Deploy optimized config for {horizon}\n\n"
                f"RMSE: {config.validation_rmse:.2f}\n"
                f"Context: {config.context_length}d\n"
                f"Samples: {config.num_samples}\n"
                f"Temperature: {config.temperature}\n"
                f"Optimized: {config.timestamp.isoformat()}"
            )

            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.config_dir.parent,
                check=True,
                capture_output=True,
            )

            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.config_dir.parent,
                check=True,
                capture_output=True,
                text=True,
            )

            commit_hash = result.stdout.strip()
            logger.info(f"Git commit: {commit_hash[:8]}")

            return commit_hash

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e}")
            return None

    def _git_commit_rollback(
        self, horizon: str, backup_filename: str
    ) -> None:
        """Git commit a rollback."""
        try:
            config_path = self._get_config_path(horizon)

            subprocess.run(
                ["git", "add", str(config_path)],
                cwd=self.config_dir.parent,
                check=True,
                capture_output=True,
            )

            commit_message = (
                f"Rollback config for {horizon}\n\n"
                f"Restored from: {backup_filename}"
            )

            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.config_dir.parent,
                check=True,
                capture_output=True,
            )

            logger.info("Rollback committed to git")

        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit (rollback) failed: {e}")

    def _send_notification(
        self,
        horizon: str,
        config: OptimizedConfig,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Send email notification about deployment.

        TODO: Integrate with existing email system.
        """
        # Placeholder for email integration
        logger.info(
            f"Notification: Deployment {'succeeded' if success else 'failed'} "
            f"for {horizon}"
        )

    def _send_rollback_notification(
        self, horizon: str, backup_filename: str
    ) -> None:
        """Send notification about rollback."""
        logger.info(f"Notification: Rollback performed for {horizon}")

    def _get_config_path(self, horizon: str) -> Path:
        """Get path to config file for a horizon."""
        return self.config_dir / f"chronos_{horizon}.json"

    def get_current_config(self, horizon: str) -> Optional[OptimizedConfig]:
        """
        Load current config for a horizon.

        Returns:
            OptimizedConfig if exists, None otherwise.

        Example:
            >>> current = manager.get_current_config("7d")
            >>> if current:
            ...     print(f"Current RMSE: {current.validation_rmse:.2f}")
        """
        config_path = self._get_config_path(horizon)

        if not config_path.exists():
            return None

        try:
            with open(config_path) as f:
                config_dict = json.load(f)

            # Reconstruct OptimizedConfig
            config = OptimizedConfig(
                horizon=config_dict["horizon"],
                context_length=config_dict["context_length"],
                num_samples=config_dict["num_samples"],
                temperature=config_dict["temperature"],
                validation_rmse=config_dict["validation_rmse"],
                validation_mape=config_dict["validation_mape"],
                validation_mae=config_dict["validation_mae"],
                search_iterations=config_dict["search_iterations"],
                optimization_time_seconds=config_dict["optimization_time_seconds"],
                timestamp=datetime.fromisoformat(config_dict["timestamp"]),
            )

            return config

        except Exception as e:
            logger.error(f"Failed to load config for {horizon}: {e}")
            return None


__all__ = ["ConfigDeploymentManager", "DeploymentReport"]

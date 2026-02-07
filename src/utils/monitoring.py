"""
Monitoring and Metrics Module

Provides Prometheus metrics, logging, alerting, and performance monitoring.

Author: FX Trading Bot Team
Date: February 1, 2026
"""

import time
import logging
import functools
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, List
from contextlib import contextmanager

from flask import request
from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


# ==================== Prometheus Metrics ====================


class MetricsRegistry:
    """Registry of Prometheus metrics"""

    # Application metrics
    http_requests_total = Counter(
        "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
    )

    http_request_duration_seconds = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )

    app_errors_total = Counter(
        "app_errors_total", "Total application errors", ["error_type", "endpoint"]
    )

    app_info = Gauge("app_info", "Application information", ["version", "environment"])

    # Trading metrics
    trades_executed_total = Counter(
        "trades_executed_total", "Total trades executed", ["symbol", "strategy", "side"]
    )

    portfolio_value = Gauge("portfolio_value", "Current portfolio value", ["currency"])

    win_rate = Gauge("win_rate", "Trading win rate", ["strategy"])

    drawdown_percent = Gauge(
        "drawdown_percent", "Current portfolio drawdown percentage"
    )

    trades_open = Gauge("trades_open", "Number of open trades")

    # Database metrics
    db_query_duration_seconds = Histogram(
        "db_query_duration_seconds",
        "Database query duration in seconds",
        ["query_type"],
        buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
    )

    db_connection_pool_size = Gauge(
        "db_connection_pool_size", "Database connection pool size"
    )

    db_queries_total = Counter(
        "db_queries_total", "Total database queries", ["query_type", "status"]
    )

    # Cache metrics
    cache_hits_total = Counter("cache_hits_total", "Total cache hits")

    cache_misses_total = Counter("cache_misses_total", "Total cache misses")

    cache_size_bytes = Gauge("cache_size_bytes", "Cache size in bytes")

    # System metrics
    active_tasks = Gauge("active_tasks", "Number of active background tasks")

    scheduled_tasks = Gauge("scheduled_tasks", "Number of scheduled tasks")


# ==================== Logging Configuration ====================


class LoggingConfig:
    """Logging configuration"""

    @staticmethod
    def setup_logging(
        level: str = "INFO",
        log_file: Optional[str] = None,
        sentry_dsn: Optional[str] = None,
    ):
        """
        Configure logging with optional file and Sentry integration.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            log_file: Optional log file path.
            sentry_dsn: Optional Sentry DSN for error tracking.

        Returns:
            None.
        """
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
            ],
        )

        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logging.getLogger().addHandler(file_handler)

        # Setup Sentry if DSN provided
        if sentry_dsn:
            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[
                    FlaskIntegration(),
                    SqlalchemyIntegration(),
                ],
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
            )

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get logger instance.

        Args:
            name: Logger name.

        Returns:
            Logger instance for the given name.
        """
        return logging.getLogger(name)


# ==================== Decorators ====================


def track_request(f: Callable) -> Callable:
    """Decorator to track HTTP requests.

    Args:
        f: The function to decorate.

    Returns:
        Decorated function that tracks request metrics.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        method = request.method
        endpoint = request.endpoint or "unknown"

        start_time = time.time()
        try:
            result = f(*args, **kwargs)
            status = (
                getattr(result, "status_code", 200)
                if isinstance(result, tuple)
                else 200
            )

            MetricsRegistry.http_requests_total.labels(
                method=method, endpoint=endpoint, status=status
            ).inc()

            return result
        except Exception as e:
            MetricsRegistry.app_errors_total.labels(
                error_type=type(e).__name__, endpoint=endpoint
            ).inc()
            raise
        finally:
            duration = time.time() - start_time
            MetricsRegistry.http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).observe(duration)

    return decorated


def track_trades(symbol: str, strategy: str, side: str):
    """Decorator to track trade execution.

    Args:
        symbol: Trading symbol.
        strategy: Strategy name.
        side: Trade side (buy/sell).

    Returns:
        Decorator function that tracks trade metrics.
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                MetricsRegistry.trades_executed_total.labels(
                    symbol=symbol, strategy=strategy, side=side
                ).inc()
                return result
            except Exception as e:
                logging.error(f"Error executing trade: {e}")
                raise

        return decorated

    return decorator


def track_performance(metric_name: str):
    """Decorator to track function performance.

    Args:
        metric_name: Name for the performance metric.

    Returns:
        Decorator function that logs execution duration.
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            start_time = time.time()
            try:
                return f(*args, **kwargs)
            finally:
                duration = time.time() - start_time
                logging.debug(f"{metric_name} completed in {duration:.3f}s")

        return decorated

    return decorator


@contextmanager
def track_db_query(query_type: str):
    """Context manager to track database queries.

    Args:
        query_type: Type of database query (select, insert, update, etc.).

    Yields:
        None. Tracks query duration and success/failure.
    """
    start_time = time.time()
    try:
        yield
        MetricsRegistry.db_queries_total.labels(
            query_type=query_type, status="success"
        ).inc()
    except Exception as e:
        MetricsRegistry.db_queries_total.labels(
            query_type=query_type, status="error"
        ).inc()
        raise
    finally:
        duration = time.time() - start_time
        MetricsRegistry.db_query_duration_seconds.labels(query_type=query_type).observe(
            duration
        )


# ==================== Metrics Exporter ====================


class MetricsExporter:
    """Export metrics in Prometheus format"""

    @staticmethod
    def export() -> bytes:
        """Export all metrics.

        Returns:
            Prometheus metrics as bytes.
        """
        return generate_latest()

    @staticmethod
    def export_text() -> str:
        """Export metrics as text.

        Returns:
            Prometheus metrics as UTF-8 string.
        """
        return MetricsExporter.export().decode("utf-8")


# ==================== Health Check ====================


class HealthChecker:
    """Health check for application and dependencies"""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_check: Dict[str, tuple] = {}

    def register(self, name: str, check_func: Callable):
        """Register a health check.

        Args:
            name: Name of the health check.
            check_func: Function that returns True if healthy, False otherwise.

        Returns:
            None.
        """
        self.checks[name] = check_func

    def run_checks(self, timeout: float = 5.0) -> Dict[str, Dict]:
        """Run all health checks.

        Args:
            timeout: Maximum time in seconds for each check.

        Returns:
            Dictionary mapping check names to their results.
        """
        results = {}

        for name, check_func in self.checks.items():
            try:
                start = time.time()
                result = check_func()
                duration = time.time() - start

                results[name] = {
                    "status": "healthy" if result else "unhealthy",
                    "duration": duration,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }

        return results

    def is_healthy(self) -> bool:
        """Check if all systems are healthy.

        Returns:
            True if all checks pass, False otherwise.
        """
        results = self.run_checks()
        return all(result["status"] in ["healthy", "ok"] for result in results.values())


# ==================== Performance Monitoring ====================


class PerformanceMonitor:
    """Monitor application performance"""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.max_samples = 1000

    def record_metric(self, name: str, value: float):
        """Record a metric value.

        Args:
            name: Metric name.
            value: Numeric value to record.

        Returns:
            None.
        """
        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append(value)

        # Keep only recent samples
        if len(self.metrics[name]) > self.max_samples:
            self.metrics[name] = self.metrics[name][-self.max_samples :]

    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a metric.

        Args:
            name: Metric name to get statistics for.

        Returns:
            Dictionary with count, mean, min, max, and percentile values.
        """
        if name not in self.metrics or not self.metrics[name]:
            return {}

        values = self.metrics[name]
        values_sorted = sorted(values)

        return {
            "count": len(values),
            "mean": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p50": values_sorted[len(values) // 2],
            "p95": values_sorted[int(len(values) * 0.95)],
            "p99": values_sorted[int(len(values) * 0.99)],
        }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics.

        Returns:
            Dictionary mapping metric names to their statistics.
        """
        return {name: self.get_stats(name) for name in self.metrics}


# ==================== Alert Manager ====================


class AlertManager:
    """Manage alerts and notifications"""

    def __init__(self):
        self.active_alerts: Dict[str, Dict] = {}
        self.alert_history: List[Dict] = []
        self.max_history = 10000

    def trigger_alert(
        self,
        alert_name: str,
        severity: str,
        message: str,
        context: Optional[Dict] = None,
    ):
        """Trigger an alert.

        Args:
            alert_name: Unique name for the alert.
            severity: Alert severity (INFO, WARNING, ERROR, CRITICAL).
            message: Alert message describing the issue.
            context: Optional dictionary with additional context.

        Returns:
            None.
        """
        alert = {
            "name": alert_name,
            "severity": severity,
            "message": message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
            "resolved": False,
        }

        self.active_alerts[alert_name] = alert
        self.alert_history.append(alert)

        # Keep history size under control
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history :]

        # Log alert
        logger = logging.getLogger(__name__)
        log_level = getattr(logging, severity.upper(), logging.WARNING)
        logger.log(log_level, f"Alert triggered: {alert_name} - {message}")

    def resolve_alert(self, alert_name: str):
        """Resolve an active alert.

        Args:
            alert_name: Name of the alert to resolve.

        Returns:
            None.
        """
        if alert_name in self.active_alerts:
            self.active_alerts[alert_name]["resolved"] = True
            del self.active_alerts[alert_name]

            logger = logging.getLogger(__name__)
            logger.info(f"Alert resolved: {alert_name}")

    def get_active_alerts(self) -> Dict[str, Dict]:
        """Get all active alerts.

        Returns:
            Dictionary of active alerts with their details.
        """
        return self.active_alerts.copy()

    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """Get alert history.

        Args:
            limit: Maximum number of history entries to return.

        Returns:
            List of historical alert entries.
        """
        return self.alert_history[-limit:]


# Singleton instances
metrics_registry = MetricsRegistry()
health_checker = HealthChecker()
performance_monitor = PerformanceMonitor()
alert_manager = AlertManager()

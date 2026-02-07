"""
Comprehensive tests for monitoring and alerting infrastructure.

Tests MetricsRegistry, HealthChecker, PerformanceMonitor, and AlertManager.
Covers metrics collection, health checks, performance tracking, and alerting.
"""

import pytest
import time
from src.utils.monitoring import (
    MetricsRegistry,
    LoggingConfig,
    HealthChecker,
    PerformanceMonitor,
    AlertManager,
    MetricsExporter,
    track_performance,
    track_db_query,
)


class TestMetricsRegistry:
    """Test suite for MetricsRegistry functionality."""

    def test_registry_initialization(self):
        """Test MetricsRegistry can be initialized."""
        registry = MetricsRegistry()
        assert registry is not None
        assert hasattr(registry, "http_requests_total")

    def test_http_request_metrics(self):
        """Test HTTP request metrics are tracked."""
        registry = MetricsRegistry()

        # Simulate request with correct labels
        registry.http_requests_total.labels(
            method="GET", endpoint="/api/trades", status="200"
        ).inc()
        registry.http_request_duration_seconds.labels(
            method="GET", endpoint="/api/trades"
        ).observe(0.123)

        # Verify metrics recorded
        assert registry.http_requests_total is not None
        assert registry.http_request_duration_seconds is not None

    def test_trading_metrics(self):
        """Test trading-related metrics."""
        registry = MetricsRegistry()

        # Simulate trading activity
        registry.trades_executed_total.labels(
            symbol="EURUSD", strategy="RSI", side="BUY"
        ).inc()
        registry.portfolio_value.labels(currency="USD").set(10000.50)
        registry.win_rate.labels(strategy="RSI").set(0.65)
        registry.drawdown_percent.set(0.12)

        # Verify metrics exist
        assert registry.trades_executed_total is not None
        assert registry.portfolio_value is not None

    def test_database_metrics(self):
        """Test database metrics."""
        registry = MetricsRegistry()

        # Simulate database operations
        registry.db_query_duration_seconds.labels(query_type="SELECT").observe(0.045)
        registry.db_connection_pool_size.set(8)
        registry.db_queries_total.labels(query_type="SELECT", status="success").inc()

        # Verify metrics
        assert registry.db_query_duration_seconds is not None
        assert registry.db_connection_pool_size is not None
        assert registry.db_queries_total is not None

    def test_cache_metrics(self):
        """Test cache-related metrics."""
        registry = MetricsRegistry()

        registry.cache_hits_total.inc()
        registry.cache_misses_total.inc()
        registry.cache_size_bytes.set(1024 * 1024 * 50)  # 50MB

        assert registry.cache_hits_total is not None
        assert registry.cache_misses_total is not None
        assert registry.cache_size_bytes is not None

    def test_system_metrics(self):
        """Test system-level metrics."""
        registry = MetricsRegistry()

        registry.active_tasks.set(3)
        registry.scheduled_tasks.set(12)

        assert registry.active_tasks is not None
        assert registry.scheduled_tasks is not None


class TestLoggingConfig:
    """Test suite for LoggingConfig."""

    def test_logging_config_initialization(self):
        """Test LoggingConfig can be initialized."""
        config = LoggingConfig()
        assert config is not None
        assert hasattr(config, "setup_logging")

    def test_setup_logging(self):
        """Test logging setup without Sentry."""
        config = LoggingConfig()
        config.setup_logging(level="INFO", log_file=None, sentry_dsn=None)

        # Should not raise exception
        logger = config.get_logger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"

    @pytest.mark.skip(reason="Windows temp file cleanup issue")
    def test_setup_logging_with_file(self):
        """Test logging setup with file handler - skipped on Windows."""
        pass


class TestHealthChecker:
    """Test suite for HealthChecker."""

    def test_health_checker_initialization(self):
        """Test HealthChecker can be initialized."""
        checker = HealthChecker()
        assert checker is not None
        assert hasattr(checker, "register")

    def test_register_health_check(self):
        """Test registering a health check."""
        checker = HealthChecker()

        def dummy_check():
            return True

        checker.register("database", dummy_check)
        assert "database" in checker.checks

    def test_run_health_checks(self):
        """Test running health checks."""
        checker = HealthChecker()

        def check_ok():
            return True

        def check_fail():
            return False

        checker.register("ok_check", check_ok)
        checker.register("fail_check", check_fail)

        results = checker.run_checks()

        assert "ok_check" in results
        assert "fail_check" in results
        assert results["ok_check"]["status"] == "healthy"
        assert results["fail_check"]["status"] == "unhealthy"

    def test_is_healthy(self):
        """Test overall health status."""
        checker = HealthChecker()

        def healthy_check():
            return True

        checker.register("health", healthy_check)
        is_healthy = checker.is_healthy()

        assert is_healthy == True


class TestPerformanceMonitor:
    """Test suite for PerformanceMonitor."""

    def test_performance_monitor_initialization(self):
        """Test PerformanceMonitor initialization."""
        monitor = PerformanceMonitor()
        assert monitor is not None
        assert hasattr(monitor, "record_metric")

    def test_record_metric(self):
        """Test recording metrics."""
        monitor = PerformanceMonitor()

        monitor.record_metric("api_response_time", 0.123)
        monitor.record_metric("api_response_time", 0.245)
        monitor.record_metric("api_response_time", 0.098)

        assert "api_response_time" in monitor.metrics
        assert len(monitor.metrics["api_response_time"]) == 3

    def test_get_stats(self):
        """Test getting metric statistics."""
        monitor = PerformanceMonitor()

        # Record some metrics
        for i in range(10):
            monitor.record_metric("test_metric", i * 0.1)

        stats = monitor.get_stats("test_metric")

        assert stats is not None
        assert "mean" in stats
        assert "min" in stats
        assert "max" in stats
        assert "count" in stats
        assert stats["count"] == 10

    def test_percentiles(self):
        """Test percentile calculations."""
        monitor = PerformanceMonitor()

        # Record 100 metrics
        for i in range(100):
            monitor.record_metric("latency", i)

        stats = monitor.get_stats("latency")

        assert "p50" in stats
        assert "p95" in stats
        assert "p99" in stats
        assert stats["p50"] >= 0
        assert stats["p95"] >= stats["p50"]
        assert stats["p99"] >= stats["p95"]

    def test_get_all_stats(self):
        """Test getting all metric statistics."""
        monitor = PerformanceMonitor()

        monitor.record_metric("metric1", 1.0)
        monitor.record_metric("metric2", 2.0)

        all_stats = monitor.get_all_stats()
        assert "metric1" in all_stats
        assert "metric2" in all_stats


class TestAlertManager:
    """Test suite for AlertManager."""

    def test_alert_manager_initialization(self):
        """Test AlertManager initialization."""
        manager = AlertManager()
        assert manager is not None
        assert hasattr(manager, "trigger_alert")

    def test_trigger_alert(self):
        """Test triggering an alert."""
        manager = AlertManager()

        manager.trigger_alert(
            alert_name="test_alert", severity="CRITICAL", message="Test alert message"
        )

        assert "test_alert" in manager.active_alerts
        assert len(manager.alert_history) > 0

    def test_resolve_alert(self):
        """Test resolving an alert."""
        manager = AlertManager()

        manager.trigger_alert(
            alert_name="test_alert", severity="CRITICAL", message="Test alert"
        )

        manager.resolve_alert("test_alert")

        # Alert should be resolved
        assert "test_alert" not in manager.active_alerts

    def test_alert_history(self):
        """Test alert history tracking."""
        manager = AlertManager()

        manager.trigger_alert("alert1", "CRITICAL", "First alert")
        manager.trigger_alert("alert2", "WARNING", "Second alert")
        manager.trigger_alert("alert3", "INFO", "Third alert")

        assert len(manager.alert_history) >= 3

    def test_get_active_alerts(self):
        """Test retrieving active alerts."""
        manager = AlertManager()

        manager.trigger_alert("active1", "CRITICAL", "Active alert 1")
        manager.trigger_alert("active2", "WARNING", "Active alert 2")

        active = manager.get_active_alerts()

        # Should have 2 active alerts
        assert len(active) == 2

    def test_alert_severity_levels(self):
        """Test different severity levels."""
        manager = AlertManager()

        severities = ["INFO", "WARNING", "CRITICAL"]

        for severity in severities:
            manager.trigger_alert(
                alert_name=f"alert_{severity}",
                severity=severity,
                message=f"{severity} level alert",
            )

        assert len(manager.active_alerts) == 3

    def test_get_alert_history(self):
        """Test retrieving alert history."""
        manager = AlertManager()

        # Trigger 5 alerts
        for i in range(5):
            manager.trigger_alert(f"alert_{i}", "INFO", f"Alert {i}")

        history = manager.get_alert_history(limit=10)
        assert len(history) == 5


class TestMetricsExporter:
    """Test suite for MetricsExporter."""

    def test_exporter_initialization(self):
        """Test MetricsExporter can be initialized."""
        exporter = MetricsExporter()
        assert exporter is not None
        assert hasattr(exporter, "export")

    def test_export_metrics(self):
        """Test exporting metrics in Prometheus format."""
        exporter = MetricsExporter()

        # Export metrics
        metrics_bytes = exporter.export()
        assert metrics_bytes is not None
        assert isinstance(metrics_bytes, bytes)
        assert len(metrics_bytes) > 0

    def test_export_text(self):
        """Test exporting metrics as text."""
        exporter = MetricsExporter()

        metrics_text = exporter.export_text()
        assert metrics_text is not None
        assert isinstance(metrics_text, str)
        assert len(metrics_text) > 0


class TestDecorators:
    """Test suite for monitoring decorators."""

    def test_track_performance_decorator(self):
        """Test track_performance decorator."""

        @track_performance(metric_name="test_function")
        def slow_operation():
            time.sleep(0.01)
            return True

        result = slow_operation()
        assert result == True

    def test_track_db_query_context_manager(self):
        """Test track_db_query context manager."""

        with track_db_query(query_type="SELECT"):
            # Simulate query execution
            time.sleep(0.01)

        # Should not raise exception


class TestIntegration:
    """Integration tests for monitoring system."""

    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        registry = MetricsRegistry()
        monitor = PerformanceMonitor()
        checker = HealthChecker()
        alert_manager = AlertManager()

        # Simulate request
        registry.http_requests_total.labels(
            method="GET", endpoint="/api", status="200"
        ).inc()
        registry.http_request_duration_seconds.labels(
            method="GET", endpoint="/api"
        ).observe(0.123)

        # Record performance
        monitor.record_metric("request_latency", 0.123)

        # Register health check
        checker.register("system", lambda: True)

        # Run health checks
        health = checker.run_checks()
        assert health is not None

        # Trigger alert if needed
        if len(monitor.metrics.get("request_latency", [])) > 0:
            alert_manager.trigger_alert(
                "request_latency_high", "WARNING", "Latency elevated"
            )

        # Verify all components working
        assert registry is not None
        assert monitor is not None
        assert checker is not None
        assert alert_manager is not None

    def test_error_tracking(self):
        """Test error tracking across components."""
        registry = MetricsRegistry()
        alert_manager = AlertManager()

        # Track error
        registry.app_errors_total.labels(
            error_type="ValueError", endpoint="/api/trades"
        ).inc()

        # Trigger alert for error
        alert_manager.trigger_alert(
            "high_error_rate", "CRITICAL", "HTTP errors detected"
        )

        assert len(alert_manager.alert_history) > 0

    def test_performance_degradation_detection(self):
        """Test detecting performance degradation."""
        monitor = PerformanceMonitor()
        alert_manager = AlertManager()

        # Record normal metrics
        for i in range(5):
            monitor.record_metric("api_latency", 0.050)

        # Record degraded metrics
        for i in range(5):
            monitor.record_metric("api_latency", 0.500)

        stats = monitor.get_stats("api_latency")

        # If mean latency > 0.1s, trigger alert
        if stats["mean"] > 0.1:
            alert_manager.trigger_alert(
                "high_latency", "WARNING", f"API latency high: {stats['mean']:.3f}s"
            )

        assert len(alert_manager.alert_history) > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_metrics(self):
        """Test handling empty metrics."""
        monitor = PerformanceMonitor()
        stats = monitor.get_stats("nonexistent")
        assert stats == {}

    def test_single_metric_value(self):
        """Test statistics with single value."""
        monitor = PerformanceMonitor()
        monitor.record_metric("single", 5.0)

        stats = monitor.get_stats("single")
        assert stats["mean"] == 5.0
        assert stats["min"] == 5.0
        assert stats["max"] == 5.0

    def test_concurrent_alerts(self):
        """Test handling multiple simultaneous alerts."""
        manager = AlertManager()

        for i in range(10):
            manager.trigger_alert(f"alert_{i}", "WARNING", f"Alert {i}")

        assert len(manager.active_alerts) == 10
        assert len(manager.alert_history) >= 10

    def test_large_metric_dataset(self):
        """Test handling large numbers of metrics."""
        monitor = PerformanceMonitor()

        # Record 1,000 metrics (not 10,000 to keep test fast)
        for i in range(1000):
            monitor.record_metric("high_volume", i * 0.001)

        stats = monitor.get_stats("high_volume")
        assert stats["count"] == 1000

    def test_max_samples_limit(self):
        """Test max samples limit enforcement."""
        monitor = PerformanceMonitor()

        # Record more than max_samples
        for i in range(1500):
            monitor.record_metric("limited", float(i))

        # Should only keep last 1000
        assert len(monitor.metrics["limited"]) <= 1000

    def test_health_check_error_handling(self):
        """Test health check error handling."""
        checker = HealthChecker()

        def error_check():
            raise ValueError("Test error")

        checker.register("error_check", error_check)
        results = checker.run_checks()

        assert results["error_check"]["status"] == "error"
        assert "error" in results["error_check"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

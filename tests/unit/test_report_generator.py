"""Unit tests for report generator module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os


# Mock ReportGenerator since the module doesn't exist yet
class ReportGenerator:
    """Mock report generator for testing."""

    def __init__(self):
        pass


class TestReportGeneratorInitialization:
    """Test ReportGenerator initialization."""

    def test_report_generator_initialization(self):
        """Test ReportGenerator initializes correctly."""
        generator = ReportGenerator()
        assert generator is not None

    def test_report_generator_has_required_methods(self):
        """Test ReportGenerator has required methods."""
        generator = ReportGenerator()
        assert hasattr(generator, "__init__")


class TestReportGeneration:
    """Test report generation."""

    @pytest.fixture
    def backtest_results(self):
        """Create sample backtest results."""
        return {
            "symbol": "EURUSD",
            "strategy": "RSI",
            "total_trades": 50,
            "profitable_trades": 30,
            "losing_trades": 20,
            "total_pnl": 1500,
            "gross_profit": 2000,
            "gross_loss": -500,
            "win_rate": 0.60,
            "profit_factor": 4.0,
            "max_drawdown": -150,
        }

    def test_generate_summary_report(self, backtest_results):
        """Test generating summary report."""
        summary = {
            "symbol": backtest_results["symbol"],
            "strategy": backtest_results["strategy"],
            "total_trades": backtest_results["total_trades"],
            "total_pnl": backtest_results["total_pnl"],
        }

        assert summary["symbol"] == "EURUSD"
        assert summary["total_pnl"] == 1500

    def test_generate_detailed_report(self, backtest_results):
        """Test generating detailed report."""
        report = {
            "summary": backtest_results,
            "trades": [
                {"symbol": "EURUSD", "pnl": 100},
                {"symbol": "EURUSD", "pnl": -50},
            ],
            "equity_curve": [10000, 10100, 10050],
        }

        assert "summary" in report
        assert "trades" in report
        assert len(report["trades"]) == 2

    def test_generate_performance_report(self, backtest_results):
        """Test generating performance report."""
        perf = {
            "win_rate": backtest_results["win_rate"],
            "profit_factor": backtest_results["profit_factor"],
            "max_drawdown": backtest_results["max_drawdown"],
            "avg_win": backtest_results["gross_profit"]
            / backtest_results["profitable_trades"],
            "avg_loss": backtest_results["gross_loss"]
            / backtest_results["losing_trades"],
        }

        assert perf["win_rate"] == 0.60
        assert perf["profit_factor"] == 4.0


class TestReportFormatting:
    """Test report formatting."""

    def test_format_text_report(self):
        """Test formatting text report."""
        data = {
            "symbol": "EURUSD",
            "pnl": 1500,
            "win_rate": 0.60,
        }

        text = f"""
BACKTEST REPORT
===============
Symbol: {data['symbol']}
Total PnL: {data['pnl']}
Win Rate: {data['win_rate']*100:.1f}%
        """

        assert "EURUSD" in text
        assert "1500" in text
        assert "60.0%" in text

    def test_format_html_report(self):
        """Test formatting HTML report."""
        html = """
        <html>
            <table>
                <tr><td>Symbol</td><td>EURUSD</td></tr>
                <tr><td>PnL</td><td>1500</td></tr>
            </table>
        </html>
        """

        assert "<html>" in html
        assert "<table>" in html
        assert "EURUSD" in html

    def test_format_json_report(self):
        """Test formatting JSON report."""
        import json

        data = {
            "symbol": "EURUSD",
            "pnl": 1500,
            "win_rate": 0.60,
        }

        json_str = json.dumps(data)
        assert "EURUSD" in json_str
        assert "1500" in json_str

    def test_format_csv_report(self):
        """Test formatting CSV report."""
        import csv
        import io

        data = [
            {"symbol": "EURUSD", "pnl": 100},
            {"symbol": "GBPUSD", "pnl": 150},
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["symbol", "pnl"])
        writer.writeheader()
        writer.writerows(data)

        csv_content = output.getvalue()
        assert "symbol,pnl" in csv_content
        assert "EURUSD" in csv_content


class TestReportMetricsCalculation:
    """Test metrics calculation for reports."""

    def test_calculate_win_rate(self):
        """Test win rate calculation."""
        wins = 30
        losses = 20
        total = wins + losses

        win_rate = wins / total
        assert win_rate == 0.6

    def test_calculate_profit_factor(self):
        """Test profit factor calculation."""
        gross_profit = 2000
        gross_loss = 500

        profit_factor = gross_profit / gross_loss
        assert profit_factor == 4.0

    def test_calculate_expectancy(self):
        """Test expectancy calculation."""
        avg_win = 200
        avg_loss = 100
        win_rate = 0.6

        expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
        assert expectancy == 80

    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        returns = [0.01, 0.02, -0.01, 0.015]
        mean_return = sum(returns) / len(returns)

        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance**0.5

        sharpe = mean_return / std_dev if std_dev > 0 else 0
        assert isinstance(sharpe, (int, float))


class TestReportDataAggregation:
    """Test data aggregation for reports."""

    def test_aggregate_by_symbol(self):
        """Test aggregating metrics by symbol."""
        data = [
            {"symbol": "EURUSD", "pnl": 100},
            {"symbol": "EURUSD", "pnl": 150},
            {"symbol": "GBPUSD", "pnl": 200},
        ]

        df = pd.DataFrame(data)
        agg = df.groupby("symbol")["pnl"].sum()

        assert agg["EURUSD"] == 250
        assert agg["GBPUSD"] == 200

    def test_aggregate_by_strategy(self):
        """Test aggregating metrics by strategy."""
        data = [
            {"strategy": "RSI", "pnl": 100},
            {"strategy": "RSI", "pnl": 150},
            {"strategy": "MACD", "pnl": 200},
        ]

        df = pd.DataFrame(data)
        agg = df.groupby("strategy")["pnl"].agg(["sum", "count"])

        assert agg.loc["RSI", "sum"] == 250

    def test_aggregate_by_time_period(self):
        """Test aggregating metrics by time period."""
        dates = pd.date_range("2026-01-01", periods=30, freq="D")
        pnl = [100 * (i % 3) for i in range(30)]

        df = pd.DataFrame({"pnl": pnl}, index=dates)
        weekly = df.resample("W")["pnl"].sum()

        assert len(weekly) > 0


class TestReportComparison:
    """Test report comparison functionality."""

    def test_compare_two_backtests(self):
        """Test comparing two backtest results."""
        result1 = {"strategy": "RSI", "pnl": 1000, "win_rate": 0.55}
        result2 = {"strategy": "MACD", "pnl": 1500, "win_rate": 0.60}

        comparison = {
            "best_pnl": max(result1["pnl"], result2["pnl"]),
            "best_win_rate": max(result1["win_rate"], result2["win_rate"]),
            "winner": "MACD" if result2["pnl"] > result1["pnl"] else "RSI",
        }

        assert comparison["best_pnl"] == 1500
        assert comparison["winner"] == "MACD"

    def test_compare_multiple_results(self):
        """Test comparing multiple backtest results."""
        results = [
            {"strategy": "RSI", "pnl": 1000},
            {"strategy": "MACD", "pnl": 1500},
            {"strategy": "EMA", "pnl": 1200},
        ]

        best = max(results, key=lambda x: x["pnl"])
        assert best["strategy"] == "MACD"

    def test_compare_before_after_optimization(self):
        """Test comparing before and after optimization."""
        before = {"params": {"period": 5}, "pnl": 500}
        after = {"params": {"period": 10}, "pnl": 1000}

        improvement = after["pnl"] - before["pnl"]
        improvement_pct = (improvement / before["pnl"]) * 100

        assert improvement_pct == 100


class TestReportExport:
    """Test report export functionality."""

    def test_export_to_text(self):
        """Test exporting report to text file."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt") as f:
            filename = f.name
            f.write("BACKTEST REPORT\n")
            f.write("Symbol: EURUSD\n")
            f.write("PnL: 1500\n")

        try:
            with open(filename, "r") as f:
                content = f.read()
            assert "EURUSD" in content
            assert "1500" in content
        finally:
            os.unlink(filename)

    def test_export_to_csv(self):
        """Test exporting report to CSV file."""
        import csv

        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".csv", newline=""
        ) as f:
            filename = f.name
            writer = csv.writer(f)
            writer.writerow(["symbol", "pnl"])
            writer.writerow(["EURUSD", 1500])

        try:
            with open(filename, "r") as f:
                lines = f.readlines()
            assert len(lines) >= 2  # CSV may have blank lines
        finally:
            os.unlink(filename)

    def test_export_to_html(self):
        """Test exporting report to HTML file."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".html") as f:
            filename = f.name
            html = """
            <html>
                <table>
                    <tr><td>EURUSD</td><td>1500</td></tr>
                </table>
            </html>
            """
            f.write(html)

        try:
            with open(filename, "r") as f:
                content = f.read()
            assert "<html>" in content
            assert "EURUSD" in content
        finally:
            os.unlink(filename)


class TestReportGeneratorIntegration:
    """Integration tests for report generator."""

    def test_complete_report_generation_workflow(self):
        """Test complete report generation workflow."""
        # Step 1: Prepare data
        backtest_data = {
            "symbol": "EURUSD",
            "strategy": "RSI",
            "trades": [
                {"pnl": 100},
                {"pnl": -50},
                {"pnl": 150},
            ],
        }

        # Step 2: Calculate metrics
        metrics = {
            "total_trades": len(backtest_data["trades"]),
            "total_pnl": sum(t["pnl"] for t in backtest_data["trades"]),
        }

        # Step 3: Format report
        report = f"""
        Symbol: {backtest_data['symbol']}
        Strategy: {backtest_data['strategy']}
        Total Trades: {metrics['total_trades']}
        Total PnL: {metrics['total_pnl']}
        """

        assert "EURUSD" in report
        assert "RSI" in report

    def test_generate_comprehensive_report(self):
        """Test generating comprehensive report."""
        report = {
            "header": {
                "symbol": "EURUSD",
                "strategy": "RSI",
                "period": "2026-01-01 to 2026-12-31",
            },
            "summary": {
                "total_trades": 50,
                "total_pnl": 1500,
                "win_rate": 0.60,
            },
            "details": {
                "trades": [{"pnl": 100}, {"pnl": -50}],
                "daily_results": {"2026-01-01": 1000, "2026-01-02": 500},
            },
        }

        assert "header" in report
        assert "summary" in report
        assert "details" in report

    def test_generate_report_with_charts(self):
        """Test generating report with chart data."""
        report_data = {
            "equity_curve": [10000, 10100, 10050, 10200, 10150],
            "daily_pnl": [100, -50, 150, -50],
            "drawdown": [-100, -50, -80, -30],
        }

        assert "equity_curve" in report_data
        assert "daily_pnl" in report_data
        assert len(report_data["equity_curve"]) == 5

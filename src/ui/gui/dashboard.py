"""Main GUI dashboard for the FX Trading Bot.

Provides interactive backtesting results visualization with dynamic filtering,
equity curve viewing, and optimization heatmap analysis. All data loaded from
the backtest database in real-time.
"""

# pylint: disable=no-name-in-module
import json
import logging
import os
import webbrowser

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Dashboard(QMainWindow):
    """Main GUI dashboard for the FX Trading Bot."""

    def __init__(self, db, config):
        """Initialize the dashboard with database connection and config.

        Args:
            db: Database manager instance
            config: Configuration dictionary
        """
        super().__init__()
        self.db = db
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.init_ui()

    def init_ui(self):
        """Set up the main dashboard UI"""
        self.setWindowTitle("FX Trading Bot Dashboard")
        self.setGeometry(100, 100, 1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        title_label = QLabel(
            "FX Trading Bot Dashboard - Backtest Results Analysis & Visualization"
        )
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)

        # Filters - Load from database
        filter_layout = QVBoxLayout()

        # Get symbols from database
        try:
            symbols_result = self.db.execute_query(
                "SELECT DISTINCT symbol FROM backtest_backtests ORDER BY symbol"
            )
            symbols = ["All"] + [row["symbol"] for row in symbols_result]
        except (RuntimeError, ValueError, KeyError):
            symbols = ["All"]

        self.symbol_filter = QComboBox()
        self.symbol_filter.addItems(symbols)
        self.symbol_filter.currentIndexChanged.connect(self.refresh_results)

        # Get timeframes from database
        try:
            timeframes_result = self.db.execute_query(
                "SELECT DISTINCT timeframe FROM backtest_backtests ORDER BY timeframe"
            )
            timeframes = ["All"] + [row["timeframe"] for row in timeframes_result]
        except (RuntimeError, ValueError, KeyError):
            timeframes = ["All"]

        self.timeframe_filter = QComboBox()
        self.timeframe_filter.addItems(timeframes)
        self.timeframe_filter.currentIndexChanged.connect(self.refresh_results)

        filter_layout.addWidget(QLabel("Symbol:"))
        filter_layout.addWidget(self.symbol_filter)
        filter_layout.addWidget(QLabel("Timeframe:"))
        filter_layout.addWidget(self.timeframe_filter)
        layout.addLayout(filter_layout)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(13)
        self.results_table.setHorizontalHeaderLabels(
            [
                "Strategy",
                "Symbol",
                "Timeframe",
                "Sharpe Ratio",
                "Sortino Ratio",
                "Profit Factor",
                "Calmar Ratio",
                "Ulcer Index",
                "K-Ratio",
                "Tail Ratio",
                "Expectancy",
                "ROE",
                "Time to Recover",
            ]
        )
        self.results_table.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.results_table)

        # Buttons
        button_layout = QVBoxLayout()
        refresh_button = QPushButton("Refresh Results")
        refresh_button.clicked.connect(self.refresh_results)
        button_layout.addWidget(refresh_button)

        view_equity_button = QPushButton("View Equity Curves")
        view_equity_button.clicked.connect(self.view_equity_curves)
        button_layout.addWidget(view_equity_button)

        view_heatmap_button = QPushButton("View Optimization Heatmap")
        view_heatmap_button.clicked.connect(self.view_heatmap)
        button_layout.addWidget(view_heatmap_button)

        layout.addLayout(button_layout)

        self.refresh_results()

    def refresh_results(self):
        """Load backtest results from the database with strategy names"""
        try:
            symbol = self.symbol_filter.currentText()
            timeframe = self.timeframe_filter.currentText()
            query = """
                SELECT b.strategy_id, s.name AS strategy_name, b.symbol, b.timeframe, b.metrics
                FROM backtest_backtests b
                JOIN backtest_strategies s ON b.strategy_id = s.id
                WHERE (:symbol = 'All' OR b.symbol = :symbol)
                AND (:timeframe = 'All' OR b.timeframe = :timeframe)
            """
            results = self.db.execute_query(
                query, {"symbol": symbol, "timeframe": timeframe}
            )
            self.results_table.setRowCount(len(results))
            for row, result in enumerate(results):
                self.results_table.setItem(
                    row, 0, QTableWidgetItem(str(result["strategy_name"]))
                )
                self.results_table.setItem(
                    row, 1, QTableWidgetItem(str(result["symbol"]))
                )
                self.results_table.setItem(
                    row, 2, QTableWidgetItem(str(result["timeframe"]))
                )
                metrics = json.loads(result["metrics"])
                self.results_table.setItem(
                    row, 3, QTableWidgetItem(str(metrics.get("sharpe_ratio", 0)))
                )
                self.results_table.setItem(
                    row, 4, QTableWidgetItem(str(metrics.get("sortino_ratio", 0)))
                )
                self.results_table.setItem(
                    row, 5, QTableWidgetItem(str(metrics.get("profit_factor", 0)))
                )
                self.results_table.setItem(
                    row, 6, QTableWidgetItem(str(metrics.get("calmar_ratio", 0)))
                )
                self.results_table.setItem(
                    row, 7, QTableWidgetItem(str(metrics.get("ulcer_index", 0)))
                )
                self.results_table.setItem(
                    row, 8, QTableWidgetItem(str(metrics.get("k_ratio", 0)))
                )
                self.results_table.setItem(
                    row, 9, QTableWidgetItem(str(metrics.get("tail_ratio", 0)))
                )
                self.results_table.setItem(
                    row, 10, QTableWidgetItem(str(metrics.get("expectancy", 0)))
                )
                self.results_table.setItem(
                    row, 11, QTableWidgetItem(str(metrics.get("roe", 0)))
                )
                self.results_table.setItem(
                    row, 12, QTableWidgetItem(str(metrics.get("time_to_recover", 0)))
                )
            self.logger.debug("Refreshed backtest results in dashboard")
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to load backtest results: %s", e)

    def view_equity_curves(self):
        """Open equity curve plot in browser for selected symbol and strategy"""
        try:
            symbol = self.symbol_filter.currentText()
            if symbol == "All":
                self.logger.warning(
                    "Please select a specific symbol to view equity curve"
                )
                return

            # Get selected row strategy
            selected_rows = self.results_table.selectionModel().selectedRows()
            if not selected_rows:
                self.logger.warning(
                    "Please select a backtest result to view its equity curve"
                )
                return

            row = selected_rows[0].row()
            strategy_item = self.results_table.item(row, 0)
            if not strategy_item:
                self.logger.warning("Could not retrieve strategy name")
                return

            strategy_name = strategy_item.text()
            equity_file = os.path.abspath(
                f"backtests/results/equity_curve_{symbol}_{strategy_name}.html"
            )

            if os.path.exists(equity_file):
                webbrowser.open(f"file:///{equity_file}")
                self.logger.info("Opened equity curve: %s", equity_file)
            else:
                # Try to find any available equity curve file for this symbol
                results_dir = "backtests/results"
                if os.path.exists(results_dir):
                    files = [
                        f
                        for f in os.listdir(results_dir)
                        if f.startswith(f"equity_curve_{symbol}")
                        and f.endswith(".html")
                    ]
                    if files:
                        fallback_file = os.path.abspath(
                            os.path.join(results_dir, files[0])
                        )
                        webbrowser.open(f"file:///{fallback_file}")
                        self.logger.info(
                            "Opened available equity curve: %s", fallback_file
                        )
                    else:
                        self.logger.warning("No equity curve found for %s", symbol)
                else:
                    self.logger.warning("Results directory not found")
        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error("Failed to open equity curve: %s", e)

    def view_heatmap(self):
        """Open optimization heatmap in browser for selected symbol and timeframe"""
        try:
            symbol = self.symbol_filter.currentText()
            timeframe = self.timeframe_filter.currentText()

            if symbol == "All" or timeframe == "All":
                self.logger.warning(
                    "Please select a specific symbol and timeframe to view heatmap"
                )
                return

            heatmap_file = os.path.abspath(
                f"backtests/results/rsi_optimization_heatmap_{symbol}_{timeframe}.png"
            )

            if os.path.exists(heatmap_file):
                webbrowser.open(f"file:///{heatmap_file}")
                self.logger.info("Opened heatmap: %s", heatmap_file)
            else:
                # Try to find any available heatmap file for this symbol/timeframe
                results_dir = "backtests/results"
                if os.path.exists(results_dir):
                    files = [
                        f
                        for f in os.listdir(results_dir)
                        if f"optimization_heatmap_{symbol}_{timeframe}" in f
                    ]
                    if files:
                        fallback_file = os.path.abspath(
                            os.path.join(results_dir, files[0])
                        )
                        webbrowser.open(f"file:///{fallback_file}")
                        self.logger.info("Opened available heatmap: %s", fallback_file)
                    else:
                        self.logger.warning(
                            "No heatmap found for %s (%s). Run optimization first.",
                            symbol,
                            timeframe,
                        )
                else:
                    self.logger.warning("Results directory not found")
        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error("Failed to open heatmap: %s", e)

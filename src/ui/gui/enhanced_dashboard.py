# src/ui/gui/enhanced_dashboard.py
# Purpose: Enhanced PyQt5 dashboard with 5 tabs for backtest visualization
# pylint: disable=no-name-in-module
import json
from datetime import datetime

from src.utils.logging_factory import LoggingFactory

import pandas as pd
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.database.db_manager import DatabaseManager
from src.ui.gui.plotly_charts import PlotlyCharts


class MetricsCard(QFrame):
    """Custom widget for displaying a single metric."""

    def __init__(self, name: str, value: str, color: str = "black"):
        """Initialize metrics card.

        Args:
            name: Metric name
            value: Metric value
            color: Text color
        """
        super().__init__()
        self.setStyleSheet(
            """
            QFrame {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                background-color: #f9f9f9;
            }
        """
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(name_label)

        value_label = QLabel(value)
        value_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {color};"
        )
        layout.addWidget(value_label)

        self.setLayout(layout)


class EnhancedDashboard(QMainWindow):
    """Enhanced dashboard with 5 tabs for backtest results."""

    def __init__(self, db: DatabaseManager, config: dict):
        """Initialize dashboard.

        Args:
            db: Database manager instance
            config: Configuration dictionary
        """
        super().__init__()
        self.db = db
        self.config = config
        self.logger = LoggingFactory.get_logger(__name__)
        self.charts = PlotlyCharts()

        self.setWindowTitle("FX Trading Bot - Backtest Dashboard")
        self.setGeometry(100, 100, 1600, 900)

        # Current selected backtest
        self.current_backtest = None
        self.current_trades = []

        # Initialize tab attributes
        self.tabs = None
        self.summary_tab = None
        self.equity_tab = None
        self.equity_view = None
        self.trades_tab = None
        self.trades_table = None
        self.metrics_tab = None
        self.metrics_view = None
        self.export_tab = None
        self.backtest_selector = None

        self.init_ui()
        self.logger.info("Enhanced dashboard initialized")

    def init_ui(self):
        """Initialize user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Select Backtest:"))

        self.backtest_selector = QComboBox()
        self.backtest_selector.currentIndexChanged.connect(self.on_backtest_selected)
        header_layout.addWidget(self.backtest_selector)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        header_layout.addWidget(refresh_btn)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Load backtests
        self.load_backtests()

        # Tab widget
        self.tabs = QTabWidget()
        self.create_summary_tab()
        self.create_equity_tab()
        self.create_trades_tab()
        self.create_metrics_tab()
        self.create_export_tab()

        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)

    def load_backtests(self):
        """Load available backtests from database."""
        try:
            query = "SELECT id, symbol, strategy_name, timeframe, created_at FROM backtest_results ORDER BY created_at DESC"
            results = self.db.execute_query(query)

            self.backtest_selector.clear()
            for result in results:
                label = f"{result[1]} / {result[2]} / {result[3]} ({result[4]})"
                self.backtest_selector.addItem(label, result[0])

            self.logger.info("Loaded %d backtests", len(results))
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to load backtests: %s", e)

    def on_backtest_selected(self, index: int):
        """Handle backtest selection from dropdown.

        Args:
            index: Index of selected item in the dropdown.
        """
        if index >= 0:
            backtest_id = self.backtest_selector.itemData(index)
            self.load_backtest_data(backtest_id)

    def load_backtest_data(self, backtest_id: int):
        """Load backtest data from database.

        Args:
            backtest_id: Backtest result ID
        """
        try:
            # Load results
            query = "SELECT * FROM backtest_results WHERE id = ?"
            results = self.db.execute_query(query, (backtest_id,))

            if results:
                self.current_backtest = results[0]

            # Load trades
            query = "SELECT * FROM backtest_trades WHERE backtest_result_id = ? ORDER BY entry_time"
            trades = self.db.execute_query(query, (backtest_id,))

            self.current_trades = [
                {
                    "entry_time": t[2],
                    "exit_time": t[3],
                    "symbol": t[4],
                    "entry_price": t[5],
                    "exit_price": t[6],
                    "volume": t[7],
                    "profit": t[8],
                    "profit_pct": t[9],
                    "duration_hours": t[10],
                }
                for t in trades
            ]

            self.logger.info(
                "Loaded backtest %d with %d trades",
                backtest_id,
                len(self.current_trades),
            )
            self.refresh_tabs()
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to load backtest data: %s", e)

    def refresh_data(self):
        """Refresh dashboard data by reloading backtests and current selection."""
        self.load_backtests()
        if self.current_backtest:
            self.load_backtest_data(self.current_backtest[0])

    def refresh_tabs(self):
        """Refresh all tab displays with current backtest data."""
        self.refresh_summary_tab()
        self.refresh_equity_tab()
        self.refresh_trades_tab()
        self.refresh_metrics_tab()

    # ========== TAB 1: SUMMARY ==========

    def create_summary_tab(self):
        """Create summary tab with key performance metrics."""
        self.summary_tab = QWidget()
        self.tabs.addTab(self.summary_tab, "Summary")

    def refresh_summary_tab(self):
        """Refresh summary tab with current backtest metrics."""
        if not self.current_backtest:
            return

        # Clear layout
        if self.summary_tab.layout():
            while self.summary_tab.layout().count():
                self.summary_tab.layout().itemAt(0).widget().deleteLater()
        else:
            self.summary_tab.setLayout(QVBoxLayout())

        layout = QVBoxLayout()

        # Metadata
        meta_layout = QHBoxLayout()
        meta_layout.addWidget(QLabel(f"Symbol: {self.current_backtest[1]}"))
        meta_layout.addWidget(QLabel(f"Strategy: {self.current_backtest[2]}"))
        meta_layout.addWidget(QLabel(f"Timeframe: {self.current_backtest[3]}"))
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        layout.addWidget(QLabel(""))  # Spacing

        # Metrics grid
        grid = QGridLayout()
        metrics = {
            "Total Profit %": f"{self.current_backtest[7]:.2f}%",
            "Sharpe Ratio": f"{self.current_backtest[8]:.2f}",
            "Annual Return %": f"{self.current_backtest[9]:.2f}%",
            "Max Drawdown %": f"{self.current_backtest[10]:.2f}%",
            "Profit Factor": f"{self.current_backtest[11]:.2f}",
            "Total Orders": f"{int(self.current_backtest[12])}",
            "Win Rate %": f"{self.current_backtest[13]:.1f}%",
            "P/L Ratio": f"{self.current_backtest[14]:.2f}",
            "Winner Avg %": f"{self.current_backtest[15]:.2f}%",
            "Loser Avg %": f"{self.current_backtest[16]:.2f}%",
            "Sortino Ratio": f"{self.current_backtest[17]:.2f}",
            "Calmar Ratio": f"{self.current_backtest[18]:.2f}",
        }

        row = 0
        for i, (name, value) in enumerate(metrics.items()):
            if i % 3 == 0:
                row = i // 3
            col = i % 3
            color = (
                "green"
                if "+" in value or ("%" in value and float(value.rstrip("%")) > 0)
                else "red"
            )
            grid.addWidget(MetricsCard(name, value, color), row, col)

        layout.addLayout(grid)
        layout.addStretch()
        self.summary_tab.setLayout(layout)

    # ========== TAB 2: EQUITY CURVE ==========

    def create_equity_tab(self):
        """Create equity curve tab with interactive Plotly chart."""
        self.equity_tab = QWidget()
        layout = QVBoxLayout()

        self.equity_view = QWebEngineView()
        layout.addWidget(self.equity_view)

        self.equity_tab.setLayout(layout)
        self.tabs.addTab(self.equity_tab, "Equity Curve")

    def refresh_equity_tab(self):
        """Refresh equity curve chart with current trade data."""
        if not self.current_trades:
            return

        fig = self.charts.create_equity_curve(self.current_trades)
        html = fig.to_html(include_plotlyjs="cdn")

        self.equity_view.setHtml(html)

    # ========== TAB 3: TRADES ==========

    def create_trades_tab(self):
        """Create trades details tab with table view."""
        self.trades_tab = QWidget()
        layout = QVBoxLayout()

        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(9)
        self.trades_table.setHorizontalHeaderLabels(
            [
                "Entry Time",
                "Exit Time",
                "Symbol",
                "Entry Price",
                "Exit Price",
                "Volume",
                "Profit",
                "Profit %",
                "Duration (hrs)",
            ]
        )
        layout.addWidget(self.trades_table)

        self.trades_tab.setLayout(layout)
        self.tabs.addTab(self.trades_tab, "Trades")

    def refresh_trades_tab(self):
        """Refresh trades table with current backtest trades."""
        if not self.current_trades:
            return

        self.trades_table.setRowCount(len(self.current_trades))

        for row, trade in enumerate(self.current_trades):
            self.trades_table.setItem(
                row, 0, QTableWidgetItem(str(trade["entry_time"])[:19])
            )
            self.trades_table.setItem(
                row, 1, QTableWidgetItem(str(trade["exit_time"])[:19])
            )
            self.trades_table.setItem(row, 2, QTableWidgetItem(trade["symbol"]))
            self.trades_table.setItem(
                row, 3, QTableWidgetItem(f"${trade['entry_price']:.2f}")
            )
            self.trades_table.setItem(
                row, 4, QTableWidgetItem(f"${trade['exit_price']:.2f}")
            )
            self.trades_table.setItem(
                row, 5, QTableWidgetItem(f"{trade['volume']:.4f}")
            )
            self.trades_table.setItem(
                row, 6, QTableWidgetItem(f"${trade['profit']:.2f}")
            )
            self.trades_table.setItem(
                row, 7, QTableWidgetItem(f"{trade['profit_pct']:.2f}%")
            )
            self.trades_table.setItem(
                row, 8, QTableWidgetItem(f"{trade['duration_hours']:.1f}")
            )

    # ========== TAB 4: METRICS ==========

    def create_metrics_tab(self):
        """Create metrics analysis tab with comparison chart."""
        self.metrics_tab = QWidget()
        layout = QVBoxLayout()

        self.metrics_view = QWebEngineView()
        layout.addWidget(self.metrics_view)

        self.metrics_tab.setLayout(layout)
        self.tabs.addTab(self.metrics_tab, "Metrics")

    def refresh_metrics_tab(self):
        """Refresh metrics comparison chart with current data."""
        if not self.current_backtest:
            return

        metrics = {
            "sharpe_ratio": self.current_backtest[8],
            "annual_return_pct": self.current_backtest[9],
            "max_drawdown_pct": self.current_backtest[10],
            "profit_factor": self.current_backtest[11],
            "win_rate_pct": self.current_backtest[13],
        }

        fig = self.charts.create_metrics_comparison(metrics)
        html = fig.to_html(include_plotlyjs="cdn")

        self.metrics_view.setHtml(html)

    # ========== TAB 5: EXPORT ==========

    def create_export_tab(self):
        """Create export tab with CSV and JSON export options."""
        self.export_tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Export Backtest Results"))
        layout.addWidget(QLabel(""))

        btn_csv = QPushButton("Export to CSV")
        btn_csv.clicked.connect(self.export_csv)
        layout.addWidget(btn_csv)

        btn_json = QPushButton("Export to JSON")
        btn_json.clicked.connect(self.export_json)
        layout.addWidget(btn_json)

        layout.addStretch()
        self.export_tab.setLayout(layout)
        self.tabs.addTab(self.export_tab, "Export")

    def export_csv(self):
        """Export current backtest trades to CSV file."""
        if not self.current_trades:
            return

        df = pd.DataFrame(self.current_trades)
        filename = f"backtest_{self.current_backtest[1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        self.logger.info("Exported to %s", filename)

    def export_json(self):
        """Export current backtest results and trades to JSON file."""
        if not self.current_backtest:
            return

        results = {
            "symbol": self.current_backtest[1],
            "strategy": self.current_backtest[2],
            "timeframe": self.current_backtest[3],
            "metrics": {
                "total_profit_pct": self.current_backtest[7],
                "sharpe_ratio": self.current_backtest[8],
                "annual_return_pct": self.current_backtest[9],
                "max_drawdown_pct": self.current_backtest[10],
                "profit_factor": self.current_backtest[11],
                "win_rate_pct": self.current_backtest[13],
            },
            "trades": self.current_trades,
        }

        filename = f"backtest_{self.current_backtest[1]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)

        self.logger.info("Exported to %s", filename)

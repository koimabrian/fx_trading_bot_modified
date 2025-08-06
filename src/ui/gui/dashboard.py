# fx_trading_bot/src/ui/gui/dashboard.py
# Purpose: Implements the main GUI dashboard for the FX Trading Bot
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox
from PyQt5.QtCore import Qt
import json
import logging
import os
import webbrowser

class Dashboard(QMainWindow):
    def __init__(self, db, config):
        """Initialize the dashboard with database connection and config"""
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

        title_label = QLabel("FX Trading Bot Dashboard")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)

        # Filters
        filter_layout = QVBoxLayout()
        self.symbol_filter = QComboBox()
        self.symbol_filter.addItems(['All'] + sorted(set([p['symbol'] for p in self.config.get('pairs', [])])))
        self.timeframe_filter = QComboBox()
        timeframes = sorted(set([f"M{p['timeframe']}" if p['timeframe'] < 60 else f"H{p['timeframe']//60}" for p in self.config.get('pairs', [])]))
        self.timeframe_filter.addItems(['All'] + timeframes)
        filter_layout.addWidget(QLabel("Symbol:"))
        filter_layout.addWidget(self.symbol_filter)
        filter_layout.addWidget(QLabel("Timeframe:"))
        filter_layout.addWidget(self.timeframe_filter)
        layout.addLayout(filter_layout)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(13)
        self.results_table.setHorizontalHeaderLabels([
            "Strategy", "Symbol", "Timeframe", "Sharpe Ratio", "Sortino Ratio",
            "Profit Factor", "Calmar Ratio", "Ulcer Index", "K-Ratio",
            "Tail Ratio", "Expectancy", "ROE", "Time to Recover"
        ])
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
            results = self.db.execute_query(query, {'symbol': symbol, 'timeframe': timeframe})
            self.results_table.setRowCount(len(results))
            for row, result in enumerate(results):
                self.results_table.setItem(row, 0, QTableWidgetItem(str(result['strategy_name'])))
                self.results_table.setItem(row, 1, QTableWidgetItem(str(result['symbol'])))
                self.results_table.setItem(row, 2, QTableWidgetItem(str(result['timeframe'])))
                metrics = json.loads(result['metrics'])
                self.results_table.setItem(row, 3, QTableWidgetItem(str(metrics.get('sharpe_ratio', 0))))
                self.results_table.setItem(row, 4, QTableWidgetItem(str(metrics.get('sortino_ratio', 0))))
                self.results_table.setItem(row, 5, QTableWidgetItem(str(metrics.get('profit_factor', 0))))
                self.results_table.setItem(row, 6, QTableWidgetItem(str(metrics.get('calmar_ratio', 0))))
                self.results_table.setItem(row, 7, QTableWidgetItem(str(metrics.get('ulcer_index', 0))))
                self.results_table.setItem(row, 8, QTableWidgetItem(str(metrics.get('k_ratio', 0))))
                self.results_table.setItem(row, 9, QTableWidgetItem(str(metrics.get('tail_ratio', 0))))
                self.results_table.setItem(row, 10, QTableWidgetItem(str(metrics.get('expectancy', 0))))
                self.results_table.setItem(row, 11, QTableWidgetItem(str(metrics.get('roe', 0))))
                self.results_table.setItem(row, 12, QTableWidgetItem(str(metrics.get('time_to_recover', 0))))
            self.logger.debug("Refreshed backtest results in dashboard")
        except Exception as e:
            self.logger.error(f"Failed to load backtest results: {e}")

    def view_equity_curves(self):
        """Open equity curve plot in browser"""
        try:
            equity_file = os.path.abspath('backtests/results/equity_curve_comparison.html')
            if os.path.exists(equity_file):
                webbrowser.open(f'file://{equity_file}')
                self.logger.debug("Opened equity curve plot")
            else:
                self.logger.warning("Equity curve plot not found")
        except Exception as e:
            self.logger.error(f"Failed to open equity curve plot: {e}")

    def view_heatmap(self):
        """Open optimization heatmap in browser"""
        try:
            heatmap_file = os.path.abspath('backtests/results/rsi_optimization_heatmap.html')
            if os.path.exists(heatmap_file):
                self.logger.debug("Opened optimization heatmap")
                webbrowser.open(f'file://{heatmap_file}')
            else:
                self.logger.warning("Optimization heatmap not found")
        except Exception as e:
            self.logger.error(f"Failed to open optimization heatmap: {e}")
# fx_trading_bot/src/ui/gui/dashboard.py
# Purpose: Implements the main GUI dashboard for the FX Trading Bot
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
import logging

class Dashboard(QMainWindow):
    def __init__(self, db):
        """Initialize the dashboard with database connection"""
        super().__init__()
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.init_ui()

    def init_ui(self):
        """Set up the main dashboard UI"""
        self.setWindowTitle("FX Trading Bot Dashboard")
        self.setGeometry(100, 100, 800, 600)

        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Title
        title_label = QLabel("FX Trading Bot Dashboard")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)

        # Backtest results table
        self.results_table = QTableWidget()
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Strategy", "Profit Factor", "Max Drawdown", "Sharpe Ratio"])
        self.results_table.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.results_table)

        # Refresh button
        refresh_button = QPushButton("Refresh Results")
        refresh_button.clicked.connect(self.refresh_results)
        layout.addWidget(refresh_button)

        # Initial data load
        self.refresh_results()

    def refresh_results(self):
        """Load backtest results from the database with strategy names"""
        try:
            # Join backtests and strategies tables to get strategy names
            results = self.db.execute_query(
                """
                SELECT b.strategy_id, s.name AS strategy_name, b.metrics
                FROM backtests b
                JOIN strategies s ON b.strategy_id = s.id
                """
            )
            self.results_table.setRowCount(len(results))
            for row, result in enumerate(results):
                self.results_table.setItem(row, 0, QTableWidgetItem(str(result['strategy_name'])))
                metrics = eval(result['metrics'])  # Assuming metrics stored as JSON string
                self.results_table.setItem(row, 1, QTableWidgetItem(str(metrics.get('profit_factor', 0))))
                self.results_table.setItem(row, 2, QTableWidgetItem(str(metrics.get('max_drawdown', 0))))
                self.results_table.setItem(row, 3, QTableWidgetItem(str(metrics.get('sharpe_ratio', 0))))
            self.logger.debug("Refreshed backtest results in dashboard")
        except Exception as e:
            self.logger.error(f"Failed to load backtest results: {e}")
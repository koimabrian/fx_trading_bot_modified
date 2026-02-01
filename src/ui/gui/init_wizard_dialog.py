"""PyQt5 wizard dialog for FX Trading Bot initialization.

Guides users through:
1. Database and MT5 connection setup
2. Symbol discovery and categorization
3. Symbol selection for trading
4. Confirmation and initialization
"""

import time
from typing import Dict, List, Optional

import MetaTrader5 as mt5

from src.utils.logging_factory import LoggingFactory
from PyQt5.QtCore import Qt, QTimer  # pylint: disable=no-name-in-module

# pylint: disable=no-name-in-module
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.init_manager import InitManager
from src.database.db_manager import DatabaseManager
from src.database.migrations import DatabaseMigrations
from src.mt5_connector import MT5Connector


class InitWizardDialog(QDialog):
    """Multi-step initialization wizard for FX Trading Bot."""

    def __init__(self, config: dict, parent=None):
        """Initialize the wizard.

        Args:
            config: Configuration dictionary
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = LoggingFactory.get_logger(__name__)
        self.config = config
        self.db = None
        self.mt5_conn = None
        self.symbols = []
        self.categories = {}
        self.selected_symbols = []
        self.checkboxes = {}
        self.category_checkboxes = {}

        self.setWindowTitle("FX Trading Bot - Initialization Wizard")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)

        self.stacked_layout = QVBoxLayout()
        self.current_step = 0
        self.steps = []

        self._create_steps()
        self.setLayout(self.stacked_layout)

        # Show first step
        self.show_step(0)

    def _create_steps(self):
        """Create all wizard steps."""
        self.steps = [
            self._create_step1_welcome,
            self._create_step2_connection,
            self._create_step3_discovery,
            self._create_step4_selection,
            self._create_step5_review,
            self._create_step6_success,
        ]

    def show_step(self, step_num: int):
        """Show a specific step.

        Args:
            step_num: Step number (0-indexed)
        """
        # Clear layout
        while self.stacked_layout.count():
            self.stacked_layout.takeAt(0).widget().deleteLater()

        self.current_step = step_num
        if step_num < len(self.steps):
            widget = self.steps[step_num]()
            self.stacked_layout.addWidget(widget)

    def _create_step1_welcome(self) -> QWidget:
        """Step 1: Welcome screen."""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("🚀 FX Trading Bot - Initialization")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(20)

        welcome_text = QLabel(
            "Welcome to FX Trading Bot Setup!\n\n"
            "This wizard will:\n"
            "1. Create your trading database\n"
            "2. Discover trading pairs from MetaTrader5\n"
            "3. Auto-detect symbol categories\n"
            "4. Let you select which symbols to trade\n\n"
            "Estimated time: 2-3 minutes\n\n"
            "Click [Continue] to begin."
        )
        welcome_text.setWordWrap(True)
        layout.addWidget(welcome_text)

        layout.addSpacing(30)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        start_btn = QPushButton("Continue ➜")
        start_btn.clicked.connect(lambda: self.show_step(1))
        start_btn.setMinimumWidth(120)
        button_layout.addWidget(start_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def _create_step2_connection(self) -> QWidget:
        """Step 2: Database and MT5 connection."""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Step 1 of 4: System Setup")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(15)

        # Database section
        db_label = QLabel("📊 DATABASE")
        db_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(db_label)

        db_path_label = QLabel(
            f"Path: {self.config.get('database', {}).get('path', 'src/data/market_data.sqlite')}"
        )
        layout.addWidget(db_path_label)

        self.db_progress = QProgressBar()
        self.db_progress.setMaximum(100)
        layout.addWidget(self.db_progress)

        self.db_status_label = QLabel("⟳ Initializing database...")
        layout.addWidget(self.db_status_label)

        layout.addSpacing(20)

        # MT5 section
        mt5_label = QLabel("🔗 METATRADER5 CONNECTION")
        mt5_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(mt5_label)

        self.mt5_server_label = QLabel(
            f"Server: {self.config.get('mt5', {}).get('server', 'N/A')}"
        )
        layout.addWidget(self.mt5_server_label)

        self.mt5_login_label = QLabel(
            f"Login: {self.config.get('mt5', {}).get('login', 'N/A')}"
        )
        layout.addWidget(self.mt5_login_label)

        self.mt5_progress = QProgressBar()
        self.mt5_progress.setMaximum(100)
        layout.addWidget(self.mt5_progress)

        self.mt5_status_label = QLabel("⟳ Connecting...")
        layout.addWidget(self.mt5_status_label)

        layout.addStretch()

        # Start initialization after dialog shows
        QTimer.singleShot(500, self._initialize_connection)

        widget.setLayout(layout)
        return widget

    def _initialize_connection(self):
        """Initialize database and MT5 connection."""
        try:
            # Initialize database
            self.db_progress.setValue(50)
            self.db_status_label.setText("Creating database tables...")

            self.db = DatabaseManager(self.config["database"])
            self.db.connect()  # Explicitly connect (normally done by context manager)
            migrations = DatabaseMigrations(self.db.conn)
            if not migrations.fresh_init():
                raise RuntimeError("Failed to initialize database")

            self.db_progress.setValue(100)
            self.db_status_label.setText("✓ Database initialized: 6 tables created")

            # Initialize MT5
            self.mt5_progress.setValue(30)
            self.mt5_status_label.setText("Connecting to MetaTrader5...")

            self.mt5_conn = MT5Connector(self.db)
            if not self.mt5_conn.initialize():
                raise RuntimeError("Failed to initialize MT5 connection")

            self.mt5_progress.setValue(100)
            self.mt5_status_label.setText("✓ MT5 connection verified")

            # Enable next button
            QTimer.singleShot(800, lambda: self.show_step(2))

        except Exception as e:
            self.logger.error("Connection initialization failed: %s", e)
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Failed to initialize connection:\n{str(e)}",
            )
            self.reject()

    def _create_step3_discovery(self) -> QWidget:
        """Step 3: Symbol discovery."""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Step 2 of 4: Symbol Discovery")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(15)

        self.discovery_progress = QProgressBar()
        self.discovery_progress.setMaximum(100)
        layout.addWidget(self.discovery_progress)

        self.discovery_status_label = QLabel("⟳ Scanning MetaTrader5 symbols...")
        layout.addWidget(self.discovery_status_label)

        layout.addSpacing(15)

        self.forex_label = QLabel("📊 FOREX SYMBOLS: (discovering...)")
        layout.addWidget(self.forex_label)

        self.crypto_label = QLabel("💰 CRYPTO SYMBOLS: (discovering...)")
        layout.addWidget(self.crypto_label)

        layout.addSpacing(15)

        self.discovery_info_label = QLabel("")
        self.discovery_info_label.setWordWrap(True)
        layout.addWidget(self.discovery_info_label)

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        back_btn = QPushButton("⬅ Back")
        back_btn.clicked.connect(lambda: self.show_step(1))
        button_layout.addWidget(back_btn)

        self.next_btn = QPushButton("Continue ➜")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(lambda: self.show_step(3))
        button_layout.addWidget(self.next_btn)

        layout.addLayout(button_layout)

        widget.setLayout(layout)

        # Start discovery after dialog shows
        QTimer.singleShot(500, self._discover_symbols)

        return widget

    def _discover_symbols(self):
        """Discover tradable symbols from MT5 and categorize by path."""
        try:
            self.discovery_progress.setValue(30)
            self.discovery_status_label.setText("Scanning MT5 symbols...")

            if not mt5.initialize():
                raise RuntimeError("Failed to initialize MT5 for symbol discovery")

            # Get all symbols
            all_symbols = mt5.symbols_get()
            if not all_symbols:
                raise RuntimeError("No symbols found in MT5")

            # Filter only TRADABLE symbols (SYMBOL_TRADE_MODE_FULL)
            tradable_symbols = [
                s for s in all_symbols if s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
            ]

            if not tradable_symbols:
                raise RuntimeError(
                    "No tradable symbols found in MT5. "
                    "Make sure your account supports trading."
                )

            # Categorize symbols using MT5's path attribute
            self.categories = self._categorize_symbols_by_path(tradable_symbols)

            # Flatten for display
            self.symbols = sorted([s.name for s in tradable_symbols])

            self.discovery_progress.setValue(100)
            self.discovery_status_label.setText(
                f"✓ Found {len(self.symbols)} tradable symbols"
            )

            # Update category labels
            forex_symbols = self.categories.get("Forex", [])
            crypto_symbols = self.categories.get("Crypto", [])
            other_symbols = self.categories.get("Other", [])

            self.forex_label.setText(
                f"📊 FOREX SYMBOLS ({len(forex_symbols)} found):\n"
                + ", ".join(forex_symbols[:5])
                + ("..." if len(forex_symbols) > 5 else "")
            )

            self.crypto_label.setText(
                f"💰 CRYPTO SYMBOLS ({len(crypto_symbols)} found):\n"
                + ", ".join(crypto_symbols)
            )

            info_text = (
                f"✓ {len(forex_symbols)} forex symbols (tradable)\n"
                f"✓ {len(crypto_symbols)} crypto symbols (tradable)"
            )
            if other_symbols:
                info_text += f"\n✓ {len(other_symbols)} other symbols (tradable)"

            info_text += "\n✓ Categories auto-detected from MT5 paths\n"
            info_text += "✓ All shown symbols are broker-tradable"

            self.discovery_info_label.setText(info_text)

            # Enable next button
            self.next_btn.setEnabled(True)

        except Exception as e:
            self.logger.error("Symbol discovery failed: %s", e)
            QMessageBox.critical(
                self,
                "Discovery Error",
                f"Failed to discover symbols:\n{str(e)}\n\n"
                "Make sure MetaTrader5 is running with the correct account active.",
            )
            self.reject()

    def _categorize_symbols_by_path(self, mt5_symbols) -> Dict[str, List[str]]:
        """Categorize symbols using MT5's symbol path attribute.

        Args:
            mt5_symbols: List of MT5 symbol objects

        Returns:
            Dictionary with categories and symbol lists
        """
        categories = {}

        for symbol in mt5_symbols:
            # Get path like "Pro\Forex\EURUSD" or "Pro\Crypto\BTCUSD"
            path = symbol.path.lower() if symbol.path else "other"

            # Extract category from path
            # Format: Pro\Category\Symbol or Pro/Category/Symbol
            parts = path.replace("\\", "/").split("/")

            if len(parts) >= 2:
                category = parts[-2]  # Get the second-to-last part (category)
                # Capitalize first letter for display
                category = category.capitalize()
            else:
                category = "Other"

            # Add symbol to category
            if category not in categories:
                categories[category] = []
            categories[category].append(symbol.name)

        # Sort symbols within each category
        for category in categories:
            categories[category].sort()

        return categories

    def _create_step4_selection(self) -> QWidget:
        """Step 4: Symbol selection."""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Step 3 of 4: Select Trading Symbols")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel(
            "Choose which symbols to trade. You can modify this later via the GUI dashboard."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(10)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter symbols (e.g., EUR, BTC)...")
        self.search_input.textChanged.connect(self._filter_symbols)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Tabs for categories
        self.tabs = QTabWidget()
        for category, symbols in self.categories.items():
            tab_widget = QWidget()
            tab_layout = QVBoxLayout()

            # Category select/deselect
            category_checkbox = QCheckBox(f"Select all {category} ({len(symbols)})")
            category_checkbox.stateChanged.connect(
                lambda state, cat=category: self._toggle_category(cat, state)
            )
            self.category_checkboxes[category] = category_checkbox
            tab_layout.addWidget(category_checkbox)

            # Scrollable area for checkboxes
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout()

            for symbol in symbols:
                checkbox = QCheckBox(symbol)
                checkbox.stateChanged.connect(self._on_checkbox_changed)
                self.checkboxes[symbol] = checkbox
                scroll_layout.addWidget(checkbox)

            scroll_layout.addStretch()
            scroll_widget.setLayout(scroll_layout)
            scroll.setWidget(scroll_widget)
            tab_layout.addWidget(scroll)

            tab_widget.setLayout(tab_layout)
            self.tabs.addTab(tab_widget, category)

        layout.addWidget(self.tabs)

        layout.addSpacing(10)

        # Summary
        self.selection_summary = QLabel("Selected: 0 symbols")
        self.selection_summary.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.selection_summary)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        back_btn = QPushButton("⬅ Back")
        back_btn.clicked.connect(lambda: self.show_step(2))
        button_layout.addWidget(back_btn)

        continue_btn = QPushButton("Continue ➜")
        continue_btn.clicked.connect(self._validate_selection)
        button_layout.addWidget(continue_btn)

        layout.addLayout(button_layout)

        widget.setLayout(layout)
        return widget

    def _filter_symbols(self):
        """Filter symbols based on search input."""
        search_term = self.search_input.text().upper()

        for symbol, checkbox in self.checkboxes.items():
            if search_term in symbol:
                checkbox.show()
            else:
                checkbox.hide()

    def _on_checkbox_changed(self):
        """Handle checkbox state changes."""
        # Update category checkboxes
        for category in self.categories:
            category_symbols = self.categories[category]
            checked_count = sum(
                1
                for sym in category_symbols
                if sym in self.checkboxes and self.checkboxes[sym].isChecked()
            )

            if checked_count == len(category_symbols):
                self.category_checkboxes[category].blockSignals(True)
                self.category_checkboxes[category].setCheckState(Qt.Checked)
                self.category_checkboxes[category].blockSignals(False)
            elif checked_count == 0:
                self.category_checkboxes[category].blockSignals(True)
                self.category_checkboxes[category].setCheckState(Qt.Unchecked)
                self.category_checkboxes[category].blockSignals(False)
            else:
                self.category_checkboxes[category].blockSignals(True)
                self.category_checkboxes[category].setCheckState(Qt.PartiallyChecked)  # type: ignore
                self.category_checkboxes[category].blockSignals(False)

        # Update summary
        selected = self._get_selected_symbols()
        self.selection_summary.setText(
            f"Selected: {len(selected)} symbols - "
            f"Forex: {len([s for s in selected if any(s.endswith(x) for x in ('USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF'))])}, "
            f"Crypto: {len([s for s in selected if any(x in s for x in ('BTC', 'ETH', 'XRP'))])}"
        )

    def _toggle_category(self, category: str, state):
        """Toggle all symbols in a category.

        Args:
            category: Category name
            state: Qt checkbox state
        """
        is_checked = state == Qt.Checked
        for symbol in self.categories[category]:
            if symbol in self.checkboxes:
                self.checkboxes[symbol].blockSignals(True)
                self.checkboxes[symbol].setChecked(is_checked)
                self.checkboxes[symbol].blockSignals(False)
        self._on_checkbox_changed()

    def _get_selected_symbols(self) -> List[str]:
        """Get list of selected symbols.

        Returns:
            List of selected symbol names
        """
        return [
            symbol
            for symbol, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def _validate_selection(self):
        """Validate symbol selection and proceed."""
        selected = self._get_selected_symbols()
        if not selected:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one symbol before continuing.",
            )
            return

        self.selected_symbols = selected
        self.show_step(4)

    def _create_step5_review(self) -> QWidget:
        """Step 5: Review and confirm."""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("Step 4 of 4: Review & Confirm")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(15)

        # Database summary
        db_label = QLabel("📂 DATABASE CONFIGURATION:")
        db_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(db_label)

        db_info = QLabel(
            f"Location: {self.config.get('database', {}).get('path', 'src/data/market_data.sqlite')}\n"
            "Tables: tradable_pairs, market_data, optimal_parameters, "
            "backtest_backtests, backtest_trades, trades"
        )
        db_info.setWordWrap(True)
        layout.addWidget(db_info)

        layout.addSpacing(15)

        # MT5 summary
        mt5_label = QLabel("🔗 METATRADER5 CONFIGURATION:")
        mt5_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(mt5_label)

        mt5_info = QLabel(
            f"Server: {self.config.get('mt5', {}).get('server', 'N/A')}\n"
            f"Account: {self.config.get('mt5', {}).get('login', 'N/A')}\n"
            "Connection: ✓ Verified"
        )
        layout.addWidget(mt5_info)

        layout.addSpacing(15)

        # Symbols summary
        symbols_label = QLabel("📊 SYMBOLS TO TRADE:")
        symbols_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(symbols_label)

        # Build category breakdown from actual categories
        category_breakdown = []
        for category, symbols in sorted(self.categories.items()):
            selected_in_cat = [s for s in self.selected_symbols if s in symbols]
            if selected_in_cat:
                category_breakdown.append(
                    f"{category} ({len(selected_in_cat)}): {', '.join(selected_in_cat)}"
                )

        symbols_info = QLabel(
            f"Total Selected: {len(self.selected_symbols)} symbols\n\n"
            + "\n".join(category_breakdown)
            if category_breakdown
            else "No symbols selected"
        )
        symbols_info.setWordWrap(True)
        layout.addWidget(symbols_info)

        layout.addSpacing(15)

        next_steps = QLabel(
            "Next Steps After Initialization:\n"
            "1. Data Sync: Fetch historical OHLCV data (5-10 minutes)\n"
            "2. Backtesting: Optimize strategy parameters (30-60 minutes)\n"
            "3. Live Trading: Start trading with dashboard monitoring"
        )
        next_steps.setWordWrap(True)
        layout.addWidget(next_steps)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        back_btn = QPushButton("⬅ Back")
        back_btn.clicked.connect(lambda: self.show_step(3))
        button_layout.addWidget(back_btn)

        confirm_btn = QPushButton("✓ INITIALIZE")
        confirm_btn.clicked.connect(self._perform_initialization)
        button_layout.addWidget(confirm_btn)

        layout.addLayout(button_layout)

        widget.setLayout(layout)
        return widget

    def _perform_initialization(self):
        """Perform the actual initialization."""
        try:
            self.show_step(5)

            # Initialize with selected symbols
            init_manager = InitManager(self.db, self.mt5_conn, self.config)
            init_manager.selected_symbols = self.selected_symbols

            # This runs the actual initialization
            if not init_manager.run_initialization():
                raise RuntimeError("Initialization process failed")

        except Exception as e:
            self.logger.error("Initialization failed: %s", e)
            QMessageBox.critical(
                self,
                "Initialization Error",
                f"Initialization failed:\n{str(e)}",
            )
            self.reject()

    def _create_step6_success(self) -> QWidget:
        """Step 6: Success screen."""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("✅ SUCCESS!")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        layout.addSpacing(20)

        success_text = QLabel(
            "Your trading system has been initialized and is ready to use.\n\n"
            "Initialization completed successfully:\n"
            f"✓ Database created\n"
            f"✓ {len(self.selected_symbols)} trading symbols configured\n"
            f"✓ MT5 connection verified\n\n"
            "What's Next?\n"
            "1. Sync Data: Fetch historical price data\n"
            "   Command: python -m src.main --mode sync\n\n"
            "2. Backtest: Optimize strategy parameters\n"
            "   Command: python -m src.main --mode backtest\n\n"
            "3. Live Trading: Start automated trading\n"
            "   Command: python -m src.main --mode live\n\n"
            "4. Dashboard: Monitor performance\n"
            "   Command: python -m src.main --mode gui"
        )
        success_text.setWordWrap(True)
        layout.addWidget(success_text)

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        finish_btn = QPushButton("✓ Finish")
        finish_btn.clicked.connect(self.accept)
        button_layout.addWidget(finish_btn)

        layout.addLayout(button_layout)

        widget.setLayout(layout)
        return widget

    def closeEvent(self, event):
        """Clean up on close."""
        if self.db:
            try:
                self.db.close()
            except Exception as e:
                self.logger.error("Error closing database: %s", e)
        event.accept()

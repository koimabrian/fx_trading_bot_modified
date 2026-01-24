"""PyQt5 dialog for selecting trading pairs during initialization."""

import logging
from typing import List, Dict

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QLabel,
    QMessageBox,
)
from PyQt5.QtCore import Qt


class PairSelectorDialog(QDialog):
    """Dialog for selecting trading pairs from available symbols."""

    def __init__(self, symbols: List[str], parent=None):
        """Initialize the pair selector dialog.

        Args:
            symbols: List of all available trading symbols
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.symbols = sorted(symbols)
        self.selected_pairs = []
        self.checkboxes = {}
        self.category_checkboxes = {}
        self.search_term = ""

        # Categorize symbols
        self.categories = self._categorize_symbols(self.symbols)

        self.setWindowTitle("Select Trading Pairs")
        self.setGeometry(100, 100, 700, 600)
        self.init_ui()

    def _categorize_symbols(self, symbols: List[str]) -> Dict[str, List[str]]:
        """Categorize symbols by type (Forex, Crypto, Stocks).

        Args:
            symbols: List of trading symbols

        Returns:
            Dictionary with categories as keys and symbol lists as values
        """
        forex_suffixes = ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF")
        crypto_suffixes = ("BTC", "ETH", "XRP")
        stock_names = ("AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA")

        categories = {"Forex": [], "Crypto": [], "Stocks": [], "Other": []}

        for symbol in symbols:
            if any(symbol.endswith(suffix) for suffix in forex_suffixes):
                categories["Forex"].append(symbol)
            elif any(crypto in symbol for crypto in crypto_suffixes):
                categories["Crypto"].append(symbol)
            elif any(stock in symbol for stock in stock_names):
                categories["Stocks"].append(symbol)
            else:
                categories["Other"].append(symbol)

        return {k: v for k, v in categories.items() if v}  # Remove empty categories

    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter pairs (e.g., EUR, BTC)...")
        self.search_input.textChanged.connect(self.filter_pairs)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Buttons for select/deselect all
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_all_btn)
        layout.addLayout(button_layout)

        # Tabs for categories
        self.tabs = QTabWidget()
        for category, symbols in self.categories.items():
            tab_widget = QWidget()
            tab_layout = QVBoxLayout()

            # Category select/deselect
            category_btn_layout = QHBoxLayout()
            category_label = QLabel(f"{category} ({len(symbols)})")
            self.category_checkboxes[category] = QCheckBox(f"Select all {category}")
            self.category_checkboxes[category].stateChanged.connect(
                lambda state, cat=category: self.toggle_category(cat, state)
            )
            category_btn_layout.addWidget(category_label)
            category_btn_layout.addWidget(self.category_checkboxes[category])
            category_btn_layout.addStretch()
            tab_layout.addLayout(category_btn_layout)

            # Scrollable area for checkboxes
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout()

            for symbol in symbols:
                checkbox = QCheckBox(symbol)
                checkbox.stateChanged.connect(self.on_checkbox_changed)
                self.checkboxes[symbol] = checkbox
                scroll_layout.addWidget(checkbox)

            scroll_layout.addStretch()
            scroll_widget.setLayout(scroll_layout)
            scroll.setWidget(scroll_widget)
            tab_layout.addWidget(scroll)

            tab_widget.setLayout(tab_layout)
            self.tabs.addTab(tab_widget, category)

        layout.addWidget(self.tabs)

        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addStretch()
        dialog_buttons.addWidget(ok_btn)
        dialog_buttons.addWidget(cancel_btn)
        layout.addLayout(dialog_buttons)

        self.setLayout(layout)

    def on_checkbox_changed(self):
        """Handle checkbox state changes."""
        # Update category checkbox state
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
                self.category_checkboxes[category].setCheckState(Qt.PartiallyChecked)
                self.category_checkboxes[category].blockSignals(False)

    def toggle_category(self, category: str, state):
        """Toggle all pairs in a category.

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

    def select_all(self):
        """Select all pairs."""
        for checkbox in self.checkboxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)
        for cat_checkbox in self.category_checkboxes.values():
            cat_checkbox.blockSignals(True)
            cat_checkbox.setCheckState(Qt.Checked)
            cat_checkbox.blockSignals(False)

    def clear_all(self):
        """Deselect all pairs."""
        for checkbox in self.checkboxes.values():
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
        for cat_checkbox in self.category_checkboxes.values():
            cat_checkbox.blockSignals(True)
            cat_checkbox.setCheckState(Qt.Unchecked)
            cat_checkbox.blockSignals(False)

    def filter_pairs(self):
        """Filter pairs based on search input."""
        search_term = self.search_input.text().upper()
        self.search_term = search_term

        for symbol, checkbox in self.checkboxes.items():
            if search_term in symbol:
                checkbox.show()
            else:
                checkbox.hide()

    def get_selected_pairs(self) -> List[str]:
        """Get list of selected pairs.

        Returns:
            List of selected trading symbols
        """
        return [
            symbol
            for symbol, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]

    def accept(self):
        """Override accept to validate selection."""
        selected = self.get_selected_pairs()
        if not selected:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select at least one pair before continuing.",
            )
            return

        self.selected_pairs = selected
        self.logger.info("Selected %d pairs: %s", len(selected), ", ".join(selected))
        super().accept()

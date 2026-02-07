"""WebSocket-based live trading updates system.

Provides real-time signal updates, trade execution events, and volatility
metrics to connected clients using Socket.IO.
"""

import threading
from datetime import datetime
from queue import Queue
from typing import Dict

from flask import Flask
from flask_socketio import SocketIO, emit, join_room

from src.utils.logging_factory import LoggingFactory


class LiveTradingBroadcaster:
    """Manages real-time updates for live trading signals and trades."""

    def __init__(self):
        """Initialize the broadcaster."""
        self.logger = LoggingFactory.get_logger(__name__)
        self.socketio = None
        self.signal_queue = Queue()
        self.trade_queue = Queue()
        self.metrics_queue = Queue()
        self.connected_clients = set()
        self.broadcast_thread = None
        self.running = False

    def init_socketio(self, app: Flask) -> SocketIO:
        """Initialize Socket.IO with Flask app.

        Args:
            app: Flask application instance

        Returns:
            Configured SocketIO instance
        """
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            ping_timeout=60,
            ping_interval=25,
            async_mode="threading",
        )
        self._register_handlers()
        return self.socketio

    def _register_handlers(self):
        """Register Socket.IO event handlers."""

        @self.socketio.on("connect")
        def handle_connect():
            client_id = threading.current_thread().ident
            self.connected_clients.add(client_id)
            self.logger.info(f"Client connected: {client_id}")
            emit(
                "connection_response",
                {"status": "connected", "timestamp": datetime.now().isoformat()},
            )

        @self.socketio.on("disconnect")
        def handle_disconnect():
            client_id = threading.current_thread().ident
            self.connected_clients.discard(client_id)
            self.logger.info(f"Client disconnected: {client_id}")

        @self.socketio.on("subscribe_signals")
        def handle_subscribe_signals():
            join_room("signals")
            emit("status", {"message": "Subscribed to trading signals"})

        @self.socketio.on("subscribe_trades")
        def handle_subscribe_trades():
            join_room("trades")
            emit("status", {"message": "Subscribed to trade executions"})

        @self.socketio.on("subscribe_metrics")
        def handle_subscribe_metrics():
            join_room("metrics")
            emit("status", {"message": "Subscribed to live metrics"})

    def broadcast_signal(self, signal: Dict):
        """Broadcast a trading signal to all connected clients.

        Args:
            signal: Signal dictionary with structure:
                {
                    'symbol': 'EURUSD',
                    'action': 'buy'|'sell',
                    'strategy': 'RSI',
                    'timeframe': 15,
                    'entry_price': 1.2054,
                    'timestamp': '2024-01-24T10:30:45Z',
                    'confidence': 0.85,
                    'signal_strength': 0.72
                }
        """
        if not self.socketio:
            return

        signal_data = {
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "strategy": signal.get("strategy", "unknown"),
            "timeframe": signal.get("timeframe"),
            "entry_price": signal.get("entry_price"),
            "timestamp": signal.get("timestamp", datetime.now().isoformat()),
            "confidence": signal.get("confidence", 0),
            "signal_strength": signal.get("signal_strength", 0),
        }

        self.logger.info(
            f"Broadcasting signal: {signal_data['symbol']} {signal_data['action']}"
        )
        self.socketio.emit("new_signal", signal_data, room="signals")

    def broadcast_trade(self, trade: Dict):
        """Broadcast a trade execution event.

        Args:
            trade: Trade dictionary with structure:
                {
                    'symbol': 'EURUSD',
                    'side': 'buy'|'sell',
                    'volume': 0.01,
                    'entry_price': 1.2054,
                    'stop_loss': 1.2044,
                    'take_profit': 1.2074,
                    'timestamp': '2024-01-24T10:30:45Z',
                    'status': 'executed'|'pending'|'failed',
                    'error': None or error message
                }
        """
        if not self.socketio:
            return

        trade_data = {
            "symbol": trade.get("symbol"),
            "side": trade.get("side"),
            "volume": trade.get("volume"),
            "entry_price": trade.get("entry_price"),
            "stop_loss": trade.get("stop_loss"),
            "take_profit": trade.get("take_profit"),
            "timestamp": trade.get("timestamp", datetime.now().isoformat()),
            "status": trade.get("status", "unknown"),
            "error": trade.get("error"),
        }

        self.logger.info(
            f"Broadcasting trade: {trade_data['symbol']} {trade_data['side']} {trade_data['status']}"
        )
        self.socketio.emit("new_trade", trade_data, room="trades")

    def broadcast_metrics(self, metrics: Dict):
        """Broadcast live trading metrics.

        Args:
            metrics: Metrics dictionary with structure:
                {
                    'net_profit': 1234.56,
                    'win_rate': 0.615,
                    'open_positions': 3,
                    'active_pairs': ['EURUSD', 'GBPUSD'],
                    'top_signals': [...],
                    'volatility_ranking': [...],
                    'timestamp': '2024-01-24T10:30:45Z'
                }
        """
        if not self.socketio:
            return

        metrics_data = {
            "net_profit": metrics.get("net_profit", 0),
            "win_rate": metrics.get("win_rate", 0),
            "open_positions": metrics.get("open_positions", 0),
            "active_pairs": metrics.get("active_pairs", []),
            "top_signals": metrics.get("top_signals", []),
            "volatility_ranking": metrics.get("volatility_ranking", []),
            "timestamp": metrics.get("timestamp", datetime.now().isoformat()),
        }

        self.logger.debug("Broadcasting metrics update")
        self.socketio.emit("metrics_update", metrics_data, room="metrics")

    def broadcast_volatility_update(self, volatility_data: Dict):
        """Broadcast volatility ranking update.

        Args:
            volatility_data: Dictionary with:
                {
                    'pairs': [
                        {'symbol': 'EURUSD', 'atr': 0.0025, 'rank': 1},
                        ...
                    ],
                    'timestamp': '2024-01-24T10:30:45Z'
                }
        """
        if not self.socketio:
            return

        self.logger.debug(
            f"Broadcasting volatility update with {len(volatility_data.get('pairs', []))} pairs"
        )
        self.socketio.emit("volatility_update", volatility_data, room="metrics")

    def broadcast_status(self, status: Dict):
        """Broadcast bot status update.

        Args:
            status: Status dictionary with:
                {
                    'state': 'running'|'paused'|'stopped',
                    'message': 'Status message',
                    'uptime_seconds': 3600,
                    'last_sync': '2024-01-24T10:30:45Z'
                }
        """
        if not self.socketio:
            return

        self.logger.info(f"Broadcasting status: {status.get('state')}")
        self.socketio.emit("status_update", status)

    def get_connected_count(self) -> int:
        """Get number of connected clients.

        Returns:
            Number of connected clients
        """
        return len(self.connected_clients)


# Global broadcaster instance
broadcaster = LiveTradingBroadcaster()

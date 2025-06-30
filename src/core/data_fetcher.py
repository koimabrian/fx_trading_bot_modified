# src/core/data_fetcher.py
import yaml
import pandas as pd
import logging
import MetaTrader5 as mt5

class DataFetcher:
    def __init__(self, mt5_conn, db):
        self.mt5_conn = mt5_conn
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.pairs = self.load_pairs()

    def load_pairs(self):
        """Load trading pairs from config"""
        try:
            with open('src/config/config.yaml', 'r') as file:
                config = yaml.safe_load(file)
            return config.get('pairs', [])
        except Exception as e:
            self.logger.error(f"Failed to load pairs from config: {e}")
            return []

    def sync_data(self):
        """Fetch and sync market data for all configured pairs to market_data.sqlite"""
        if not self.mt5_conn.initialize():
            self.logger.error("Failed to initialize MT5 connection")
            return
        for pair in self.pairs:
            symbol = pair['symbol']
            timeframe = pair['timeframe']
            mt5_timeframe = getattr(mt5, f"TIMEFRAME_M{timeframe}" if timeframe < 60 else f"TIMEFRAME_H{timeframe//60}", mt5.TIMEFRAME_M15)
            data = self.mt5_conn.fetch_market_data(symbol, mt5_timeframe, count=100)
            if data is not None:
                try:
                    data['symbol'] = symbol
                    data['timeframe'] = f"M{timeframe}" if timeframe < 60 else f"H{timeframe//60}"
                    data.to_sql('market_data', self.db.conn, if_exists='append', index=False)
                    self.db.conn.commit()
                    self.logger.info(f"Updated market_data.sqlite with {len(data)} rows for {symbol} ({timeframe})")
                except Exception as e:
                    self.logger.error(f"Failed to update market_data.sqlite for {symbol}: {e}")
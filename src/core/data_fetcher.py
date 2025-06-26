# Purpose: Fetch and sync market data from MT5
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
        """Fetch and sync market data for all configured pairs"""
        for pair in self.pairs:
            symbol = pair['symbol']
            timeframe = pair['timeframe']
            mt5_timeframe = getattr(mt5, f"TIMEFRAME_M{timeframe}", mt5.TIMEFRAME_M15)
            data = self.mt5_conn.fetch_market_data(symbol, mt5_timeframe, count=100)
            if data is not None:
                try:
                    data['symbol'] = symbol
                    data['timeframe'] = f"M{timeframe}"
                    data.to_sql('market_data', self.db.conn, if_exists='append', index=False)
                    self.db.conn.commit()
                    self.logger.info(f"Updated database with {len(data)} rows for {symbol} (M{timeframe})")
                except Exception as e:
                    self.logger.error(f"Failed to update database for {symbol}: {e}")
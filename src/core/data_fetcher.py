# fx_trading_bot/src/backtesting/data_pipeline.py
# Purpose: Preprocesses and validates historical data for backtesting
import pandas as pd
import logging
from src.database.db_manager import DatabaseManager

class DataPipeline:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def fetch_data(self, symbol, timeframe, start_date=None, end_date=None):
        """Fetch and preprocess historical data"""
        try:
            # Normalize symbol to handle variations (e.g., BTCUSD vs. BTCUSDm)
            query = f"SELECT * FROM market_data WHERE symbol = ? AND timeframe = ? ORDER BY time"
            params = (symbol, f"M{timeframe}")
            if start_date and end_date:
                query += " AND time BETWEEN ? AND ?"
                params += (start_date, end_date)
            data = pd.read_sql(query, self.db.conn, params=params)
            if data.empty:
                self.logger.warning(f"No data found for {symbol} on M{timeframe}")
                # Try alternative symbol (e.g., BTCUSDm)
                alt_symbol = f"{symbol}m" if not symbol.endswith('m') else symbol[:-1]
                query = f"SELECT * FROM market_data WHERE symbol = ? AND timeframe = ? ORDER BY time"
                params = (alt_symbol, f"M{timeframe}")
                if start_date and end_date:
                    query += " AND time BETWEEN ? AND ?"
                    params += (start_date, end_date)
                data = pd.read_sql(query, self.db.conn, params=params)
                if data.empty:
                    self.logger.warning(f"No data found for {alt_symbol} on M{timeframe}")
                    return pd.DataFrame()

            data['time'] = pd.to_datetime(data['time'])
            data.set_index('time', inplace=True)
            data = data.sort_index()
            data = data.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'tick_volume': 'Volume'
            })
            if 'Volume' not in data.columns:
                data['Volume'] = 0
            if not self.validate_data(data):
                self.logger.error(f"Invalid data for {symbol} on M{timeframe}")
                return pd.DataFrame()
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch data for {symbol} on M{timeframe}: {e}")
            return pd.DataFrame()

    def validate_data(self, data: pd.DataFrame):
        """Validate data integrity"""
        if len(data) < 100:
            self.logger.warning("Insufficient data points")
            return False
        if data[['Open', 'High', 'Low', 'Close']].isnull().any().any():
            self.logger.warning("Missing values in OHLC data")
            return False
        if (data['High'] < data['Low']).any() or (data['Open'] < 0).any():
            self.logger.warning("Invalid price data")
            return False
        return True
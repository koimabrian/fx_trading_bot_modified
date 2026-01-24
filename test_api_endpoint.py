#!/usr/bin/env python3
"""Test the API flow to debug the 500 error."""

import sys
import yaml

sys.path.insert(0, ".")

from src.utils.indicator_analyzer import IndicatorAnalyzer
from src.database.db_manager import DatabaseManager
from flask import Flask, jsonify

app = Flask(__name__)

# Load config
with open("src/config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Create and connect database (like dashboard_server does)
db = DatabaseManager(config)
db.connect()


@app.route("/test-api/<symbol>/<timeframe>")
def test_api(symbol, timeframe):
    """Test endpoint that mimics api_signal_checks."""
    try:
        analyzer = IndicatorAnalyzer(db, config=config)
        checks = analyzer.get_entry_signal_checks(symbol, timeframe)
        return jsonify({"status": "success", "data": checks})
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5001, debug=True)

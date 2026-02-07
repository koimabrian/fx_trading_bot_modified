#!/usr/bin/env python3
"""
Test script to verify the live_trades table schema is correct.
This validates:
1. Table exists and is named 'live_trades'
2. order_id column is NOT UNIQUE (allows duplicates)
3. deal_id and ticket columns ARE UNIQUE
4. All required indexes exist
"""

import sqlite3
import tempfile
import os
from src.database.migrations import DatabaseMigrations


def test_schema():
    """Test the new schema with a temporary database."""
    
    # Create a temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
    temp_db.close()
    
    try:
        print("Creating temporary database...")
        conn = sqlite3.connect(temp_db.name)
        conn.row_factory = sqlite3.Row
        
        # Create schema
        print("Creating tables...")
        migrations = DatabaseMigrations(conn)
        if not migrations.create_tables():
            print("❌ Failed to create tables")
            return False
        
        print("Creating indexes...")
        if not migrations.create_indexes():
            print("❌ Failed to create indexes")
            return False
        
        # Verify table exists with correct name
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='live_trades'")
        if not cursor.fetchone():
            print("❌ Table 'live_trades' not found")
            return False
        print("✓ Table 'live_trades' exists")
        
        # Check table schema
        cursor.execute("PRAGMA table_info(live_trades)")
        columns = {row[1]: row for row in cursor.fetchall()}
        
        # Verify order_id column exists and is NOT marked as UNIQUE in schema
        if 'order_id' not in columns:
            print("❌ Column 'order_id' not found")
            return False
        print("✓ Column 'order_id' exists")
        
        # Verify deal_id and ticket exist
        if 'deal_id' not in columns:
            print("❌ Column 'deal_id' not found")
            return False
        if 'ticket' not in columns:
            print("❌ Column 'ticket' not found")
            return False
        print("✓ Columns 'deal_id' and 'ticket' exist")
        
        # Check indexes
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='live_trades'")
        indexes = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Verify UNIQUE indexes exist for deal_id and ticket
        expected_unique_indexes = [
            'idx_live_trades_deal_id_unique',
            'idx_live_trades_ticket_unique'
        ]
        
        for idx_name in expected_unique_indexes:
            if idx_name not in indexes:
                print(f"❌ UNIQUE index '{idx_name}' not found")
                return False
            if 'UNIQUE' not in indexes[idx_name].upper():
                print(f"❌ Index '{idx_name}' is not UNIQUE")
                return False
        print("✓ UNIQUE indexes on deal_id and ticket exist")
        
        # Verify non-UNIQUE index exists for order_id
        if 'idx_live_trades_order_id' not in indexes:
            print("❌ Index 'idx_live_trades_order_id' not found")
            return False
        if 'UNIQUE' in indexes['idx_live_trades_order_id'].upper():
            print("❌ Index 'idx_live_trades_order_id' should NOT be UNIQUE")
            return False
        print("✓ Non-UNIQUE index on order_id exists")
        
        # Test inserting multiple deals with same order_id
        print("\nTesting duplicate order_id insertion...")
        cursor.execute("""
            INSERT INTO tradable_pairs (symbol) VALUES ('EURUSD')
        """)
        symbol_id = cursor.lastrowid
        
        # Insert first deal with order_id 12345
        cursor.execute("""
            INSERT INTO live_trades 
            (symbol_id, timeframe, strategy_name, trade_type, volume, open_price, 
             order_id, deal_id, ticket, status)
            VALUES (?, 'H1', 'TEST', 'BUY', 1.0, 1.1234, 12345, 1001, 5001, 'closed')
        """, (symbol_id,))
        print("✓ Inserted deal #1001 with order_id=12345")
        
        # Insert second deal with SAME order_id 12345
        try:
            cursor.execute("""
                INSERT INTO live_trades 
                (symbol_id, timeframe, strategy_name, trade_type, volume, open_price, 
                 order_id, deal_id, ticket, status)
                VALUES (?, 'H1', 'TEST', 'BUY', 0.5, 1.1235, 12345, 1002, 5002, 'closed')
            """, (symbol_id,))
            print("✓ Inserted deal #1002 with order_id=12345 (DUPLICATE - ALLOWED!)")
        except sqlite3.IntegrityError as e:
            print(f"❌ Failed to insert duplicate order_id: {e}")
            return False
        
        # Insert third deal with SAME order_id 12345
        try:
            cursor.execute("""
                INSERT INTO live_trades 
                (symbol_id, timeframe, strategy_name, trade_type, volume, open_price, 
                 order_id, deal_id, ticket, status)
                VALUES (?, 'H1', 'TEST', 'BUY', 0.3, 1.1236, 12345, 1003, 5003, 'closed')
            """, (symbol_id,))
            print("✓ Inserted deal #1003 with order_id=12345 (DUPLICATE - ALLOWED!)")
        except sqlite3.IntegrityError as e:
            print(f"❌ Failed to insert duplicate order_id: {e}")
            return False
        
        # Verify all three deals are in database
        cursor.execute("""
            SELECT COUNT(*) as count FROM live_trades WHERE order_id = 12345
        """)
        count = cursor.fetchone()[0]
        if count != 3:
            print(f"❌ Expected 3 deals with order_id=12345, found {count}")
            return False
        print(f"✓ All 3 deals with order_id=12345 successfully stored")
        
        # Test that duplicate deal_id is NOT allowed
        print("\nTesting duplicate deal_id rejection...")
        try:
            cursor.execute("""
                INSERT INTO live_trades 
                (symbol_id, timeframe, strategy_name, trade_type, volume, open_price, 
                 order_id, deal_id, ticket, status)
                VALUES (?, 'H1', 'TEST', 'BUY', 0.2, 1.1237, 12346, 1001, 5004, 'closed')
            """, (symbol_id,))
            print("❌ Duplicate deal_id was allowed (should have been rejected)")
            return False
        except sqlite3.IntegrityError:
            print("✓ Duplicate deal_id correctly rejected")
        
        # Test that duplicate ticket is NOT allowed
        print("\nTesting duplicate ticket rejection...")
        try:
            cursor.execute("""
                INSERT INTO live_trades 
                (symbol_id, timeframe, strategy_name, trade_type, volume, open_price, 
                 order_id, deal_id, ticket, status)
                VALUES (?, 'H1', 'TEST', 'BUY', 0.2, 1.1238, 12347, 1004, 5001, 'closed')
            """, (symbol_id,))
            print("❌ Duplicate ticket was allowed (should have been rejected)")
            return False
        except sqlite3.IntegrityError:
            print("✓ Duplicate ticket correctly rejected")
        
        conn.commit()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ ALL SCHEMA TESTS PASSED!")
        print("="*60)
        print("\nKey validations:")
        print("  • Table renamed from 'trades' to 'live_trades'")
        print("  • order_id allows duplicates (multiple deals per order)")
        print("  • deal_id is UNIQUE (each deal is unique)")
        print("  • ticket is UNIQUE (each position is unique)")
        print("  • Indexes created correctly")
        return True
        
    finally:
        # Clean up
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)
            print(f"\nCleaned up temporary database")


if __name__ == '__main__':
    import sys
    success = test_schema()
    sys.exit(0 if success else 1)

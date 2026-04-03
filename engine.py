import sqlite3
import random
import os

def update_market_prices():
    db_path = os.path.join(os.path.dirname(__file__), 'shadow_trader.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    stocks = cursor.execute('SELECT id, price FROM stocks').fetchall()
    for stock_id, current_price in stocks:
        # Variation de -2% à +2.5%
        change = random.uniform(0.98, 1.025)
        new_price = round(current_price * change, 2)
        cursor.execute('UPDATE stocks SET old_price = ?, price = ? WHERE id = ?', 
                       (current_price, new_price, stock_id))
    
    conn.commit()
    conn.close()

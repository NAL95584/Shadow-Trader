from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import sqlite3
import os
import threading
import time
from datetime import datetime

# --- CONFIGURATION INITIALE ---
app = Flask(__name__)
app.secret_key = 'shadow_trader_key_2026'
bcrypt = Bcrypt(app)
chat_history = [] 

def get_db_connection():
    # Utilise le chemin relatif pour que ça marche partout
    db_path = os.path.join(os.path.dirname(__file__), 'shadow_trader.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# --- IMPORT DU MOTEUR ---
try:
    from engine import update_market_prices
    def market_loop():
        while True:
            with app.app_context():
                try:
                    update_market_prices()
                except:
                    pass
            time.sleep(60)
    threading.Thread(target=market_loop, daemon=True).start()
except ImportError:
    print("Moteur non détecté.")

# --- ROUTES ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if user and bcrypt.check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect(url_for('dashboard'))
    flash('Identifiants incorrects', 'danger')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    stocks = conn.execute('SELECT * FROM stocks').fetchall()
    # FIX: On initialise toujours unread_msg pour éviter l'erreur Jinja2
    unread_msg = 0
    conn.close()
    return render_template('dashboard.html', user=user, stocks=stocks, unread_msg=unread_msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import sqlite3
import os
import threading
import time
from datetime import datetime
from engine import update_market_prices
from security_audit import run_security_check

# --- CONFIGURATION INITIALE ---
app = Flask(__name__)
app.secret_key = 'shadow_trader_secret_key_pro'
bcrypt = Bcrypt(app)
chat_history = [] # Stockage temporaire des messages

def get_db_connection():
    conn = sqlite3.connect('shadow_trader.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- BOUCLE DE MARCHÉ & SÉCURITÉ (THREADS) ---
def market_loop():
    while True:
        with app.app_context():
            try:
                update_market_prices()
                run_security_check()
                print("Tick Système : Marché et Sécurité OK.")
            except Exception as e:
                print(f"Erreur système dans la boucle : {e}")
        time.sleep(60)

# Lancement automatique du moteur en arrière-plan
threading.Thread(target=market_loop, daemon=True).start()

# --- ROUTES AUTHENTIFICATION ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
        conn.commit()
        flash('Inscription réussie !', 'success')
    except sqlite3.IntegrityError:
        flash('Pseudo déjà pris.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('home'))

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if user and bcrypt.check_password_hash(user['password'], password):
        if user['is_banned']:
            flash(f"Banni : {user['ban_reason']}", 'danger')
            return redirect(url_for('home'))
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect(url_for('dashboard'))
    flash('Identifiants incorrects.', 'danger')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- ROUTES JEU (DASHBOARD, MARCHÉ, CHAT) ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('''
        SELECT users.*, corps.name AS corp_name FROM users 
        LEFT JOIN corps ON users.corp_id = corps.id WHERE users.id = ?''', (session['user_id'],)).fetchone()
    stocks = conn.execute('SELECT * FROM stocks').fetchall()
    unread_msg = conn.execute('SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0', (session['user_id'],)).fetchone()[0]
    conn.close()
    return render_template('dashboard.html', user=user, stocks=stocks, unread_msg=unread_msg)

@app.route('/buy', methods=['POST'])
def buy():
    data = request.json
    conn = get_db_connection()
    user = conn.execute('SELECT cash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    stock = conn.execute('SELECT price FROM stocks WHERE id = ?', (data['stock_id'],)).fetchone()
    if user['cash'] >= stock['price']:
        conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (stock['price'], session['user_id']))
        conn.commit()
        conn.close()
        return {"status": "success"}
    conn.close()
    return {"status": "error", "message": "Fonds insuffisants"}

@app.route('/get_messages')
def get_msgs():
    return {"messages": chat_history}

@app.route('/send_message', methods=['POST'])
def send_msg():
    data = request.json
    msg_obj = {"user": session.get('username'), "text": data['message'], "time": datetime.now().strftime("%H:%M")}
    chat_history.append(msg_obj)
    if len(chat_history) > 50: chat_history.pop(0)
    return {"status": "success"}

# --- ROUTES CORPORATIONS ---

@app.route('/corporation')
def corporation():
    if 'user_id' not in session: return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT users.*, corps.name AS corp_name FROM users LEFT JOIN corps ON users.corp_id = corps.id WHERE users.id = ?', (session['user_id'],)).fetchone()
    corp = None
    members = []
    if user['corp_id']:
        corp = conn.execute('SELECT * FROM corps WHERE id = ?', (user['corp_id'],)).fetchone()
        members = conn.execute('SELECT id, username FROM users WHERE corp_id = ?', (user['corp_id'],)).fetchall()
    conn.close()
    return render_template('corporation.html', user=user, corp=corp, members=members)

@app.route('/create_corp', methods=['POST'])
def create_corp():
    name, code = request.form['corp_name'], request.form['invite_code']
    conn = get_db_connection()
    user = conn.execute('SELECT cash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user['cash'] >= 100000:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO corps (name, ceo_id, invite_code, treasury) VALUES (?, ?, ?, 0)', (name, session['user_id'], code))
        conn.execute('UPDATE users SET cash = cash - 100000, corp_id = ? WHERE id = ?', (cursor.lastrowid, session['user_id']))
        conn.commit()
        flash('Corporation créée !', 'success')
    else:
        flash('Fonds insuffisants', 'danger')
    conn.close()
    return redirect(url_for('corporation'))

# --- ROUTES PRÊTS (LOANS) ---

@app.route('/loans')
def loans():
    if 'user_id' not in session: return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    pending = conn.execute('SELECT loans.*, users.username, users.stars FROM loans JOIN users ON loans.borrower_id = users.id WHERE status = "PENDING" AND borrower_id != ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('loans.html', user=user, pending_loans=pending)

# --- LANCEMENT ---

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

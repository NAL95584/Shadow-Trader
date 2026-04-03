from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import sqlite3
import os
import threading
import time
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = 'shadow_trader_ultra_secret'
bcrypt = Bcrypt(app)
chat_history = []

# Fonction pour se connecter à la base SQLite
def get_db_connection():
    conn = sqlite3.connect('shadow_trader.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- MOTEUR DE PRIX (Background) ---
# On importe la fonction depuis ton fichier engine.py
try:
    from engine import update_market_prices
    def market_loop():
        while True:
            with app.app_context():
                try:
                    update_market_prices()
                    print("Tick Marché : Prix mis à jour.")
                except Exception as e:
                    print(f"Erreur moteur : {e}")
            time.sleep(60)
    threading.Thread(target=market_loop, daemon=True).start()
except ImportError:
    print("Attention: engine.py introuvable. Le marché sera statique.")

# --- ROUTES AUTHENTIFICATION ---

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password, cash) VALUES (?, ?, ?)', 
                         (username, hashed_pw, 10000.0))
            conn.commit()
            flash('Compte créé ! Connectez-vous.', 'success')
            return redirect(url_for('home'))
        except:
            flash('Erreur : Pseudo déjà utilisé.', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and bcrypt.check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect(url_for('dashboard'))
    
    flash('Identifiants invalides.', 'danger')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- ROUTES TRADING & DASHBOARD ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    stocks = conn.execute('SELECT * FROM stocks').fetchall()
    
    # AJOUTE CETTE LIGNE ICI POUR FIXER L'ERREUR :
    unread_msg = 0 
    
    conn.close()
    return render_template('dashboard.html', user=user, stocks=stocks, unread_msg=unread_msg)

@app.route('/scoreboard')
def scoreboard():
    conn = get_db_connection()
    users = conn.execute('SELECT username, cash FROM users ORDER BY cash DESC LIMIT 10').fetchall()
    conn.close()
    return render_template('scoreboard.html', users=users)

# --- CHAT API ---

@app.route('/send_message', methods=['POST'])
def send_msg():
    data = request.json
    msg = {"user": session.get('username'), "text": data['message'], "time": datetime.now().strftime("%H:%M")}
    chat_history.append(msg)
    return {"status": "success"}

@app.route('/get_messages')
def get_msgs():
    return {"messages": chat_history}

# --- LANCEMENT ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'shadow_trader_secret_key_pro' # Clé pour sécuriser les sessions
bcrypt = Bcrypt(app)

# Connexion à la base de données
def get_db_connection():
    conn = sqlite3.connect('shadow_trader.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- ROUTES DE CONNEXION ---

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
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                     (username, hashed_password))
        conn.commit()
        flash('Inscription réussie ! Connectez-vous.', 'success')
    except sqlite3.IntegrityError:
        flash('Ce pseudo existe déjà.', 'danger')
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
            flash(f"Accès refusé. Motif : {user['ban_reason']}", 'danger')
            return redirect(url_for('home'))
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_admin'] = user['is_admin']
        return redirect(url_for('dashboard'))
    
    flash('Pseudo ou mot de passe incorrect.', 'danger')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# --- TABLEAU DE BORD (DASHBOARD) ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    stocks = conn.execute('SELECT * FROM stocks').fetchall()
    # On récupère les messages non lus pour la pastille de notification
    unread_msg = conn.execute('SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0', 
                              (session['user_id'],)).fetchone()[0]
    conn.close()
    
    return render_template('dashboard.html', user=user, stocks=stocks, unread_msg=unread_msg)

if __name__ == '__main__':
    # On écoute sur 0.0.0.0 pour que tes camarades puissent se connecter via ton IP
    app.run(host='0.0.0.0', port=5000, debug=True)

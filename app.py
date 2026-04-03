import threading
import time
from engine import update_market_prices

# ... (reste de ton code app.py) ...

# Fonction qui tourne en boucle toutes les 60 secondes
def market_loop():
    while True:
        with app.app_context():
            try:
                update_market_prices()
                print("Tick Marché : Prix actualisés.")
            except Exception as e:
                print(f"Erreur moteur : {e}")
        time.sleep(60) # Attendre 1 minute

# Lancer le thread du marché au démarrage
threading.Thread(target=market_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
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
    # On utilise une jointure LEFT JOIN pour récupérer le nom de la corp en même temps que l'user
    query = '''
        SELECT users.*, corps.name AS corp_name 
        FROM users 
        LEFT JOIN corps ON users.corp_id = corps.id 
        WHERE users.id = ?
    '''
    user = conn.execute(query, (session['user_id'],)).fetchone()
    stocks = conn.execute('SELECT * FROM stocks').fetchall()
    unread_msg = conn.execute('SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0', 
                              (session['user_id'],)).fetchone()[0]
    conn.close()
    
    return render_template('dashboard.html', user=user, stocks=stocks, unread_msg=unread_msg)

if __name__ == '__main__':
    from datetime import datetime

# Liste temporaire pour le chat (en attendant la BDD chat)
chat_history = []

@app.route('/get_user_stats')
def get_user_stats():
    if 'user_id' not in session: return {"error": "unauthorized"}, 401
    conn = get_db_connection()
    user = conn.execute('SELECT cash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return {"cash": user['cash']}

@app.route('/send_message', methods=['POST'])
def send_msg():
    data = request.json
    msg_obj = {
        "user": session.get('username', 'Anonyme'),
        "text": data['message'],
        "time": datetime.now().strftime("%H:%M")
    }
    chat_history.append(msg_obj)
    if len(chat_history) > 50: chat_history.pop(0) # Garder les 50 derniers
    return {"status": "success"}

@app.route('/get_messages')
def get_msgs():
    return {"messages": chat_history}

@app.route('/buy', methods=['POST'])
def buy():
    # Logique d'achat simplifiée pour le test
    data = request.json
    conn = get_db_connection()
    user = conn.execute('SELECT cash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    stock = conn.execute('SELECT price FROM stocks WHERE id = ?', (data['stock_id'],)).fetchone()
    
    if user['cash'] >= stock['price']:
        new_cash = user['cash'] - stock['price']
        conn.execute('UPDATE users SET cash = ? WHERE id = ?', (new_cash, session['user_id']))
        conn.commit()
        conn.close()
        return {"status": "success"}
    
    conn.close()
    return {"status": "error", "message": "Fonds insuffisants !"}
    @app.route('/corporation')
def corporation():
    if 'user_id' not in session: return redirect(url_for('home'))
    conn = get_db_connection()
    
    # Infos utilisateur et sa corp
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
    name = request.form['corp_name']
    code = request.form['invite_code']
    user_id = session['user_id']
    
    conn = get_db_connection()
    user = conn.execute('SELECT cash FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user['cash'] >= 100000:
        # Création de la corp
        cursor = conn.cursor()
        cursor.execute('INSERT INTO corps (name, ceo_id, invite_code, treasury) VALUES (?, ?, ?, ?)', 
                       (name, user_id, code, 0))
        corp_id = cursor.lastrowid
        
        # Mise à jour de l'user (Paye 100k + devient membre)
        conn.execute('UPDATE users SET cash = cash - 100000, corp_id = ? WHERE id = ?', (corp_id, user_id))
        conn.commit()
        flash(f"Corporation {name} créée avec succès !", "success")
    else:
        flash("Fonds insuffisants (100 000 € requis).", "danger")
    
    conn.close()
    return redirect(url_for('corporation'))

@app.route('/join_corp', methods=['POST'])
def join_corp():
    code = request.form['invite_code']
    conn = get_db_connection()
    corp = conn.execute('SELECT id FROM corps WHERE invite_code = ?', (code,)).fetchone()
    
    if corp:
        conn.execute('UPDATE users SET corp_id = ? WHERE id = ?', (corp['id'], session['user_id']))
        conn.commit()
        flash("Bienvenue dans votre nouvelle entreprise.", "success")
    else:
        flash("Code d'invitation invalide.", "danger")
    
    conn.close()
    return redirect(url_for('corporation'))
@app.route('/loans')
def loans():
    if 'user_id' not in session: return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Prêts en attente de financement
    pending_loans = conn.execute('''
        SELECT loans.*, users.username, users.stars 
        FROM loans JOIN users ON loans.borrower_id = users.id 
        WHERE status = 'PENDING' AND borrower_id != ?''', (session['user_id'],)).fetchall()
    
    # Mes contrats (Emprunteur ou Prêteur)
    my_loans = conn.execute('''
        SELECT l.*, u.username as partner_name 
        FROM loans l 
        JOIN users u ON (l.lender_id = u.id OR l.borrower_id = u.id)
        WHERE (l.lender_id = ? OR l.borrower_id = ?) AND u.id != ?''', 
        (session['user_id'], session['user_id'], session['user_id'])).fetchall()
    
    conn.close()
    return render_template('loans.html', user=user, pending_loans=pending_loans, my_loans=my_loans)

@app.route('/request_loan', methods=['POST'])
def request_loan():
    amount = float(request.form['amount'])
    interest = float(request.form['interest'])
    conn = get_db_connection()
    conn.execute('INSERT INTO loans (borrower_id, amount, interest_rate, status) VALUES (?, ?, ?, ?)',
                 (session['user_id'], amount, interest, 'PENDING'))
    conn.commit()
    conn.close()
    flash("Demande de prêt publiée sur le réseau.", "success")
    return redirect(url_for('loans'))

@app.route('/fund_loan', methods=['POST'])
def fund_loan():
    loan_id = request.form['loan_id']
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id = ?', (loan_id,)).fetchone()
    lender = conn.execute('SELECT cash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if lender['cash'] >= loan['amount']:
        # Transaction atomique
        conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (loan['amount'], session['user_id']))
        conn.execute('UPDATE users SET cash = cash + ? WHERE id = ?', (loan['amount'], loan['borrower_id']))
        conn.execute('UPDATE loans SET lender_id = ?, status = "ACTIVE" WHERE id = ?', (session['user_id'], loan_id))
        conn.commit()
        flash("Prêt accordé ! Vous recevrez les intérêts au remboursement.", "success")
    else:
        flash("Solde insuffisant pour prêter.", "danger")
    conn.close()
    return redirect(url_for('loans'))

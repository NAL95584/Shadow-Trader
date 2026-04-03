from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
import sqlite3
import os
import threading
import time
from datetime import datetime

# --- CONFIGURATION ---
app = Flask(__name__)
app.secret_key = 'shadow_trader_key_2026'
bcrypt = Bcrypt(app)

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'shadow_trader.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# --- MOTEUR DE MARCHÉ ---
try:
    from engine import update_market_prices
    def market_loop():
        while True:
            with app.app_context():
                try:
                    update_market_prices()
                except Exception as e:
                    print(f"Erreur moteur: {e}")
            time.sleep(60)
    threading.Thread(target=market_loop, daemon=True).start()
except ImportError:
    print("Moteur non détecté.")

# --- HELPER ---
def get_unread_count(user_id):
    conn = get_db_connection()
    try:
        count = conn.execute(
            'SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0',
            (user_id,)
        ).fetchone()[0]
    except:
        count = 0
    conn.close()
    return count

# ==================== AUTH ====================

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
        if user['is_banned']:
            flash(f"Compte banni : {user['ban_reason']}", 'danger')
            return redirect(url_for('home'))
        session['user_id'] = user['id']
        session['username'] = user['username']
        return redirect(url_for('dashboard'))
    flash('Identifiants incorrects', 'danger')
    return redirect(url_for('home'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    if not username or not password:
        flash('Champs requis.', 'danger')
        return redirect(url_for('home'))
    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed))
        conn.commit()
        flash('Compte créé ! Connecte-toi.', 'success')
    except sqlite3.IntegrityError:
        flash('Pseudo déjà utilisé.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ==================== DASHBOARD ====================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    stocks = conn.execute('SELECT * FROM stocks').fetchall()
    conn.close()
    unread_msg = get_unread_count(session['user_id'])
    return render_template('dashboard.html', user=user, stocks=stocks, unread_msg=unread_msg)

# ==================== MARCHÉ ====================

@app.route('/buy', methods=['POST'])
def buy():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Non connecté'}), 401
    data = request.get_json()
    stock_id = data.get('stock_id')
    quantity = int(data.get('quantity', 1))
    conn = get_db_connection()
    stock = conn.execute('SELECT * FROM stocks WHERE id = ?', (stock_id,)).fetchone()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not stock or not user:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Données introuvables'})
    total_cost = stock['price'] * quantity
    if user['cash'] < total_cost:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Fonds insuffisants'})
    # Déduire le cash
    conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (total_cost, session['user_id']))
    # Mettre à jour ou créer le portefeuille
    existing = conn.execute(
        'SELECT * FROM portfolio WHERE user_id = ? AND stock_id = ?',
        (session['user_id'], stock_id)
    ).fetchone()
    if existing:
        conn.execute(
            'UPDATE portfolio SET quantity = quantity + ? WHERE user_id = ? AND stock_id = ?',
            (quantity, session['user_id'], stock_id)
        )
    else:
        conn.execute(
            'INSERT INTO portfolio (user_id, stock_id, quantity) VALUES (?, ?, ?)',
            (session['user_id'], stock_id, quantity)
        )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Acheté {quantity}x {stock["name"]}'})

@app.route('/sell', methods=['POST'])
def sell():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Non connecté'}), 401
    data = request.get_json()
    stock_id = data.get('stock_id')
    quantity = int(data.get('quantity', 1))
    conn = get_db_connection()
    stock = conn.execute('SELECT * FROM stocks WHERE id = ?', (stock_id,)).fetchone()
    holding = conn.execute(
        'SELECT * FROM portfolio WHERE user_id = ? AND stock_id = ?',
        (session['user_id'], stock_id)
    ).fetchone()
    if not holding or holding['quantity'] < quantity:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Pas assez d\'actifs'})
    total_gain = stock['price'] * quantity
    conn.execute('UPDATE users SET cash = cash + ? WHERE id = ?', (total_gain, session['user_id']))
    new_qty = holding['quantity'] - quantity
    if new_qty == 0:
        conn.execute('DELETE FROM portfolio WHERE user_id = ? AND stock_id = ?', (session['user_id'], stock_id))
    else:
        conn.execute(
            'UPDATE portfolio SET quantity = ? WHERE user_id = ? AND stock_id = ?',
            (new_qty, session['user_id'], stock_id)
        )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': f'Vendu {quantity}x {stock["name"]}'})

@app.route('/get_user_stats')
def get_user_stats():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401
    conn = get_db_connection()
    user = conn.execute('SELECT cash FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    stocks = conn.execute('SELECT * FROM stocks').fetchall()
    conn.close()
    return jsonify({
        'cash': user['cash'],
        'stocks': [{'id': s['id'], 'price': s['price'], 'old_price': s['old_price']} for s in stocks]
    })

# ==================== PORTFOLIO ====================

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    holdings = conn.execute('''
        SELECT p.quantity, s.name, s.ticker, s.price, s.old_price,
               (p.quantity * s.price) as total_value
        FROM portfolio p
        JOIN stocks s ON p.stock_id = s.id
        WHERE p.user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    unread_msg = get_unread_count(session['user_id'])
    return render_template('portfolio.html', user=user, holdings=holdings, unread_msg=unread_msg)

# ==================== CHAT ====================

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'status': 'error'}), 401
    data = request.get_json()
    message = data.get('message', '').strip()
    if not message or len(message) > 300:
        return jsonify({'status': 'error', 'message': 'Message invalide'})
    # Filtre mots interdits basique
    forbidden = ['hack', 'cheat', 'password']
    for word in forbidden:
        if word in message.lower():
            return jsonify({'status': 'error', 'message': 'Message refusé'})
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO chat_messages (user_id, username, content) VALUES (?, ?, ?)',
        (session['user_id'], session['username'], message)
    )
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/get_messages')
def get_messages():
    conn = get_db_connection()
    try:
        msgs = conn.execute(
            'SELECT username, content, created_at FROM chat_messages ORDER BY created_at DESC LIMIT 50'
        ).fetchall()
        conn.close()
        messages = [{
            'user': m['username'],
            'text': m['content'],
            'time': m['created_at'][:16] if m['created_at'] else ''
        } for m in reversed(msgs)]
        return jsonify({'messages': messages})
    except:
        conn.close()
        return jsonify({'messages': []})

# ==================== MESSAGERIE PRIVÉE ====================

@app.route('/messages')
def messages():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    try:
        msgs = conn.execute(
            'SELECT * FROM messages WHERE receiver_id = ? ORDER BY created_at DESC',
            (session['user_id'],)
        ).fetchall()
        # Marquer comme lu
        conn.execute('UPDATE messages SET is_read = 1 WHERE receiver_id = ?', (session['user_id'],))
        conn.commit()
    except:
        msgs = []
    conn.close()
    return render_template('messages.html', user=user, messages=msgs)

# ==================== PRÊTS P2P ====================

@app.route('/loans')
def loans():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    try:
        pending_loans = conn.execute('''
            SELECT l.*, u.username, u.stars FROM loans l
            JOIN users u ON l.borrower_id = u.id
            WHERE l.status = 'PENDING' AND l.borrower_id != ?
        ''', (session['user_id'],)).fetchall()
        my_loans = conn.execute('''
            SELECT l.*,
                CASE WHEN l.borrower_id = ? THEN u2.username ELSE u1.username END as partner_name
            FROM loans l
            LEFT JOIN users u1 ON l.borrower_id = u1.id
            LEFT JOIN users u2 ON l.lender_id = u2.id
            WHERE l.borrower_id = ? OR l.lender_id = ?
        ''', (session['user_id'], session['user_id'], session['user_id'])).fetchall()
    except:
        pending_loans = []
        my_loans = []
    conn.close()
    unread_msg = get_unread_count(session['user_id'])
    return render_template('loans.html', user=user, pending_loans=pending_loans, my_loans=my_loans, unread_msg=unread_msg)

@app.route('/request_loan', methods=['POST'])
def request_loan():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    amount = float(request.form.get('amount', 0))
    interest = float(request.form.get('interest', 15))
    if amount <= 0 or amount > 5000:
        flash('Montant invalide (max 5000€)', 'danger')
        return redirect(url_for('loans'))
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO loans (borrower_id, amount, interest_rate, status) VALUES (?, ?, ?, "PENDING")',
        (session['user_id'], amount, interest)
    )
    conn.commit()
    conn.close()
    flash('Demande publiée !', 'success')
    return redirect(url_for('loans'))

@app.route('/fund_loan', methods=['POST'])
def fund_loan():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    loan_id = request.form.get('loan_id')
    conn = get_db_connection()
    loan = conn.execute('SELECT * FROM loans WHERE id = ? AND status = "PENDING"', (loan_id,)).fetchone()
    lender = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not loan or not lender:
        flash('Prêt introuvable.', 'danger')
        conn.close()
        return redirect(url_for('loans'))
    if lender['cash'] < loan['amount']:
        flash('Fonds insuffisants.', 'danger')
        conn.close()
        return redirect(url_for('loans'))
    conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (loan['amount'], session['user_id']))
    conn.execute('UPDATE users SET cash = cash + ? WHERE id = ?', (loan['amount'], loan['borrower_id']))
    conn.execute('UPDATE loans SET lender_id = ?, status = "ACTIVE" WHERE id = ?', (session['user_id'], loan_id))
    conn.commit()
    conn.close()
    flash('Prêt accordé !', 'success')
    return redirect(url_for('loans'))

@app.route('/repay_loan', methods=['POST'])
def repay_loan():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    loan_id = request.form.get('loan_id')
    conn = get_db_connection()
    loan = conn.execute(
        'SELECT * FROM loans WHERE id = ? AND borrower_id = ? AND status = "ACTIVE"',
        (loan_id, session['user_id'])
    ).fetchone()
    if not loan:
        flash('Prêt introuvable.', 'danger')
        conn.close()
        return redirect(url_for('loans'))
    total_repay = loan['amount'] * (1 + loan['interest_rate'] / 100)
    borrower = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if borrower['cash'] < total_repay:
        flash('Fonds insuffisants pour rembourser.', 'danger')
        conn.close()
        return redirect(url_for('loans'))
    conn.execute('UPDATE users SET cash = cash - ? WHERE id = ?', (total_repay, session['user_id']))
    conn.execute('UPDATE users SET cash = cash + ? WHERE id = ?', (total_repay, loan['lender_id']))
    conn.execute('UPDATE loans SET status = "PAID" WHERE id = ?', (loan_id,))
    conn.commit()
    conn.close()
    flash('Prêt remboursé !', 'success')
    return redirect(url_for('loans'))

# ==================== CORPORATION ====================

@app.route('/corporation')
def corporation():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    corp = None
    members = []
    if user['corp_id']:
        corp = conn.execute('SELECT * FROM corporations WHERE id = ?', (user['corp_id'],)).fetchone()
        members = conn.execute('SELECT * FROM users WHERE corp_id = ?', (user['corp_id'],)).fetchall()
    conn.close()
    unread_msg = get_unread_count(session['user_id'])
    return render_template('corporation.html', user=user, corp=corp, members=members, unread_msg=unread_msg)

@app.route('/create_corp', methods=['POST'])
def create_corp():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    corp_name = request.form.get('corp_name', '').strip()
    invite_code = request.form.get('invite_code', '').strip()
    if not corp_name or not invite_code:
        flash('Champs requis.', 'danger')
        return redirect(url_for('corporation'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if user['cash'] < 100000:
        flash('Fonds insuffisants (100 000€ requis).', 'danger')
        conn.close()
        return redirect(url_for('corporation'))
    try:
        cursor = conn.execute(
            'INSERT INTO corporations (name, ceo_id, invite_code, treasury) VALUES (?, ?, ?, 0)',
            (corp_name, session['user_id'], invite_code)
        )
        corp_id = cursor.lastrowid
        conn.execute('UPDATE users SET cash = cash - 100000, corp_id = ? WHERE id = ?', (corp_id, session['user_id']))
        conn.commit()
        flash(f'Corporation {corp_name} fondée !', 'success')
    except sqlite3.IntegrityError:
        flash('Nom ou code déjà utilisé.', 'danger')
    conn.close()
    return redirect(url_for('corporation'))

@app.route('/join_corp', methods=['POST'])
def join_corp():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    invite_code = request.form.get('invite_code', '').strip()
    conn = get_db_connection()
    corp = conn.execute('SELECT * FROM corporations WHERE invite_code = ?', (invite_code,)).fetchone()
    if not corp:
        flash('Code invalide.', 'danger')
        conn.close()
        return redirect(url_for('corporation'))
    conn.execute('UPDATE users SET corp_id = ? WHERE id = ?', (corp['id'], session['user_id']))
    conn.commit()
    conn.close()
    flash(f'Bienvenue dans {corp["name"]} !', 'success')
    return redirect(url_for('corporation'))

# ==================== SCOREBOARD ====================

@app.route('/scoreboard')
def scoreboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    top_traders = conn.execute(
        'SELECT username, cash, stars FROM users WHERE is_banned = 0 ORDER BY cash DESC LIMIT 10'
    ).fetchall()
    conn.close()
    unread_msg = get_unread_count(session['user_id'])
    return render_template('scoreboard.html', user=user, top_traders=top_traders, unread_msg=unread_msg)

# ==================== ADMIN ====================

@app.route('/admin/ban/<int:target_id>', methods=['POST'])
def admin_ban(target_id):
    if 'user_id' not in session:
        return redirect(url_for('home'))
    conn = get_db_connection()
    admin = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin or not admin['is_admin']:
        conn.close()
        flash('Accès refusé.', 'danger')
        return redirect(url_for('dashboard'))
    reason = request.form.get('reason', 'Comportement suspect')
    conn.execute('UPDATE users SET is_banned = 1, ban_reason = ? WHERE id = ?', (reason, target_id))
    conn.commit()
    conn.close()
    flash('Utilisateur banni.', 'success')
    return redirect(url_for('messages'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

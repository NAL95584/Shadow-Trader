"""
SHADOW TRADER — app.py
Serveur Flask principal.
Usage: python app.py
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from functools import wraps

app = Flask(__name__)
app.secret_key = "shadow_trader_secret_key_CHANGE_ME_IN_PROD"

# ─── CONFIGURATION DB ─────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password_here",  # ← Modifier
    "database": "shadow_trader"
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# ─── DÉCORATEUR AUTH ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def get_portfolio_value(conn, user_id: int) -> float:
    """Calcule la valeur totale du portefeuille (actions uniquement)."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT SUM(p.quantity * s.current_price) AS total
        FROM portfolio p
        JOIN stocks s ON p.stock_id = s.id
        WHERE p.user_id = %s AND p.quantity > 0
    """, (user_id,))
    row = cursor.fetchone()
    cursor.close()
    return float(row["total"] or 0)


def get_user(conn, user_id: int) -> dict:
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, cash FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return user


# ─── ROUTES AUTH ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Champs requis.", "error")
            return render_template("login.html")

        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        # Requête paramétrée — anti-injection SQL
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        else:
            flash("Identifiants invalides.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password or len(username) < 3 or len(password) < 6:
            flash("Pseudo (3+ chars) et mot de passe (6+ chars) requis.", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash)
            )
            conn.commit()
            flash("Compte créé ! Connecte-toi.", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("Ce pseudo est déjà pris.", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ─── DASHBOARD ────────────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    user = get_user(conn, session["user_id"])

    # Liste des actions avec variation
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM stocks ORDER BY name")
    stocks = cursor.fetchall()
    cursor.close()

    # Portefeuille de l'utilisateur
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.id, s.name, s.ticker, s.current_price, s.old_price, p.quantity,
               (p.quantity * s.current_price) AS position_value
        FROM portfolio p
        JOIN stocks s ON p.stock_id = s.id
        WHERE p.user_id = %s AND p.quantity > 0
    """, (session["user_id"],))
    portfolio = cursor.fetchall()
    cursor.close()

    # Derniers logs
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT 10")
    logs = cursor.fetchall()
    cursor.close()

    portfolio_value = get_portfolio_value(conn, session["user_id"])
    total_value = float(user["cash"]) + portfolio_value
    conn.close()

    return render_template("dashboard.html",
        user=user,
        stocks=stocks,
        portfolio=portfolio,
        logs=logs,
        portfolio_value=portfolio_value,
        total_value=total_value
    )


# ─── TRADING ──────────────────────────────────────────────────────────────────
@app.route("/buy", methods=["POST"])
@login_required
def buy():
    stock_id = request.form.get("stock_id")
    quantity_raw = request.form.get("quantity", "0")

    # Sanitisation : quantité doit être un entier positif
    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        flash("Quantité invalide (doit être un entier positif).", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Récupérer le prix actuel (en base, pas depuis le client)
    cursor.execute("SELECT id, name, ticker, current_price FROM stocks WHERE id = %s", (stock_id,))
    stock = cursor.fetchone()
    cursor.close()

    if not stock:
        flash("Action introuvable.", "error")
        conn.close()
        return redirect(url_for("dashboard"))

    total_cost = float(stock["current_price"]) * quantity
    user = get_user(conn, session["user_id"])

    # ─ Anti-solde négatif ─
    if float(user["cash"]) < total_cost:
        flash(f"Fonds insuffisants. Il te faut {total_cost:.2f}$ (tu as {float(user['cash']):.2f}$).", "error")
        conn.close()
        return redirect(url_for("dashboard"))

    cursor = conn.cursor()
    # Débiter le cash
    cursor.execute(
        "UPDATE users SET cash = cash - %s WHERE id = %s",
        (total_cost, session["user_id"])
    )
    # Ajouter les actions au portefeuille (INSERT ON DUPLICATE KEY UPDATE)
    cursor.execute("""
        INSERT INTO portfolio (user_id, stock_id, quantity)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE quantity = quantity + %s
    """, (session["user_id"], stock["id"], quantity, quantity))

    conn.commit()
    cursor.close()
    conn.close()

    flash(f"✅ Achat de {quantity} × {stock['ticker']} pour {total_cost:.2f}$", "success")
    return redirect(url_for("dashboard"))


@app.route("/sell", methods=["POST"])
@login_required
def sell():
    stock_id = request.form.get("stock_id")
    quantity_raw = request.form.get("quantity", "0")

    try:
        quantity = int(quantity_raw)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        flash("Quantité invalide.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    # Vérifier la possession
    cursor.execute(
        "SELECT quantity FROM portfolio WHERE user_id = %s AND stock_id = %s",
        (session["user_id"], stock_id)
    )
    holding = cursor.fetchone()
    cursor.close()

    if not holding or holding["quantity"] < quantity:
        flash("Tu ne possèdes pas assez d'actions.", "error")
        conn.close()
        return redirect(url_for("dashboard"))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, ticker, current_price FROM stocks WHERE id = %s", (stock_id,))
    stock = cursor.fetchone()
    cursor.close()

    total_gain = float(stock["current_price"]) * quantity

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET cash = cash + %s WHERE id = %s",
        (total_gain, session["user_id"])
    )
    cursor.execute(
        "UPDATE portfolio SET quantity = quantity - %s WHERE user_id = %s AND stock_id = %s",
        (quantity, session["user_id"], stock_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash(f"💰 Vente de {quantity} × {stock['ticker']} pour {total_gain:.2f}$", "success")
    return redirect(url_for("dashboard"))


# ─── SCOREBOARD ───────────────────────────────────────────────────────────────
@app.route("/scoreboard")
@login_required
def scoreboard():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.username, u.cash,
               COALESCE(SUM(p.quantity * s.current_price), 0) AS stocks_value,
               u.cash + COALESCE(SUM(p.quantity * s.current_price), 0) AS total_value
        FROM users u
        LEFT JOIN portfolio p ON u.id = p.user_id
        LEFT JOIN stocks s ON p.stock_id = s.id
        GROUP BY u.id, u.username, u.cash
        ORDER BY total_value DESC
        LIMIT 20
    """)
    traders = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("scoreboard.html", traders=traders)


# ─── API PRIX (pour les mises à jour live) ────────────────────────────────────
@app.route("/api/prices")
@login_required
def api_prices():
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, ticker, name, current_price, old_price FROM stocks")
    stocks = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT message, created_at FROM logs ORDER BY created_at DESC LIMIT 5")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()

    return jsonify({
        "stocks": [
            {
                "id": s["id"],
                "ticker": s["ticker"],
                "name": s["name"],
                "price": float(s["current_price"]),
                "old_price": float(s["old_price"]),
                "change_pct": round((float(s["current_price"]) - float(s["old_price"])) / float(s["old_price"]) * 100, 2)
            }
            for s in stocks
        ],
        "logs": [{"message": l["message"], "time": str(l["created_at"])} for l in logs]
    })


# ─── LANCEMENT ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)

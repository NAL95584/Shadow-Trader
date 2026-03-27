"""
SHADOW TRADER — engine.py
Moteur de prix indépendant. Lance ce script séparément du serveur Flask.
Usage: python engine.py
"""

import time
import random
import math
import mysql.connector
from datetime import datetime

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password_here",  # ← Modifier
    "database": "shadow_trader"
}

TICK_INTERVAL = 5        # Secondes entre chaque tick de bruit
INFLATION_INTERVAL = 600 # 10 minutes
NEWS_PROBABILITY = 0.01  # 1% de chance par tick


# ─── CONNEXION ────────────────────────────────────────────────────────────────
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ─── UTILITAIRES ──────────────────────────────────────────────────────────────
def log_event(conn, message: str):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (message) VALUES (%s)", (message,))
    conn.commit()
    cursor.close()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] EVENT → {message}")


def clamp_price(price: float, minimum: float = 0.01) -> float:
    """Empêche les prix de tomber à zéro ou en négatif."""
    return max(price, minimum)


# ─── MOUVEMENTS DE PRIX ───────────────────────────────────────────────────────
def apply_market_noise(conn):
    """Bruit du marché : fluctuation aléatoire selon la volatilité de chaque action."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, ticker, current_price, volatility FROM stocks")
    stocks = cursor.fetchall()
    cursor.close()

    cursor = conn.cursor()
    for stock in stocks:
        price = float(stock["current_price"])
        vol = float(stock["volatility"])

        # Mouvement gaussien centré sur 0, amplitude = volatilité
        change = random.gauss(0, vol)
        new_price = clamp_price(price * (1 + change))

        cursor.execute(
            "UPDATE stocks SET old_price = current_price, current_price = %s WHERE id = %s",
            (round(new_price, 2), stock["id"])
        )
    conn.commit()
    cursor.close()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] TICK — {len(stocks)} actions mises à jour")


def apply_inflation(conn):
    """Inflation globale : +1% sur tous les prix."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE stocks SET old_price = current_price, current_price = ROUND(current_price * 1.01, 2)"
    )
    conn.commit()
    cursor.close()
    log_event(conn, "📈 Inflation globale appliquée (+1%)")


def apply_news_event(conn):
    """Événement News : un krach ou un boom sur une action aléatoire."""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, ticker, current_price FROM stocks ORDER BY RAND() LIMIT 1")
    stock = cursor.fetchone()
    cursor.close()

    if not stock:
        return

    is_boom = random.choice([True, False])
    multiplier = 1.50 if is_boom else 0.50
    new_price = clamp_price(float(stock["current_price"]) * multiplier)

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE stocks SET old_price = current_price, current_price = %s WHERE id = %s",
        (round(new_price, 2), stock["id"])
    )
    conn.commit()
    cursor.close()

    emoji = "🚀" if is_boom else "💥"
    direction = "BOOM +50%" if is_boom else "KRACH -50%"
    log_event(conn, f"{emoji} NEWS : {stock['name']} ({stock['ticker']}) — {direction} → {new_price:.2f}$")


# ─── BOUCLE PRINCIPALE ────────────────────────────────────────────────────────
def run():
    print("=" * 50)
    print("  SHADOW TRADER — Moteur de Prix v1.0")
    print("=" * 50)
    print(f"  Tick toutes les {TICK_INTERVAL}s | Inflation toutes les {INFLATION_INTERVAL}s")
    print(f"  Probabilité News : {NEWS_PROBABILITY * 100}% par tick")
    print("=" * 50)

    tick_count = 0
    ticks_per_inflation = INFLATION_INTERVAL // TICK_INTERVAL

    while True:
        try:
            conn = get_connection()

            # 1. Bruit du marché (chaque tick)
            apply_market_noise(conn)

            # 2. Inflation (toutes les N ticks)
            if tick_count > 0 and tick_count % ticks_per_inflation == 0:
                apply_inflation(conn)

            # 3. Événement News (probabilité aléatoire)
            if random.random() < NEWS_PROBABILITY:
                apply_news_event(conn)

            conn.close()
            tick_count += 1

        except mysql.connector.Error as e:
            print(f"[ERREUR DB] {e} — Nouvelle tentative dans {TICK_INTERVAL}s...")

        time.sleep(TICK_INTERVAL)


if __name__ == "__main__":
    run()

import sqlite3
import random

def update_market_prices():
    conn = sqlite3.connect('shadow_trader.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Récupérer toutes les actions
    stocks = cursor.execute('SELECT * FROM stocks').fetchall()

    for stock in stocks:
        old_price = stock['price']
        
        # Simulation d'une variation naturelle (Bruit de marché)
        # On ajoute entre -2% et +2% au hasard
        change_percent = random.uniform(-0.02, 0.02)
        
        # --- LOGIQUE D'OFFRE ET DEMANDE (AVANCÉ) ---
        # On regarde combien de transactions d'achat ont eu lieu récemment pour cette action
        # (Plus il y a d'achats, plus le multiplicateur monte)
        # Pour l'instant, on simule une petite dérive positive
        
        new_price = old_price * (1 + change_percent)
        
        # Sécurité : Le prix ne peut pas descendre en dessous de 0.01€
        if new_price < 0.01:
            new_price = 0.01

        # Mettre à jour la base de données
        cursor.execute('''
            UPDATE stocks 
            SET old_price = ?, price = ? 
            WHERE id = ?
        ''', (old_price, round(new_price, 2), stock['id']))

    conn.commit()
    conn.close()
    print("Marché mis à jour avec succès.")

if __name__ == "__main__":
    update_market_prices()

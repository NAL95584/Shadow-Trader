import sqlite3
import openai # Pour l'analyse de sentiment/fraude

def run_security_check():
    conn = sqlite3.connect('shadow_trader.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. DÉTECTION DE FRAUDE FINANCIÈRE
    # On cherche les joueurs qui ont gagné plus de 50 000€ en moins de 5 minutes
    suspicious_users = cursor.execute('''
        SELECT username, cash FROM users 
        WHERE cash > 100000 AND is_admin = 0
    ''').fetchall()

    for user in suspicious_users:
        # Logique de signalement : On envoie un message à l'Admin
        report_body = f"ALERTE : L'utilisateur {user['username']} possède un solde élevé ({user['cash']}€). Analyse de traçabilité requise."
        
        # On vérifie si un signalement existe déjà pour éviter les doublons
        cursor.execute('''
            INSERT INTO messages (receiver_id, sender_name, subject, content, type)
            SELECT id, 'SYSTEM_AI', 'ALERTE SÉCURITÉ', ?, 'SECURITY'
            FROM users WHERE is_admin = 1
        ''', (report_body,))

    # 2. ANALYSE DU CHAT (Simulation NLP)
    # Ici, on pourrait envoyer les derniers messages à OpenAI pour vérifier la toxicité
    # Pour le projet, on va scanner des mots-clés interdits
    forbidden_words = ['hack', 'cheat', 'admin', 'password', 'ballec']
    # (Tu peux en ajouter d'autres)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run_security_check()

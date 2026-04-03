# 🌑 SHADOW TRADER — Guide de démarrage

## Structure des fichiers

```
shadow_trader/
├── app.py                  ← Serveur Flask (toutes les routes)
├── engine.py               ← Moteur de prix boursiers
├── security_audit.py       ← Audit de sécurité
├── init_db.sql             ← Initialisation BDD
├── requirements.txt        ← Dépendances Python
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
└── templates/
    ├── login.html
    ├── dashboard.html
    ├── corporation.html
    ├── loans.html
    ├── messages.html
    ├── portfolio.html      ← NOUVEAU
    └── scoreboard.html     ← NOUVEAU
```

## Installation

```bash
# 1. Installer les dépendances
pip install flask flask-bcrypt

# 2. Créer la base de données
python3 -c "
import sqlite3
with open('init_db.sql') as f:
    sqlite3.connect('shadow_trader.db').executescript(f.read())
print('BDD créée !')
"

# 3. Créer un compte admin (exemple)
python3 -c "
from flask_bcrypt import Bcrypt
import sqlite3
b = Bcrypt()
pw = b.generate_password_hash('admin123').decode()
conn = sqlite3.connect('shadow_trader.db')
conn.execute('INSERT OR IGNORE INTO users (username, password, cash, is_admin) VALUES (?, ?, ?, ?)', ('admin', pw, 999999, 1))
conn.commit()
print('Admin créé : admin / admin123')
"

# 4. Lancer le serveur
python3 app.py
```

## Accès
- URL : http://localhost:5000
- Ou sur le réseau local : http://[TON_IP]:5000

## Ce qui a été corrigé/ajouté

### app.py
- ✅ Route `/register` (inscription)
- ✅ Routes `/buy` et `/sell` (trading)
- ✅ Route `/portfolio` avec calcul de valeur
- ✅ Routes `/loans`, `/request_loan`, `/fund_loan`, `/repay_loan`
- ✅ Routes `/corporation`, `/create_corp`, `/join_corp`
- ✅ Routes `/messages` et `/send_message`
- ✅ Route `/scoreboard`
- ✅ Route `/admin/ban/<id>`
- ✅ Gestion des comptes bannis à la connexion

### init_db.sql
- ✅ Table `portfolio` (holdings des traders)
- ✅ Table `corporations` (entreprises)
- ✅ Table `loans` (prêts P2P)
- ✅ Table `chat_messages` (chat global)
- ✅ Table `messages` (messagerie privée)
- ✅ 6 actifs de base (BTC, ETH, GOLD, OIL, SHAD, TECH)
- ✅ Colonne `category` dans `stocks`

### style.css
- ✅ Styles portfolio, scoreboard, toast
- ✅ Styles améliorés pour toutes les pages

### main.js
- ✅ Touche Entrée pour envoyer un message
- ✅ `sellStock()` fonctionnel
- ✅ Mise à jour des prix en temps réel
- ✅ Échappement HTML pour la sécurité XSS

### Nouveaux templates
- ✅ `portfolio.html` — portefeuille du trader
- ✅ `scoreboard.html` — top 10 des traders
- ✅ `corporation.html` — version complète (le fichier était tronqué)

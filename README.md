# ◈ SHADOW TRADER — Guide de démarrage

## Prérequis
- Python 3.10+
- MySQL 8.0+

## Installation

```bash
# 1. Installer les dépendances Python
pip install -r requirements.txt

# 2. Créer la base de données
#    Ouvrir phpMyAdmin ou MySQL Workbench
#    Exécuter le contenu de init_db.sql

# 3. Configurer le mot de passe MySQL
#    Modifier DB_CONFIG dans app.py et engine.py :
#    "password": "ton_mot_de_passe"
```

## Lancement

```bash
# Terminal 1 — Moteur de prix (indépendant)
python engine.py

# Terminal 2 — Serveur web
python app.py
```

Accéder à : http://localhost:5000

## Structure des fichiers

```
shadow_trader/
├── app.py          ← Serveur Flask (routes, auth, trading)
├── engine.py       ← Moteur de prix (boucle infinie)
├── requirements.txt
├── init_db.sql     ← Script SQL d'initialisation
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   └── scoreboard.html
└── static/
    ├── css/style.css
    └── js/main.js
```

## Sécurité implémentée
- ✅ Hachage des mots de passe (Werkzeug/bcrypt)
- ✅ Requêtes paramétrées (anti-injection SQL)
- ✅ Anti-solde négatif (vérification côté serveur)
- ✅ Sanitisation des quantités (entiers positifs uniquement)
- ✅ Prix vérifiés côté serveur (pas côté client)
- ✅ Session Flask sécurisée

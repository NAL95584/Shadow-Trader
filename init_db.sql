-- Suppression pour reset propre
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS corps;
DROP TABLE IF EXISTS stocks;
DROP TABLE IF EXISTS portfolio;
DROP TABLE IF EXISTS loans;
DROP TABLE IF EXISTS messages;

-- 1. Table des Entreprises
CREATE TABLE corps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    ceo_id INTEGER,
    treasury REAL DEFAULT 0.0,
    invite_code TEXT, -- Code pour rejoindre en privé
    is_ipo BOOLEAN DEFAULT 0, -- Cotation en bourse dès 1M
    tax_rate REAL DEFAULT 0.15 -- La part du patron (15%)
);

-- 2. Table des Utilisateurs
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    cash REAL DEFAULT 10000.0,
    stars REAL DEFAULT 5.0, -- Note style Vinted
    is_banned BOOLEAN DEFAULT 0,
    ban_reason TEXT,
    corp_id INTEGER,
    is_admin BOOLEAN DEFAULT 0,
    FOREIGN KEY (corp_id) REFERENCES corps(id)
);

-- 3. Table des Actions
CREATE TABLE stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- Auto, Crypto, Tech, Banque, Energie
    price REAL NOT NULL,
    old_price REAL NOT NULL
);

-- 4. Table des Prêts (Loans)
CREATE TABLE loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lender_id INTEGER,
    borrower_id INTEGER,
    amount REAL,
    interest_rate REAL, -- 10% à 50%
    due_date DATETIME,
    status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'PAID', 'LATE'
    FOREIGN KEY (lender_id) REFERENCES users(id),
    FOREIGN KEY (borrower_id) REFERENCES users(id)
);

-- 5. Table des Messages (Mailbox)
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER,
    sender_name TEXT,
    subject TEXT,
    content TEXT,
    type TEXT, -- 'INVOICE', 'CONTRACT', 'SECURITY', 'NEWS'
    is_read BOOLEAN DEFAULT 0,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);

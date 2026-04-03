CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    cash REAL DEFAULT 10000.0,
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    ban_reason TEXT,
    stars REAL DEFAULT 5.0,
    corp_id INTEGER
);

CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    old_price REAL
);

-- Insertion de données de test
INSERT OR IGNORE INTO stocks (ticker, name, price) VALUES ('BTC', 'Bitcoin', 65000.0);
INSERT OR IGNORE INTO stocks (ticker, name, price) VALUES ('GOLD', 'Or Pur', 2100.0);
INSERT OR IGNORE INTO stocks (ticker, name, price) VALUES ('SHAD', 'Shadow Corp', 150.0);

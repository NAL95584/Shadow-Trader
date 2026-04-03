-- ===========================
-- SHADOW TRADER - BASE DE DONNÉES
-- ===========================

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    cash REAL DEFAULT 10000.0,
    is_admin INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    ban_reason TEXT,
    stars REAL DEFAULT 5.0,
    corp_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT DEFAULT 'CRYPTO',
    price REAL NOT NULL,
    old_price REAL
);

CREATE TABLE IF NOT EXISTS portfolio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (stock_id) REFERENCES stocks(id),
    UNIQUE(user_id, stock_id)
);

CREATE TABLE IF NOT EXISTS corporations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    ceo_id INTEGER NOT NULL,
    invite_code TEXT UNIQUE NOT NULL,
    treasury REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    borrower_id INTEGER NOT NULL,
    lender_id INTEGER,
    amount REAL NOT NULL,
    interest_rate REAL NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (borrower_id) REFERENCES users(id),
    FOREIGN KEY (lender_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receiver_id INTEGER NOT NULL,
    sender_name TEXT NOT NULL,
    subject TEXT,
    content TEXT NOT NULL,
    type TEXT DEFAULT 'INFO',
    is_read INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);

-- === DONNÉES DE DÉPART ===

INSERT OR IGNORE INTO stocks (ticker, name, category, price, old_price) VALUES
    ('BTC',  'Bitcoin',       'CRYPTO',    65000.0,  64000.0),
    ('ETH',  'Ethereum',      'CRYPTO',     3500.0,   3400.0),
    ('GOLD', 'Or Pur',        'MATIÈRES',   2100.0,   2080.0),
    ('OIL',  'Pétrole Brut',  'MATIÈRES',     85.0,     83.0),
    ('SHAD', 'Shadow Corp',   'ACTION',      150.0,    145.0),
    ('TECH', 'TechIndex',     'ACTION',      420.0,    415.0);

-- ═══════════════════════════════════════════════════════
--  SHADOW TRADER — init_db.sql
--  Copier-coller dans phpMyAdmin ou MySQL Workbench
-- ═══════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS shadow_trader CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE shadow_trader;

-- ─── TABLES ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    cash          DECIMAL(15, 2) DEFAULT 10000.00,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stocks (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(50) NOT NULL,
    ticker        VARCHAR(5) UNIQUE NOT NULL,
    current_price DECIMAL(15, 2) NOT NULL,
    old_price     DECIMAL(15, 2) NOT NULL,
    volatility    FLOAT DEFAULT 0.02,
    sector        VARCHAR(30) DEFAULT 'Tech'
);

CREATE TABLE IF NOT EXISTS portfolio (
    user_id   INT,
    stock_id  INT,
    quantity  INT DEFAULT 0,
    PRIMARY KEY (user_id, stock_id),
    FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE,
    FOREIGN KEY (stock_id) REFERENCES stocks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS logs (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    message    TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── DONNÉES DE DÉPART (5 ACTIONS) ───────────────────────

INSERT INTO stocks (name, ticker, current_price, old_price, volatility, sector) VALUES
('TeslaX Corp',      'TSLX',  250.00,  250.00, 0.035, 'AutoTech'),
('CyberSoda Inc',    'CYBR',   80.00,   80.00, 0.025, 'Boissons'),
('MoonMining Ltd',   'MOON',  420.00,  420.00, 0.050, 'Ressources'),
('NeuralDream AI',   'NDAI',  155.00,  155.00, 0.030, 'Intelligence Artificielle'),
('OceanPower Corp',  'OCNP',   45.00,   45.00, 0.020, 'Énergie');

-- ─── LOG D'INITIALISATION ────────────────────────────────

INSERT INTO logs (message) VALUES
('🚀 Shadow Trader initialisé — 5 actions disponibles'),
('📊 Marché ouvert. Bonne chance, trader.');

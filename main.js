// ===========================
// SHADOW TRADER - main.js
// ===========================

// --- CHAT ---
function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    fetch('/send_message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            input.value = '';
            updateChat();
        } else {
            showToast(data.message || 'Erreur', 'danger');
        }
    })
    .catch(() => showToast('Erreur réseau', 'danger'));
}

document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') sendMessage();
        });
    }
    updateChat();
    updateUI();
});

function updateChat() {
    fetch('/get_messages')
    .then(r => r.json())
    .then(data => {
        const box = document.getElementById('chat-box');
        if (!box) return;
        box.innerHTML = '';
        data.messages.forEach(msg => {
            const div = document.createElement('div');
            div.className = 'chat-msg';
            const time = msg.time ? msg.time.slice(11, 16) : '';
            div.innerHTML = `<span class="muted">[${time}]</span> <span class="neon-green">${escapeHtml(msg.user)}</span>: ${escapeHtml(msg.text)}`;
            box.appendChild(div);
        });
        box.scrollTop = box.scrollHeight;
    })
    .catch(() => {});
}

// --- MARCHÉ ---
function buyStock(stockId) {
    fetch('/buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stock_id: stockId, quantity: 1 })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('✅ ' + data.message, 'success');
            updateUI();
        } else {
            showToast('❌ ' + data.message, 'danger');
        }
    })
    .catch(() => showToast('Erreur réseau', 'danger'));
}

function sellStock(stockId) {
    fetch('/sell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stock_id: stockId, quantity: 1 })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('✅ ' + data.message, 'success');
            updateUI();
        } else {
            showToast('❌ ' + data.message, 'danger');
        }
    })
    .catch(() => showToast('Erreur réseau', 'danger'));
}

// --- MISE À JOUR DES PRIX ET DU CASH ---
function updateUI() {
    fetch('/get_user_stats')
    .then(r => r.json())
    .then(data => {
        // Cash
        const cashEl = document.querySelector('.value.neon-green');
        if (cashEl) cashEl.textContent = data.cash.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';

        // Prix des actifs
        if (data.stocks) {
            data.stocks.forEach(s => {
                const cards = document.querySelectorAll('.stock-card');
                cards.forEach(card => {
                    const btn = card.querySelector(`[onclick="buyStock(${s.id})"]`);
                    if (!btn) return;
                    const priceEl = card.querySelector('.current-price');
                    const changeEl = card.querySelector('.price-change');
                    if (priceEl) priceEl.textContent = s.price.toLocaleString('fr-FR', { minimumFractionDigits: 2 }) + ' €';
                    if (changeEl && s.old_price) {
                        const pct = ((s.price - s.old_price) / s.old_price * 100).toFixed(2);
                        changeEl.textContent = (pct >= 0 ? '+' : '') + pct + '%';
                        changeEl.className = 'price-change ' + (pct >= 0 ? 'up' : 'down');
                    }
                });
            });
        }
    })
    .catch(() => {});
}

// --- TOAST ---
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} toast-notification`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3200);
}

// --- SÉCURITÉ : échapper le HTML ---
function escapeHtml(str) {
    const d = document.createElement('div');
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
}

// --- RAFRAÎCHISSEMENT AUTOMATIQUE ---
setInterval(updateChat, 4000);
setInterval(updateUI, 8000);

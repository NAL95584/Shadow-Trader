// --- GESTION DU CHAT ---
function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value;
    if (message.trim() === "") return;

    fetch('/send_message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            input.value = '';
            updateChat(); // Rafraîchir le chat immédiatement
        }
    });
}

function updateChat() {
    fetch('/get_messages')
    .then(response => response.json())
    .then(data => {
        const chatBox = document.getElementById('chat-box');
        chatBox.innerHTML = ''; // On vide pour reconstruire
        data.messages.forEach(msg => {
            const div = document.createElement('div');
            div.className = 'chat-msg';
            div.innerHTML = `<span class="neon-green">[${msg.time}]</span> <strong>${msg.user}</strong>: ${msg.text}`;
            chatBox.appendChild(div);
        });
        chatBox.scrollTop = chatBox.scrollHeight; // Scroll automatique vers le bas
    });
}

// --- GESTION DU MARCHÉ (ACHAT/VENTE) ---
function buyStock(stockId) {
    fetch('/buy', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ stock_id: stockId, quantity: 1 })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast("Achat réussi !", "success");
            updateUI(); // Met à jour le cash affiché
        } else {
            showToast(data.message, "danger");
        }
    });
}

// --- MISE À JOUR DYNAMIQUE ---
function updateUI() {
    // Cette fonction ira chercher ton nouveau solde et les nouveaux prix
    fetch('/get_user_stats')
    .then(response => response.json())
    .then(data => {
        document.querySelector('.value.neon-green').innerText = data.cash.toFixed(2) + " €";
    });
}

// Notifications de type "Toast" (petites alertes en bas de l'écran)
function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} toast-notification`;
    toast.innerText = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// On rafraîchit le chat et les prix toutes les 3 secondes
setInterval(updateChat, 3000);
setInterval(updateUI, 5000);

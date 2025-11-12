
document.addEventListener('DOMContentLoaded', function() {
    
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const messagesArea = document.getElementById('chat-messages');

    // Função para adicionar mensagem na tela (movida para o topo)
    function addMessage(text, role) { // role = 'user', 'bot', ou 'bot-loading'
        const bubble = document.createElement('div');
        bubble.classList.add('chat-bubble', role);
        bubble.innerHTML = text.replace(/\n/g, '<br>'); // Converte quebras de linha
        
        messagesArea.appendChild(bubble);
        messagesArea.scrollTop = messagesArea.scrollHeight;
        return bubble;
    }

    // --- LÓGICA DE ID DO CLIENTE MODIFICADA ---
    const urlParams = new URLSearchParams(window.location.search);
    const ID_CLIENTE_LOGADO = urlParams.get('cliente');

    if (!ID_CLIENTE_LOGADO) {
        addMessage("<b>ERRO:</b> ID do cliente não encontrado na URL. <br>Acesse este chat a partir do seu dashboard de cliente.", 'bot');
        chatForm.style.display = 'none'; // Esconde a barra de digitação
        return; // Para a execução
    }
    // --- FIM DA MODIFICAÇÃO ---


    // Enviar mensagem
    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const messageText = chatInput.value.trim();
        if (messageText === '') return;

        addMessage(messageText, 'user');
        chatInput.value = ''; 
        const loadingBubble = addMessage("digitando...", 'bot-loading');

        try {
            // A chamada de API agora usa o ID_CLIENTE_LOGADO dinâmico
            const response = await fetch(`/api/chat/${ID_CLIENTE_LOGADO}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ texto: messageText }),
            });

            messagesArea.removeChild(loadingBubble); // Remove o "digitando..."

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Erro de conexão');
            }
            
            const data = await response.json();
            addMessage(data.resposta, 'bot');

        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            if(loadingBubble) messagesArea.removeChild(loadingBubble);
            addMessage('Desculpe, estou com problemas de conexão. 😥', 'bot');
        }
    });

    // Mensagem de boas-vindas (agora dinâmica)
    setTimeout(() => {
        addMessage(`Olá! 👋 Esta é uma simulação. Você está conectado como o cliente ID: <b>${ID_CLIENTE_LOGADO}</b>. Pode me enviar uma mensagem!`, 'bot');
    }, 500);
});

document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. Verificação de Login ---
    const ID_CLIENTE_LOGADO = localStorage.getItem('id_cliente'); 
    const NOME_CLIENTE = localStorage.getItem('nome_cliente') || 'Cliente';
    const NOME_NUTRI = localStorage.getItem('nome_nutri') || 'Nutricionista';

    if (!ID_CLIENTE_LOGADO) {
        alert("Sessão não encontrada. Por favor, faça o login.");
        window.location.href = 'cliente_login.html';
        return;
    }

    // --- 2. Popular Dados Globais (Nomes) ---
    document.querySelector('.sidebar-profile span').textContent = `Bem-vindo(a), ${NOME_CLIENTE}!`;
    document.querySelector('#home .nutri-info h2').textContent = `Dr(a). ${NOME_NUTRI}`;
    // Popula a tela de "Informações" também
    const infoNutriH3 = document.querySelector('#info .nutri-profile h3');
    if (infoNutriH3) {
        infoNutriH3.textContent = `Dr(a). ${NOME_NUTRI}`;
    }
    
    // --- LÓGICA DO BOTÃO WHATSAPP ADICIONADA AQUI ---
    const whatsappLink = document.getElementById('whatsapp-sim-link');
    if (whatsappLink) {
        // Define o link para a simulação, passando o ID do cliente na URL
        whatsappLink.href = `../Whatsapp_Sim/chat.html?cliente=${ID_CLIENTE_LOGADO}`;
        // Faz abrir em uma nova aba
        whatsappLink.target = "_blank";
        
        // Remove o comportamento de "aba" do dashboard
        whatsappLink.addEventListener('click', function(event) {
            event.stopPropagation(); // Impede que o listener de navegação de abas seja acionado
        });
    }
    // --- FIM DA ADIÇÃO ---


    // --- 3. Lógica de Navegação (Abas) ---
    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    const contentSections = document.querySelectorAll('.content-section');

    navItems.forEach(item => {
        // Ignora o link do whatsapp da lógica de abas
        if (item.id === 'whatsapp-sim-link') {
            return;
        }

        item.addEventListener('click', function(event) {
            event.preventDefault();
            const targetId = this.getAttribute('data-target');
            
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            
            contentSections.forEach(section => section.classList.remove('active'));
            const targetView = document.getElementById(targetId);
            
            if (targetView) {
                targetView.classList.add('active');
                
                // Carregar dados sob demanda ao clicar na aba
                if (targetId === 'perfil') {
                    carregarDadosPerfil();
                } else if (targetId === 'plano') {
                    carregarPlanoNutricional();
                } else if (targetId === 'info') {
                    carregarInfoNutri(); // Carrega dados da tela de info
                }
            }
        });
    });

    // --- 4. Lógica do Chat ---
    const chatForm = document.querySelector('.chat-input-form');
    const chatInput = document.querySelector('.chat-input-field');
    const chatMessages = document.querySelector('.chat-messages');
    
    // Função para adicionar mensagem na tela
    function adicionarMensagemAoChat(texto, tipo) { // tipo = 'user' or 'bot'
        const bubble = document.createElement('div');
        bubble.classList.add('chat-bubble');
        bubble.classList.add(tipo === 'user' ? 'user-message' : 'bot-message');
        bubble.innerHTML = texto.replace(/\n/g, '<br>'); // Converte quebras de linha
        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight; // Rola para a última mensagem
    }

    // Enviar mensagem
    chatForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const textoMensagem = chatInput.value.trim();
        if (textoMensagem === '') return;

        adicionarMensagemAoChat(textoMensagem, 'user');
        chatInput.value = ''; 

        try {
            const response = await fetch(`/api/chat/${ID_CLIENTE_LOGADO}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ texto: textoMensagem }),
            });

            if (!response.ok) throw new Error(`Erro na API: ${response.statusText}`);
            const data = await response.json();
            adicionarMensagemAoChat(data.resposta, 'bot');

        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            adicionarMensagemAoChat('Desculpe, estou com problemas de conexão. Tente novamente.', 'bot');
        }
    });

    // --- 5. Carregamento de Dados das Abas ---

    // Carregar histórico do chat ao abrir a página
    async function carregarHistoricoChat() {
        try {
            const response = await fetch(`/api/chat/${ID_CLIENTE_LOGADO}/historico`);
            if (!response.ok) throw new Error('Falha ao carregar histórico');
            
            const historico = await response.json();
            chatMessages.innerHTML = ''; // Limpa mensagens de exemplo
            historico.forEach(msg => {
                adicionarMensagemAoChat(msg.texto, msg.role);
            });
            // Saudação inicial se o histórico estiver vazio
            if(historico.length === 0) {
                 adicionarMensagemAoChat(`Olá, ${NOME_CLIENTE}! Estou pronto para ajudar com seu plano. O que você gostaria de saber?`, 'bot');
            }
        } catch (error) {
            console.error('Erro ao carregar histórico:', error);
            adicionarMensagemAoChat('Bem-vindo! Não consegui carregar seu histórico.', 'bot');
        }
    }

    // Carregar dados do perfil (chamado ao clicar na aba)
    async function carregarDadosPerfil() {
        const perfilContainer = document.querySelector('#perfil .card-container');
        perfilContainer.innerHTML = "<p>Carregando perfil...</p>";
        
        try {
            const response = await fetch(`/api/clientes/${ID_CLIENTE_LOGADO}/perfil`);
            if (!response.ok) throw new Error('Falha ao carregar perfil');
            
            const perfil = await response.json();
            
            // Popula os cards dinamicamente
            perfilContainer.innerHTML = `
                <div class="info-card">
                    <h3>Informações Pessoais</h3>
                    <p><strong>Nome:</strong> ${perfil.nome || 'Não informado'}</p>
                    <p><strong>Email:</strong> ${perfil.email || 'Não informado'}</p>
                    <p><strong>Idade:</strong> ${perfil.idade || 'Não informada'}</p>
                    <p><strong>Sexo:</strong> ${perfil.sexo || 'Não informado'}</p>
                </div>
                <div class="info-card">
                    <h3>Metas e Dados do Plano</h3>
                    <p><strong>Objetivo:</strong> ${perfil.meta || 'Não definido'}</p>
                    <p><strong>Peso Atual:</strong> ${perfil.peso_kg || 'Não informado'} kg</p>
                    <p><strong>Altura:</strong> ${perfil.altura_cm || 'Não informada'} cm</p>
                    <p><strong>IMC:</strong> ${perfil.imc ? perfil.imc.toFixed(2) : 'N/A'} (${perfil.imc_class})</p>
                </div>
            `;
        } catch (error) {
            console.error('Erro ao carregar perfil:', error);
            perfilContainer.innerHTML = "<p>Erro ao carregar seu perfil.</p>";
        }
    }

    // Carregar plano (chamado ao clicar na aba)
    async function carregarPlanoNutricional() {
        const planoContainer = document.querySelector('#plano .plano-container');
        planoContainer.innerHTML = "<p>Carregando plano...</p>";
        
        try {
            const response = await fetch(`/api/planos/${ID_CLIENTE_LOGADO}`);
            if (!response.ok) throw new Error('Falha ao carregar plano');

            const plano = await response.json();
            planoContainer.innerHTML = ''; 
            
            if (Object.keys(plano).length === 0) {
                planoContainer.innerHTML = "<p>Seu plano nutricional ainda não foi cadastrado.</p>";
                return;
            }

            const icones = {
                'cafe da manha': 'fa-coffee',
                'almoco': 'fa-utensils',
                'janta': 'fa-moon',
                'lanche': 'fa-apple-alt',
                'lanche da tarde': 'fa-apple-alt',
                'ceia': 'fa-cookie-bite'
            };

            for (const [refeicao, itens] of Object.entries(plano)) {
                const icone = icones[refeicao] || 'fa-clipboard-list';
                let itensHtml = '';
                itens.forEach(item => {
                    const p = item.per_100g;
                    itensHtml += `<li><b>${item.nome}</b> (${p.cal.toFixed(0)} kcal/100g)</li>`;
                });

                planoContainer.innerHTML += `
                    <div class="refeicao-card">
                        <h3><i class="fas ${icone} refeicao-icon"></i> ${refeicao.charAt(0).toUpperCase() + refeicao.slice(1)}</h3>
                        <ul>
                            ${itensHtml}
                        </ul>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Erro ao carregar plano:', error);
            planoContainer.innerHTML = "<p>Erro ao carregar seu plano nutricional.</p>";
        }
    }

    // Carregar informações da Nutri (chamado ao clicar na aba)
    async function carregarInfoNutri() {
        const container = document.querySelector('#info .nutri-contato ul');
        container.innerHTML = "<li>Carregando...</li>";
        
        try {
            // Reutilizamos o endpoint de perfil do cliente, que já nos dá o email da nutri
            const response = await fetch(`/api/clientes/${ID_CLIENTE_LOGADO}/perfil`);
            if (!response.ok) throw new Error('Falha ao carregar dados');
            
            const perfil = await response.json();
            
            // Popula os dados de contato
            container.innerHTML = `
                <li><i class="fas fa-phone-alt"></i> Telefone: (99) 99999-9999 (Exemplo)</li>
                <li><i class="fas fa-envelope"></i> E-mail: ${perfil.email_nutri || 'Não informado'}</li>
            `;
            // O H3 já foi populado no início
            document.querySelector('#info .nutri-credenciais').textContent = `CRN ${perfil.id_nutri}`;

        } catch (error) {
            console.error('Erro ao carregar info da nutri:', error);
            container.innerHTML = "<li>Erro ao carregar informações.</li>";
        }
    }
    
    // Inicia o carregamento do chat
    carregarHistoricoChat();
});
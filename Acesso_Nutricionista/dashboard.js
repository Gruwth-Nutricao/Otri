document.addEventListener('DOMContentLoaded', function() {
    
    // --- 1. Variáveis Globais e Verificação de Login ---
    const ID_NUTRI_LOGADA = localStorage.getItem('id_nutri');
    if (!ID_NUTRI_LOGADA) {
        alert("Sessão não encontrada. Por favor, faça o login.");
        window.location.href = 'login.html';
        return;
    }
    
    const NOME_NUTRI_LOGADA = localStorage.getItem('nome_nutri') || 'Nutricionista';
    document.querySelector('.sidebar-profile span').textContent = `Dr(a). ${NOME_NUTRI_LOGADA}`;
    
    // Armazena o ID do cliente que está sendo visualizado na tela de chat
    let clienteIdAtual = null;
    let timerBuscaAlimento = null;
    

    const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
    const contentSections = document.querySelectorAll('.content-section');

    navItems.forEach(item => {
        item.addEventListener('click', function(event) {
            event.preventDefault();
            const targetId = this.getAttribute('data-target');
            
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');

            contentSections.forEach(section => section.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');
            
            // Carregar dados da aba clicada
            if (targetId === 'dashboard') {
                carregarClientesDashboard();
            } else if (targetId === 'bot-config') {
                carregarBotConfig();
            } else if (targetId === 'profile') {
                carregarNutriPerfil();
            } else if (targetId === 'debug') {
                setupDebugTela();
            }
        });
    });

 
    const newClientBtn = document.querySelector('.btn-primary[data-target="new-client"]');
    if (newClientBtn) {
        newClientBtn.addEventListener('click', function(event) {
            event.preventDefault();
            document.querySelector('.nav-item.active').classList.remove('active');
            document.querySelector('.nav-item[data-target="new-client"]').classList.add('active');
            document.querySelector('.content-section.active').classList.remove('active');
            document.getElementById('new-client').classList.add('active');
        });
    }


    const clientList = document.querySelector('.client-list');
    
    async function carregarClientesDashboard() {
        clientList.innerHTML = '<li>Carregando clientes...</li>';
        try {
            const response = await fetch(`/api/nutricionistas/${ID_NUTRI_LOGADA}/clientes`);
            if (!response.ok) throw new Error('Falha ao carregar clientes');
            
            const clientes = await response.json();
            clientList.innerHTML = ''; 
            
            if (clientes.length === 0) {
                clientList.innerHTML = '<li>Nenhum cliente cadastrado.</li>';
                return;
            }

            clientes.forEach(cliente => {
                const li = document.createElement('li');
                li.classList.add('client-item');
                li.setAttribute('data-client-id', cliente.id_cliente);
                li.innerHTML = `
                    <div class="client-info">
                        <img src="https://via.placeholder.com/40" alt="Foto ${cliente.nome}" class="client-avatar">
                        <span>${cliente.nome} (${cliente.email})</span>
                    </div>
                    <div class="client-status inactive-chat">
                        <span class="status-indicator"></span> Chat Inativo
                    </div>
                    <button class="btn-view-chat">Gerenciar Cliente</button>
                `;
                li.querySelector('.btn-view-chat').addEventListener('click', () => {
                    visualizarChatCliente(cliente.id_cliente, cliente.nome);
                });
                clientList.appendChild(li);
            });
            

            document.querySelector('.stat-card .stat-number').textContent = clientes.length;

        } catch (error) {
            console.error('Erro ao carregar clientes:', error);
            clientList.innerHTML = '<li>Erro ao carregar clientes.</li>';
        }
    }

    
    const chatContainer = document.querySelector('#chat-view .chat-messages');
    const btnConfigBotChat = document.getElementById('btn-config-bot-chat');
    const btnDeleteClient = document.getElementById('btn-delete-client');
    const planoAtualLista = document.getElementById('plano-atual-lista');

    function visualizarChatCliente(clienteId, clienteNome) {
        clienteIdAtual = clienteId; 
        
      
        document.querySelector('.content-section.active').classList.remove('active');
        document.getElementById('chat-view').classList.add('active');
        document.querySelector('#chat-view .section-header h2').textContent = `Gerenciar ${clienteNome}`;
   
        carregarHistoricoChat(clienteId);
        carregarPlanoAtual(clienteId);
    }
    
    async function carregarHistoricoChat(clienteId) {
        chatContainer.innerHTML = '<p>Carregando histórico...</p>';
        try {
            const response = await fetch(`/api/chat/${clienteId}/historico`);
            const historico = await response.json();
            chatContainer.innerHTML = '';
            historico.forEach(msg => {
                const bubble = document.createElement('div');
                bubble.classList.add('chat-bubble');
                bubble.classList.add(msg.role === 'user' ? 'user-message' : 'bot-message');
                bubble.innerText = msg.texto;
                chatContainer.appendChild(bubble);
            });
            chatContainer.scrollTop = chatContainer.scrollHeight;
        } catch (err) {
            chatContainer.innerHTML = '<p>Erro ao carregar histórico.</p>';
        }
    }
    

    btnConfigBotChat.addEventListener('click', () => {
        document.querySelector('.nav-item[data-target="bot-config"]').click();
    });
    

    btnDeleteClient.addEventListener('click', async () => {
        if (!clienteIdAtual) return;
        
        if (confirm(`Tem certeza que deseja excluir este cliente? Esta ação não pode ser desfeita.`)) {
            try {
                const response = await fetch(`/api/clientes/${clienteIdAtual}`, {
                    method: 'DELETE'
                });
                if (!response.ok) throw new Error('Falha ao excluir');
                
                alert("Cliente excluído com sucesso.");
                document.querySelector('.nav-item[data-target="dashboard"]').click();
                clienteIdAtual = null; // Limpa o ID
            } catch (error) {
                alert("Erro ao excluir cliente.");
            }
        }
    });

    const newClientForm = document.getElementById('form-new-client');
    newClientForm.addEventListener('submit', async function(event) {
        event.preventDefault(); 
        
        const data = {
            id_nutri: ID_NUTRI_LOGADA,
            nome: document.getElementById('nome-cliente').value,
            email: document.getElementById('email-cliente').value,
            senha: document.getElementById('senha-cliente').value,
            idade: parseInt(document.getElementById('idade-cliente').value),
            sexo: document.getElementById('sexo-cliente').value,
            peso_kg: parseFloat(document.getElementById('peso-cliente').value),
            altura_cm: parseFloat(document.getElementById('altura-cliente').value),
            atividade: document.getElementById('atividade-cliente').value
        };
        
        if(!data.nome || !data.email || !data.senha) {
            alert("Por favor, preencha todos os campos de acesso.");
            return;
        }

        try {
            const response = await fetch(`/api/clientes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Erro ao cadastrar');
            }

            const novoCliente = await response.json();
            alert(`Cliente '${novoCliente.nome}' cadastrado com sucesso!`);
            
            newClientForm.reset();
            document.querySelector('.nav-item[data-target="dashboard"]').click();
            
        } catch (error) {
            alert(`Erro: ${error.message}`);
        }
    });

    const perfilForm = document.getElementById('form-profile-nutri');
    
    async function carregarNutriPerfil() {
        try {
            const response = await fetch(`/api/nutricionistas/${ID_NUTRI_LOGADA}/perfil`);
            if (!response.ok) throw new Error('Falha ao carregar perfil');
            const perfil = await response.json();
            
            document.getElementById('nome-perfil').value = perfil.nome;
            document.getElementById('email-perfil').value = perfil.email;
            document.getElementById('senha-perfil').value = ""; // Limpa campo de senha
        } catch (error) {
            console.error(error);
            alert("Erro ao carregar perfil da Nutri.");
        }
    }
    
    perfilForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const nome = document.getElementById('nome-perfil').value;
        const email = document.getElementById('email-perfil').value;
        const senha = document.getElementById('senha-perfil').value;
        
        const data = { nome, email };
        if (senha) { 
            data.senha = senha;
        }

        try {
            const response = await fetch(`/api/nutricionistas/${ID_NUTRI_LOGADA}/perfil`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                 const err = await response.json();
                 throw new Error(err.detail || 'Falha ao salvar');
            }
            const perfilAtualizado = await response.json();
            

            localStorage.setItem('nome_nutri', perfilAtualizado.nome);
            document.querySelector('.sidebar-profile span').textContent = `Dr(a). ${perfilAtualizado.nome}`;
            
            alert("Perfil salvo com sucesso!");
            document.getElementById('senha-perfil').value = "";
        } catch (error) {
            alert(`Erro ao salvar perfil: ${error.message}`);
        }
    });


    const botConfigForm = document.getElementById('form-bot-config');
    const colorBoxes = document.querySelectorAll('.color-box');
    
    async function carregarBotConfig() {
        try {
            const response = await fetch(`/api/nutricionistas/${ID_NUTRI_LOGADA}/bot-config`);
            if (!response.ok) throw new Error('Falha ao carregar config');
            const config = await response.json();

            document.getElementById('persona').value = config.bot_persona || '';
            document.getElementById('restricoes').value = config.bot_restricoes || '';
            
            colorBoxes.forEach(c => c.classList.remove('selected'));
            const corSelecionada = document.querySelector(`.color-box[data-color="${config.bot_cor}"]`);
            if (corSelecionada) {
                corSelecionada.classList.add('selected');
            }
        } catch (error) {
            console.error(error);
            alert("Erro ao carregar configuração do Bot.");
        }
    }
    
    botConfigForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const persona = document.getElementById('persona').value;
        const restricoes = document.getElementById('restricoes').value;
        const cor = document.querySelector('.color-box.selected')?.getAttribute('data-color') || '#3498db';

        try {
            const response = await fetch(`/api/nutricionistas/${ID_NUTRI_LOGADA}/bot-config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ persona, restricoes, cor })
            });
            if (!response.ok) throw new Error('Falha ao salvar');
            alert("Configurações do Bot salvas com sucesso!");
        } catch (error) {
            console.error(error);
            alert("Erro ao salvar configurações.");
        }
    });

    colorBoxes.forEach(box => {
        box.addEventListener('click', function() {
            colorBoxes.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
        });
    });
    

    const debugSelect = document.querySelector('.debug-container .client-select');
    const debugInput = document.querySelector('.debug-container .debug-input');
    const debugButton = document.querySelector('.debug-container .btn-primary-form');
    const debugOutput = document.querySelector('.debug-container .debug-output');

    async function setupDebugTela() {
        try {
            const response = await fetch(`/api/nutricionistas/${ID_NUTRI_LOGADA}/clientes`);
            const clientes = await response.json();
            
            debugSelect.innerHTML = '<option value="">Selecione um cliente...</option>'; 
            clientes.forEach(cliente => {
                debugSelect.innerHTML += `<option value="${cliente.id_cliente}">${cliente.nome}</option>`;
            });
        } catch (error) {
            console.error("Erro ao popular clientes no debug:", error);
        }
    }

    debugButton.addEventListener('click', async () => {
        const clienteId = debugSelect.value;
        const texto = debugInput.value;
        
        if (!clienteId) { alert("Selecione um cliente para testar."); return; }
        if (!texto) { alert("Digite uma mensagem de teste."); return; }

        debugOutput.innerHTML = `<p><strong>Você (para ${clienteId}):</strong> ${texto}</p>`;
        
        try {
            const response = await fetch(`/api/chat/${clienteId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ texto: texto }),
            });
            
            if (!response.ok) throw new Error('Erro na API');
            const data = await response.json();

            debugOutput.innerHTML += `<p><strong>Bot (resposta):</strong> ${data.resposta.replace(/\n/g, '<br>')}</p>`;
            debugInput.value = ''; 

        } catch (error) {
            debugOutput.innerHTML += `<p><strong>Erro:</strong> ${error.message}</p>`;
        }
    });
    
    
    const inputBuscaAlimento = document.getElementById('input-busca-alimento');
    const buscaResultados = document.getElementById('busca-resultados');
    const selectRefeicao = document.getElementById('select-refeicao');

   
    inputBuscaAlimento.addEventListener('keyup', () => {
        clearTimeout(timerBuscaAlimento);
        const query = inputBuscaAlimento.value;
        
        if (query.length < 3) {
            buscaResultados.innerHTML = '';
            return;
        }
        
        timerBuscaAlimento = setTimeout(async () => {
            try {
                const response = await fetch(`/api/admin/buscar-alimento?q=${query}`);
                const alimentos = await response.json();
                
                buscaResultados.innerHTML = '';
                if (alimentos.length === 0) {
                    buscaResultados.innerHTML = '<div>Nenhum alimento encontrado.</div>';
                    return;
                }
                
                alimentos.forEach(alimento => {
                    const div = document.createElement('div');
                    div.textContent = `${alimento.descricao_alimento} (${alimento.energia_kcal.toFixed(0)} kcal/100g)`;
                   
                    div.dataset.alimento = JSON.stringify(alimento); 
                    div.addEventListener('click', () => adicionarAlimentoAoPlano(alimento));
                    buscaResultados.appendChild(div);
                });
            } catch (error) {
                console.error("Erro na busca:", error);
                buscaResultados.innerHTML = '<div>Erro ao buscar.</div>';
            }
        }, 500); 
    });

    
    async function adicionarAlimentoAoPlano(alimento) {
        if (!clienteIdAtual) return;
        
        const refeicao = selectRefeicao.value;
        const data = {
            refeicao: refeicao,
            nome_alimento: alimento.descricao_alimento,
            cal_100g: alimento.energia_kcal,
            prot_100g: alimento.proteina_g,
            carb_100g: alimento.carboidrato_g,
            fat_100g: alimento.lipideo_g
        };

        try {
            const response = await fetch(`/api/planos/${clienteIdAtual}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                 const err = await response.json();
                 throw new Error(err.detail || 'Falha ao adicionar');
            }
            
            
            inputBuscaAlimento.value = '';
            buscaResultados.innerHTML = '';
            carregarPlanoAtual(clienteIdAtual); 
            
        } catch (error) {
            alert(`Erro: ${error.message}`);
        }
    }

    
    async function carregarPlanoAtual(clienteId) {
        planoAtualLista.innerHTML = '<li>Carregando plano...</li>';
        try {
            const response = await fetch(`/api/planos/${clienteId}`);
            if (!response.ok) throw new Error('Falha ao carregar plano');
            
            const plano = await response.json();
            planoAtualLista.innerHTML = '';
            
            if (Object.keys(plano).length === 0) {
                planoAtualLista.innerHTML = '<li>Plano ainda vazio.</li>';
                return;
            }

            for (const [refeicao, itens] of Object.entries(plano)) {
                itens.forEach(item => {
                    planoAtualLista.innerHTML += `<li><strong>${refeicao}:</strong> ${item.nome}</li>`;
                });
            }
        } catch (error) {
            planoAtualLista.innerHTML = '<li>Erro ao carregar plano.</li>';
        }
    }
    
    
    carregarClientesDashboard();
});
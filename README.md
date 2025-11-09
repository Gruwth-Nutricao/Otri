# COMO RODAR 

apos criar o ambiente virtual 
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn api:app --reload


# Gruwth – Nutrição Inteligente com IA

Imagine uma nutricionista que nunca dorme, nunca perde uma mensagem e está sempre pronta para responder às dúvidas de seus clientes. Essa é a proposta do **Gruwth**: uma plataforma que combina Inteligência Artificial com a metodologia de cada nutricionista, oferecendo um atendimento personalizado, escalável e disponível 24 horas por dia.  

O Gruwth não substitui o acompanhamento humano, mas otimiza o tempo da nutricionista, aumenta a adesão do cliente e transforma o relacionamento entre profissional e paciente.

Com o Gruwth, o cliente pode perguntar:
- "O que devo comer agora no almoço?"
- "Comi tais coisas, ainda posso comer algo sem estourar as calorias?"  

E receber uma resposta baseada em seu perfil, nas orientações do nutricionista e em bases de dados nutricionais confiáveis.  

Para a nutricionista, o sistema oferece um painel administrativo completo, permitindo configurar metodologias, lançar informações clínicas do cliente e acompanhar a evolução em tempo real.

---

## 1. Identificação do Projeto

- **Título do Projeto:** Gruwth  
- **Área de Aplicação:** Saúde e bem-estar  
- **Orientador/Professor:** Rogério Morandi  
- **Equipe/Integrantes:** Guilherme Henrique, Guilherme Nicchio, Pedro Fernandes  

---

## 2. Justificativa

Muitos clientes de nutrição não conseguem manter constância ou adesão aos planos, seja por dúvidas diárias ou falta de acompanhamento próximo.  

Para o nutricionista, isso significa tempo perdido com dúvidas repetitivas e menor engajamento do paciente. O Gruwth surge para resolver essa lacuna, oferecendo respostas inteligentes, personalizadas e contínuas, reforçando as orientações do profissional e aumentando a satisfação e os resultados do cliente.

**Benefícios esperados:**
- Atendimento 24h baseado na metodologia do nutricionista.
- Otimização do tempo do profissional, com redução de dúvidas recorrentes.
- Aumento da adesão ao plano alimentar e melhores resultados clínicos.
- Diferenciação competitiva para nutricionistas no mercado.

---

## 3. Objetivos

**Objetivo Geral:**  
Desenvolver um sistema de apoio nutricional baseado em IA que ofereça recomendações alimentares personalizadas, seguindo as diretrizes de cada nutricionista, e que permita interação contínua entre cliente e profissional.

**Objetivos Específicos:**  
- Coletar e organizar dados do cliente (idade, peso, altura, sexo, objetivos, restrições, preferências alimentares).  
- Integrar dados nutricionais de bases oficiais (TACO, TBCA, USDA, Open Food Facts).  
- Utilizar algoritmos de cálculo energético e de recomendação personalizada.  
- Estimar estratégias nutricionais de acordo com cada perfil e metodologia do nutricionista.  
- Fornecer recomendações de metas diárias e semanais de forma interativa.  
- Garantir segurança e privacidade em conformidade com a LGPD.  
- Implementar atendimento personalizado com modelo de ML.

---

## 4. Entradas que a nutricionista deve fornecer

**Dados essenciais:**
- Identificação do cliente: nome, idade, sexo, histórico.
- Antropometria: peso, altura, circunferência de cintura.
- Objetivo principal (emagrecimento, hipertrofia, manutenção, gestação etc.).
- Nível de atividade física.
- Restrições alimentares e preferências pessoais.
- Horários e janelas de refeição.
- Meta calórica ou fórmula para cálculo automático.
- Tom de comunicação das respostas.

**Dados avançados (opcional):**
- Valores laboratoriais (HbA1c, perfil lipídico, TSH etc.).
- Uso de medicamentos.
- Diagnósticos clínicos relevantes.
- Condições socioeconômicas e orçamento.
- Objetivos temporais (ex.: “-6 kg em 12 semanas”).
- Limites de monitoramento.

**Configuração da metodologia do nutricionista:**
- Regras fixas e proibitivas.
- Fórmulas de cálculo energético preferidas.
- Macros-alvo padrão.
- Tabelas de substituição e equivalências.
- Padrões de prescrição.
- Regras de resposta (número de sugestões, estilo de escrita, exemplos prontos).

---

## 5. Escopo do Projeto

- Painel administrativo para nutricionista configurar metodologias e lançar dados do cliente.  
- Chat para clientes interagirem com a IA 24h/dia.  
- Personalização total por profissional, diferenciando abordagens.  
- Base de dados integrada com tabelas oficiais (TACO, TBCA, USDA, Open Food Facts).  
- Material de suporte e treinamento para nutricionistas.

---

## 6. Fundamentação Teórica

- Regressão e equações metabólicas para estimativa de gasto calórico.  
- Sistemas de recomendação baseados em perfis e preferências.  
- RAG (Retrieval-Augmented Generation) para consultas nutricionais personalizadas.  
- Bases de dados nutricionais oficiais como fonte de informação.  

**Fundamentos nutricionais:**  
- Energia total: calorias de refeições somando macros (carboidratos * 4 + proteínas * 4 + gorduras * 9).  
- Distribuição de macronutrientes: comparação com recomendações (% do total calórico).  
- IMC, TMB, Gasto Energético Total (GET): fórmulas padrão (Harris-Benedict, Mifflin-St Jeor).  
- Ajuste por objetivo: perda, ganho ou manutenção de peso.

---

## 7. Metodologia

**Coleta de dados:**  
- Tabelas nutricionais (TACO, TBCA, USDA, Open Food Facts).  
- Dados clínicos lançados pela nutricionista e feedback contínuo do cliente.

**Pré-processamento:**  
- Normalização das tabelas, padronização de medidas caseiras, vinculação de GTIN e alimentos industrializados.

**Algoritmos de IA:**  
- Regressão Linear e Random Forest para gasto calórico.  
- KNN e clustering para agrupamento de perfis alimentares.  
- LLM + RAG para linguagem natural no chat.

**Tecnologias:**  
- Front-end: React (web e mobile).  
- Back-end: FastAPI, PostgreSQL, PostGIS.  
- ML/IA: Python, integração com LLMs.  
- Integração futura: reconhecimento de alimentos por imagem (Food-101 dataset).

**Fontes de dados:**  
- TACO, TBCA, USDA, IBGE/POF, DRIs/RDA, Open Food Facts, INMETRO/ANVISA, OMS.

---

## 8. Cronograma (Resumo)

| Semana | Atividade | Entregável | Responsável |
|--------|-----------|------------|-------------|
| 1 | Planejamento e requisitos | Documento de requisitos, backlog inicial | Todos |
| 2 | Dados e arquitetura | Banco de dados inicial, documento de arquitetura | Pedro |
| 3 | Backend & IA inicial | API funcional, protótipo de IA | Nicchio |
| 4 | Desenvolvimento IA | Modelo funcional com dados reais, relatório de testes | Nicchio e Pedro |
| 5 | Interface e protótipo | Protótipo visual navegável | Henrique |
| 6 | Integração completa & testes | App funcional (frontend + backend + IA) | Henrique e Nicchio |
| 7 | Validação, ajustes e entrega | Protótipo funcional completo | Todos |
| 8 | Documentação | Documentação técnica e apresentação final | Henrique e Pedro |

---

## 9. Critérios de Sucesso

- Precisão das estimativas de gasto calórico.  
- Qualidade e relevância das recomendações personalizadas.  
- Satisfação da nutricionista com a metodologia personalizada.  
- Aumento da adesão alimentar do cliente.

---

## 10. Riscos e Limitações

- Dificuldade de integração com APIs externas.  
- Variabilidade individual no metabolismo.  
- Limitação do projeto à nutrição – não substitui acompanhamento médico.  
- Risco regulatório (LGPD e ANVISA) se termos de uso não forem claros.

---

## 11. Entregáveis

- Código-fonte da aplicação.  
- Relatório técnico.  
- Protótipo funcional (web e mobile).  
- Documentação.  
- Apresentação final.

---

**Resumo:**  
O Gruwth é uma ferramenta que une tecnologia, ciência da nutrição e atendimento humanizado, garantindo que cada cliente receba o melhor acompanhamento possível, no momento exato em que precisa.

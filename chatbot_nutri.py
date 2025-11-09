import os
import json
import re
import math
import pandas as pd
from rapidfuzz import process
import uuid
from unidecode import unidecode
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
import sqlite3 # Importamos SQLite
try:
    from sentence_transformers import SentenceTransformer, util
except Exception as e:
    raise RuntimeError("Erro ao importar sentence-transformers. "
                       "Instale com: pip install sentence-transformers torch numpy") from e

# --- Constantes e Modelos Globais ---

# 1. Modelos de IA (carregados uma vez)
MODELO_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"
MODELO_IA = None
DF_ALIMENTOS = None
INTENCOES_EMBED = {}

# 2. Banco de Dados
ARQUIVO_BANCO = "nutri.db" 

# 3. Lógica de Negócio
FATORES_ATIVIDADE = {
    "sedentario": 1.2,
    "leve": 1.375,
    "moderado": 1.55,
    "ativo": 1.725,
    "muito_ativo": 1.9
}
MEAL_KEYS = ["cafe da manha", "almoco", "lanche", "lanche da tarde", "janta", "ceia", "lanche noturno"]
GRAMAS_PATTERN = re.compile(r'(\d+(?:[.,]\d+)?)\s*(g|gramas|grama|gr)\b', re.I)
ITEM_GRAMA_PAIR_PATTERN = re.compile(r'([A-Za-zÀ-ú0-9\s\-\+]+?)\s*,?\s*(\d+(?:[.,]\d+)?\s*(?:g|gramas|gr)\b)', re.I)

# --- Funções de Inicialização ---

def carregar_modelos():
    """Carrega os modelos de IA e a base de dados de alimentos na memória."""
    global MODELO_IA, DF_ALIMENTOS, INTENCOES_EMBED
    
    if MODELO_IA: # Previne recarregamento
        return

    print("Carregando modelo de IA...")
    MODELO_IA = SentenceTransformer(MODELO_EMBEDDING)
    print("Modelo de IA carregado.")

    print("Carregando base de alimentos...")
    try:
        DF_ALIMENTOS = pd.read_csv("base-comidas-tratada.xlsx - basona.csv")
        if "descricao_alimento" not in DF_ALIMENTOS.columns:
            raise ValueError("Coluna 'descricao_alimento' não encontrada no CSV.")
            
        DF_ALIMENTOS["descricao_alimento_norm"] = DF_ALIMENTOS["descricao_alimento"].astype(str).str.lower().str.strip().apply(lambda x: unidecode(x))
        print(f"Base de alimentos carregada: {len(DF_ALIMENTOS)} itens.")
    except Exception as e:
        print(f"Erro ao carregar 'base-comidas-tratada.xlsx - basona.csv': {e}")
        try:
            DF_ALIMENTOS = pd.read_excel("base-comidas-tratada.xlsx", sheet_name="basona")
            DF_ALIMENTOS["descricao_alimento_norm"] = DF_ALIMENTOS["descricao_alimento"].astype(str).str.lower().str.strip().apply(lambda x: unidecode(x))
            print(f"Base de alimentos (Excel) carregada: {len(DF_ALIMENTOS)} itens.")
        except Exception as e_xlsx:
            print(f"Erro fatal ao carregar base de alimentos: {e_xlsx}")
            DF_ALIMENTOS = pd.DataFrame(columns=["descricao_alimento", "descricao_alimento_norm", "energia_kcal", "proteina_g", "carboidrato_g", "lipideo_g"])

    print("Carregando intenções...")
    CAMINHO_INTENCOES = "intencoes.json"
    if os.path.exists(CAMINHO_INTENCOES):
        with open(CAMINHO_INTENCOES, "r", encoding="utf-8") as f:
            INTENCOES_EXEMPLO = json.load(f)
        
        INTENCOES_EMBED = {k: MODELO_IA.encode(v, convert_to_tensor=True) for k, v in INTENCOES_EXEMPLO.items()}
        print("Intenções carregadas.")
    else:
        print(f"Aviso: Arquivo '{CAMINHO_INTENCOES}' não encontrado. A IA de intenção ficará limitada.")
        INTENCOES_EXEMPLO = {}
        INTENCOES_EMBED = {}


# --- Nova Arquitetura de Banco de Dados (SQLite) ---

def get_db():
    """Cria uma conexão com o banco de dados."""
    db = sqlite3.connect(ARQUIVO_BANCO, check_same_thread=False)
    db.row_factory = sqlite3.Row # Permite acessar colunas por nome
    return db

def init_db():
    """Cria as tabelas do banco de dados se não existirem."""
    schema = """
    CREATE TABLE IF NOT EXISTS nutricionistas (
        id_nutri TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL, -- Em produção, deve ser um hash
        criado_em TEXT NOT NULL,
        bot_persona TEXT,
        bot_restricoes TEXT,
        bot_cor TEXT
    );

    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente TEXT PRIMARY KEY,
        id_nutri TEXT NOT NULL, -- Link para o nutricionista
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL, -- Em produção, deve ser um hash
        idade INTEGER,
        sexo TEXT,
        peso_kg REAL,
        altura_cm REAL,
        atividade TEXT,
        peso_inicial REAL,
        meta TEXT,
        agua_meta_ml INTEGER,
        criado_em TEXT NOT NULL,
        FOREIGN KEY (id_nutri) REFERENCES nutricionistas (id_nutri)
    );

    CREATE TABLE IF NOT EXISTS planos (
        id_plano INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente TEXT NOT NULL,
        refeicao TEXT NOT NULL,
        id_item TEXT NOT NULL, -- uuid do item
        nome TEXT NOT NULL,
        cal_100g REAL DEFAULT 0,
        prot_100g REAL DEFAULT 0,
        carb_100g REAL DEFAULT 0,
        fat_100g REAL DEFAULT 0,
        embedding_texto TEXT,
        embedding_vec BLOB, -- Armazena o embedding como BLOB
        UNIQUE(id_cliente, refeicao, nome)
    );

    CREATE TABLE IF NOT EXISTS conversas (
        id_conversa INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente TEXT NOT NULL,
        role TEXT NOT NULL, -- 'user' or 'bot'
        texto TEXT NOT NULL,
        time TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS registros_consumo (
        id_registro INTEGER PRIMARY KEY AUTOINCREMENT,
        id_cliente TEXT NOT NULL,
        data_hora TEXT NOT NULL,
        refeicao TEXT,
        nome_item TEXT,
        gramas REAL,
        kcal REAL
    );
    """
    with get_db() as db:
        db.executescript(schema)
    
    # --- Adicionar dados de teste se o DB estiver vazio ---
    try:
        with get_db() as db:
            # Verificar se já existe um nutri
            cursor = db.execute("SELECT id_nutri FROM nutricionistas LIMIT 1")
            if cursor.fetchone() is None:
                print("Banco de dados vazio. Criando dados de teste...")
                # 1. Criar Nutri de Teste
                id_nutri_teste = 'nutri-teste-01'
                db.execute(
                    "INSERT OR IGNORE INTO nutricionistas (id_nutri, nome, email, senha, criado_em, bot_persona, bot_restricoes, bot_cor) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (id_nutri_teste, 'Dra. Ana Silva', 'nutri@teste.com', '123', datetime.utcnow().isoformat(), 'Uma assistente amigável e motivadora.', 'Nunca dar diagnósticos.', '#3498db')
                )
                
                # 2. Criar Cliente de Teste
                id_cliente_teste = 'cliente-teste-01'
                db.execute(
                    """INSERT OR IGNORE INTO clientes (id_cliente, id_nutri, nome, email, senha, idade, sexo, peso_kg, altura_cm, atividade, peso_inicial, criado_em, meta)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (id_cliente_teste, id_nutri_teste, 'Carlos Mendes', 'cliente@teste.com', '123', 30, 'M', 85.0, 175.0, 'sedentario', 85.0, datetime.utcnow().isoformat(), 'Perder peso')
                )
                print("Nutricionista (nutri@teste.com) e Cliente (cliente@teste.com) de teste criados. Senha para ambos: 123")
            
            else:
                print("Banco de dados já populado.")
                
    except Exception as e:
        print(f"Erro ao criar dados de teste: {e}")
    
    print("Banco de dados SQLite inicializado.")


# --- Funções Auxiliares ---

def gerar_id() -> str:
    return str(uuid.uuid4())[:8]

def normalizar_texto(txt: str) -> str:
    if not isinstance(txt, str):
        return ""
    return re.sub(r'\s+', ' ', txt.strip().lower())

# --- Lógica de Nutricionistas e Clientes (Atualizada para SQLite) ---

def criar_nutricionista(nome: str, email: str, senha: str) -> str:
    idn = gerar_id()
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO nutricionistas (id_nutri, nome, email, senha, criado_em) VALUES (?, ?, ?, ?, ?)",
                (idn, nome, email, senha, datetime.utcnow().isoformat())
            )
        return idn
    except sqlite3.IntegrityError:
        return None # Email já existe

def criar_cliente(id_nutri: str, nome: str, email: str, senha: str, idade: int, sexo: str, peso_kg: float, altura_cm: float, atividade: str="sedentario") -> str:
    idc = gerar_id()
    try:
        with get_db() as db:
            db.execute(
                """INSERT INTO clientes (id_cliente, id_nutri, nome, email, senha, idade, sexo, peso_kg, altura_cm, atividade, peso_inicial, criado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (idc, id_nutri, nome, email, senha, int(idade), sexo, float(peso_kg), float(altura_cm), atividade, float(peso_kg), datetime.utcnow().isoformat())
            )
        return idc
    except sqlite3.IntegrityError:
        return None # Email já existe
    except Exception as e:
        print(f"Erro ao criar cliente: {e}")
        return None

def atualizar_cliente(id_cliente: str, campos: Dict[str, Any]) -> bool:
    campos_permitidos = {"nome", "idade", "sexo", "peso_kg", "altura_cm", "atividade", "meta", "agua_meta_ml"}
    
    set_clause = []
    valores = []
    
    for campo, valor in campos.items():
        if campo in campos_permitidos:
            set_clause.append(f"{campo} = ?")
            valores.append(valor)
    
    if not set_clause:
        return False 
        
    valores.append(id_cliente)
    query = f"UPDATE clientes SET {', '.join(set_clause)} WHERE id_cliente = ?"
    
    try:
        with get_db() as db:
            db.execute(query, tuple(valores))
        return True
    except Exception as e:
        print(f"Erro ao atualizar cliente: {e}")
        return False

def get_cliente_por_id(id_cliente: str) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        cursor = db.execute("SELECT * FROM clientes WHERE id_cliente = ?", (id_cliente,))
        cliente = cursor.fetchone()
        return dict(cliente) if cliente else None

def get_cliente_perfil(id_cliente: str) -> Optional[Dict[str, Any]]:
    """Busca dados do cliente E nome da nutri para a tela de perfil."""
    with get_db() as db:
        query = """
            SELECT 
                c.id_cliente, c.nome, c.email, c.idade, c.sexo, c.peso_kg, c.altura_cm, c.meta,
                n.nome as nome_nutri,
                n.email as email_nutri,
                n.id_nutri
            FROM clientes c
            JOIN nutricionistas n ON c.id_nutri = n.id_nutri
            WHERE c.id_cliente = ?
        """
        cursor = db.execute(query, (id_cliente,))
        perfil = cursor.fetchone()
        
        if not perfil:
            return None
            
        perfil_dict = dict(perfil)
        # Calcular IMC
        if perfil_dict.get("peso_kg") and perfil_dict.get("altura_cm"):
            perfil_dict["imc"] = calcular_imc(perfil_dict["peso_kg"], perfil_dict["altura_cm"])
            perfil_dict["imc_class"] = classificar_imc(perfil_dict["imc"])
        else:
            perfil_dict["imc"] = None
            perfil_dict["imc_class"] = "Dados insuficientes"
            
        return perfil_dict

def get_nutri_perfil(id_nutri: str) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        cursor = db.execute("SELECT id_nutri, nome, email FROM nutricionistas WHERE id_nutri = ?", (id_nutri,))
        nutri = cursor.fetchone()
        return dict(nutri) if nutri else None

def update_nutri_perfil(id_nutri: str, nome: str, email: str, senha: Optional[str] = None) -> bool:
    """Atualiza o perfil da nutricionista. Só atualiza a senha se ela for fornecida."""
    try:
        with get_db() as db:
            if senha:
                # Se uma nova senha foi fornecida, atualiza
                db.execute(
                    "UPDATE nutricionistas SET nome = ?, email = ?, senha = ? WHERE id_nutri = ?",
                    (nome, email, senha, id_nutri)
                )
            else:
                # Se a senha for None ou "", não mexe na senha
                db.execute(
                    "UPDATE nutricionistas SET nome = ?, email = ? WHERE id_nutri = ?",
                    (nome, email, id_nutri)
                )
        return True
    except sqlite3.IntegrityError:
        print(f"Erro: Email '{email}' já está em uso por outra conta.")
        return False
    except Exception as e:
        print(f"Erro ao atualizar perfil da nutri: {e}")
        return False

def delete_cliente(id_cliente: str) -> bool:
    """Deleta um cliente e todos os seus dados associados."""
    try:
        with get_db() as db:
            # Usar transação para garantir que tudo seja deletado
            db.execute("BEGIN TRANSACTION")
            db.execute("DELETE FROM clientes WHERE id_cliente = ?", (id_cliente,))
            db.execute("DELETE FROM planos WHERE id_cliente = ?", (id_cliente,))
            db.execute("DELETE FROM conversas WHERE id_cliente = ?", (id_cliente,))
            db.execute("DELETE FROM registros_consumo WHERE id_cliente = ?", (id_cliente,))
            db.execute("COMMIT")
        return True
    except Exception as e:
        print(f"Erro ao deletar cliente: {e}")
        with get_db() as db:
            db.execute("ROLLBACK") # Desfaz a transação em caso de erro
        return False

def listar_clientes_por_nutri(id_nutri: str) -> List[Dict[str, Any]]:
    with get_db() as db:
        cursor = db.execute("SELECT id_cliente, nome, email, peso_kg, altura_cm, meta FROM clientes WHERE id_nutri = ?", (id_nutri,))
        clientes = cursor.fetchall()
        return [dict(c) for c in clientes]

def login_cliente(email: str, senha: str) -> Optional[Dict[str, Any]]:
    """Ao logar, já busca o nome da nutricionista."""
    with get_db() as db:
        query = """
            SELECT 
                c.id_cliente, c.nome, n.nome as nome_nutri, n.id_nutri
            FROM clientes c
            JOIN nutricionistas n ON c.id_nutri = n.id_nutri
            WHERE c.email = ? AND c.senha = ?
        """
        cursor = db.execute(query, (email, senha))
        cliente = cursor.fetchone()
        return dict(cliente) if cliente else None

def login_nutri(email: str, senha: str) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        cursor = db.execute("SELECT * FROM nutricionistas WHERE email = ? AND senha = ?", (email, senha))
        nutri = cursor.fetchone()
        return dict(nutri) if nutri else None

# --- Lógica de Configuração do Bot ---

def get_bot_config(id_nutri: str) -> Optional[Dict[str, Any]]:
    with get_db() as db:
        cursor = db.execute("SELECT bot_persona, bot_restricoes, bot_cor FROM nutricionistas WHERE id_nutri = ?", (id_nutri,))
        config = cursor.fetchone()
        return dict(config) if config else None

def update_bot_config(id_nutri: str, persona: str, restricoes: str, cor: str) -> bool:
    try:
        with get_db() as db:
            db.execute(
                "UPDATE nutricionistas SET bot_persona = ?, bot_restricoes = ?, bot_cor = ? WHERE id_nutri = ?",
                (persona, restricoes, cor, id_nutri)
            )
        return True
    except Exception as e:
        print(f"Erro ao salvar config do bot: {e}")
        return False

# --- Lógica do Plano Alimentar (Atualizada para SQLite) ---

def adicionar_opcao_plano(id_cliente: str, refeicao: str, nome_alimento: str,
                          cal_100g: float, prot_100g: float=0.0, carb_100g: float=0.0, fat_100g: float=0.0) -> bool:
    """
    Adiciona opção ao plano. Retorna True se adicionou, False se já existia ou deu erro.
    """
    if MODELO_IA is None:
        print("Modelo de IA não carregado. Não é possível adicionar embedding.")
        return False
        
    refeicao_key = refeicao.strip().lower()
    id_item = gerar_id()
    
    # Gerar embedding
    texto_repr = f"{nome_alimento} - {cal_100g:.0f} kcal por 100g"
    embedding_vec_blob = None
    try:
        emb = MODELO_IA.encode(texto_repr, convert_to_tensor=True)
        embedding_vec_blob = emb.cpu().detach().numpy().tobytes()
    except Exception as e:
        print(f"[AVISO] falha ao gerar embedding para '{nome_alimento}': {e}")

    try:
        with get_db() as db:
            db.execute(
                """INSERT INTO planos (id_cliente, refeicao, id_item, nome, cal_100g, prot_100g, carb_100g, fat_100g, embedding_texto, embedding_vec)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (id_cliente, refeicao_key, id_item, nome_alimento, float(cal_100g), float(prot_100g), float(carb_100g), float(fat_100g), texto_repr, embedding_vec_blob)
            )
        return True
    except sqlite3.IntegrityError:
        print(f"Item '{nome_alimento}' já existe para '{refeicao_key}' deste cliente.")
        return False
    except Exception as e:
        print(f"Erro ao adicionar opção ao plano: {e}")
        return False

def listar_plano(id_cliente: str) -> Dict[str, List[Dict[str,Any]]]:
    plano_dict = {}
    with get_db() as db:
        cursor = db.execute("SELECT * FROM planos WHERE id_cliente = ? ORDER BY refeicao", (id_cliente,))
        itens = cursor.fetchall()
        
    for item_row in itens:
        item = dict(item_row)
        refeicao = item["refeicao"]
        if refeicao not in plano_dict:
            plano_dict[refeicao] = []
            
        # Recriar a estrutura aninhada 'per_100g' que o frontend espera
        item_formatado = {
            "id": item["id_item"],
            "nome": item["nome"],
            "per_100g": {
                "cal": item["cal_100g"],
                "prot": item["prot_100g"],
                "carb": item["carb_100g"],
                "fat": item["fat_100g"]
            }
        }
        plano_dict[refeicao].append(item_formatado)
        
    return plano_dict

def _encontrar_item_por_nome_por_embedding(id_cliente: str, texto_item: str, limiar: float=0.55) -> Optional[Tuple[str, Dict[str,Any]]]:
    """Encontra o item mais similar no plano do cliente usando embeddings."""
    if MODELO_IA is None: return None

    with get_db() as db:
        cursor = db.execute("SELECT * FROM planos WHERE id_cliente = ? AND embedding_vec IS NOT NULL", (id_cliente,))
        itens = cursor.fetchall()

    if not itens:
        return None

    emb_texto = MODELO_IA.encode(texto_item, convert_to_tensor=True)
    melhor_sim = -1.0
    melhor_match = None
    
    for item_row in itens:
        item = dict(item_row)
        vec_blob = item.get("embedding_vec")
        if vec_blob is None:
            continue
            
        try:
            # Converter BLOB de volta para tensor
            vec = pd.np.frombuffer(vec_blob, dtype=pd.np.float32) 
            sim = float(util.cos_sim(emb_texto, vec))
            
            if sim > melhor_sim:
                melhor_sim = sim
                # Formatar o item como a função original esperava
                item_formatado = {
                    "id": item["id_item"],
                    "nome": item["nome"],
                    "per_100g": {
                        "cal": item["cal_100g"],
                        "prot": item["prot_100g"],
                        "carb": item["carb_100g"],
                        "fat": item["fat_100g"]
                    },
                    "_embedding_vec": vec # Manter o vetor para uso futuro, se necessário
                }
                melhor_match = (item["refeicao"], item_formatado)
        except Exception as e:
            print(f"Erro ao processar embedding do item {item['id_item']}: {e}")
            
    if melhor_match and melhor_sim >= limiar:
        return melhor_match
        
    return None

# --- Lógica de Cálculos (Sem alteração) ---

def calcular_bmr(peso_kg: float, altura_cm: float, idade: int, sexo: str) -> float:
    s = sexo.lower()[0] if sexo else "f"
    if s in ("f", "m") and s == "f":
        return 10 * peso_kg + 6.25 * altura_cm - 5 * idade - 161
    else:
        return 10 * peso_kg + 6.25 * altura_cm - 5 * idade + 5

def calcular_tdee(bmr: float, atividade: str) -> float:
    fator = FATORES_ATIVIDADE.get(atividade, FATORES_ATIVIDADE["sedentario"])
    return bmr * fator

def recomendacao_agua_ml(peso_kg: float) -> float:
    return peso_kg * 35

def calcular_imc(peso_kg: float, altura_cm: float) -> Optional[float]:
    try:
        altura_m = float(altura_cm) / 100.0
        if altura_m <= 0:
            return None
        return peso_kg / (altura_m * altura_m)
    except Exception:
        return None

def classificar_imc(imc: float) -> str:
    if imc is None:
        return "IMC não calculável"
    if imc < 18.5:
        return "Magreza (IMC < 18.5)"
    if imc < 25:
        return "Normal (IMC 18.5–24.9)"
    if imc < 30:
        return "Sobrepeso (IMC 25–29.9)"
    return "Obesidade (IMC ≥ 30)"

# --- Lógica do Chatbot (Atualizada para SQLite) ---

def extrair_itens_e_gramas(frase: str) -> List[Tuple[str, float]]:
    frase = frase.lower()
    resultados = []
    matches = list(ITEM_GRAMA_PAIR_PATTERN.finditer(frase))
    if matches:
        for m in matches:
            nome = m.group(1).strip(" ,.;")
            grams_text = re.search(r'(\d+(?:[.,]\d+)?)', m.group(2))
            grams = float(grams_text.group(1).replace(",", ".")) if grams_text else 100.0
            resultados.append((nome, grams))
        return resultados
    tokens = re.split(r' e |,|;|\band\b', frase)
    for t in tokens:
        t = t.strip()
        mg = GRAMAS_PATTERN.search(t)
        if mg:
            grams = float(mg.group(1).replace(",", "."))
            nome = GRAMAS_PATTERN.sub('', t).strip()
            if nome:
                resultados.append((nome, grams))
    if not resultados:
        palavras = re.findall(r'[A-Za-zÀ-ú0-9]+', frase)
        if 'comi' in frase:
            idx = palavras.index('comi') if 'comi' in palavras else -1
            if idx >= 0 and idx + 1 < len(palavras):
                nome = ' '.join(palavras[idx+1: idx+4])
                resultados.append((nome, 100.0))
    return resultados

def registrar_consumo(id_cliente: str, refeicao: str, nome_item_usuario: str, gramas: float) -> Dict[str, Any]:
    cliente = get_cliente_por_id(id_cliente)
    if not cliente:
        raise ValueError("Cliente não encontrado")

    encontrado = _encontrar_item_por_nome_por_embedding(id_cliente, nome_item_usuario)
    if encontrado:
        refeicao_plano, item_plano = encontrado
        cal100 = item_plano["per_100g"]["cal"]
        kcal = cal100 * (gramas / 100.0)
        nome_final = item_plano["nome"]
    else:
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*(kcal|calorias|cal)', nome_item_usuario)
        if m:
            kcal = float(m.group(1).replace(",", "."))
            nome_final = nome_item_usuario
        else:
            kcal = gramas * 1.0 # Fallback
            nome_final = nome_item_usuario

    registro = {
        "data_hora": datetime.utcnow().isoformat(),
        "refeicao": refeicao,
        "nome_item": nome_final,
        "gramas": float(gramas),
        "kcal": float(kcal)
    }

    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO registros_consumo (id_cliente, data_hora, refeicao, nome_item, gramas, kcal) VALUES (?, ?, ?, ?, ?, ?)",
                (id_cliente, registro["data_hora"], registro["refeicao"], registro["nome_item"], registro["gramas"], registro["kcal"])
            )
            # Logar na conversa
            texto_log = f"registrei: {nome_final} {gramas}g no {refeicao}"
            db.execute(
                "INSERT INTO conversas (id_cliente, role, texto, time) VALUES (?, ?, ?, ?)",
                (id_cliente, "user", texto_log, datetime.utcnow().isoformat())
            )
        return registro
    except Exception as e:
        print(f"Erro ao registrar consumo: {e}")
        return None

def consumo_total_hoje(id_cliente: str) -> Tuple[float, List[Dict[str,Any]]]:
    hoje = date.today().isoformat()
    with get_db() as db:
        cursor = db.execute(
            "SELECT * FROM registros_consumo WHERE id_cliente = ? AND data_hora LIKE ?",
            (id_cliente, f"{hoje}%")
        )
        itens = [dict(row) for row in cursor.fetchall()]
        
    total = sum(r.get("kcal", 0.0) for r in itens)
    return total, itens

def _salvar_conversa(id_cliente: str, role: str, texto: str):
    """Função interna para logar conversas no DB."""
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO conversas (id_cliente, role, texto, time) VALUES (?, ?, ?, ?)",
                (id_cliente, role, texto, datetime.utcnow().isoformat())
            )
    except Exception as e:
        print(f"Erro ao salvar conversa: {e}")

def get_historico_conversa(id_cliente: str) -> List[Dict[str, Any]]:
    with get_db() as db:
        cursor = db.execute(
            "SELECT role, texto, time FROM conversas WHERE id_cliente = ? ORDER BY time ASC",
            (id_cliente,)
        )
        return [dict(row) for row in cursor.fetchall()]

def saudacoes_cliente(id_cliente: str) -> str:
    cliente = get_cliente_por_id(id_cliente)
    nome = cliente.get('nome','cliente') if cliente else 'cliente'
    resposta = f"Olá {nome}! Em que posso te ajudar hoje?"
    _salvar_conversa(id_cliente, "bot", resposta)
    return resposta

def recomendar_opcoes_refeicao(id_cliente: str, refeicao: str) -> str:
    plano = listar_plano(id_cliente)
    refeicao_key = refeicao.strip().lower()
    opcoes = plano.get(refeicao_key, [])
    
    if not opcoes:
        resposta = f"Não há opções cadastradas para '{refeicao_key}'. Peça para sua nutricionista cadastrar."
    else:
        linhas = [f"Opções para {refeicao_key} (valores por 100g):"]
        for it in opcoes:
            p = it["per_100g"]
            linhas.append(f"- {it['nome']}: {p['cal']:.0f} kcal / 100g; prot {p.get('prot',0)}g; carb {p.get('carb',0)}g; gordura {p.get('fat',0)}g.")
        resposta = "\n".join(linhas)

    _salvar_conversa(id_cliente, "bot", resposta.split('\n')[0]) # Salva só a primeira linha como resumo
    return resposta

def recomendar_para_restante(id_cliente: str, margem_kcal: float = 0.0) -> str:
    cliente = get_cliente_por_id(id_cliente)
    if not cliente:
        return "Cliente não encontrado."
    if not (cliente.get("peso_kg") and cliente.get("altura_cm") and cliente.get("idade")):
        return "Faltam dados (peso/altura/idade) para calcular sua meta calórica."

    bmr = calcular_bmr(cliente["peso_kg"], cliente["altura_cm"], cliente["idade"], cliente["sexo"])
    tdee = calcular_tdee(bmr, cliente.get("atividade", "sedentario"))
    consumido, itens = consumo_total_hoje(id_cliente)
    restante = tdee - consumido - margem_kcal
    
    if restante <= 0:
        resposta = f"Você já atingiu ou ultrapassou a meta diária (~{tdee:.0f} kcal). Consumido hoje: {consumido:.0f} kcal."
    else:
        plano = listar_plano(id_cliente)
        candidatos = []
        for refeicao, lista in plano.items():
            for item in lista:
                cal100 = item["per_100g"].get("cal", 0.0)
                if cal100 <= 0: continue
                maxg = (restante / cal100) * 100.0
                if maxg >= 20:
                    candidatos.append((item["nome"], cal100, int(maxg), refeicao))
        
        if not candidatos:
            resposta = f"Nenhuma opção do plano cabe nas ~{restante:.0f} kcal restantes. Considere porções menores."
        else:
            candidatos.sort(key=lambda x: -x[2])
            linhas = [f"Meta estimada: ~{tdee:.0f} kcal. Consumido hoje: {consumido:.0f} kcal. Restam ~{restante:.0f} kcal."]
            linhas.append("Sugestões que cabem no restante (porção máxima aproximada):")
            for nome, cal100, maxg, refeicao in candidatos[:10]:
                linhas.append(f"- {nome} ({refeicao}): {cal100:.0f} kcal/100g — até ~{maxg} g")
            resposta = "\n".join(linhas)

    _salvar_conversa(id_cliente, "bot", resposta.split('\n')[0])
    return resposta

def interpretar_intencao(pergunta: str) -> Tuple[Optional[str], float]:
    if MODELO_IA is None: return None, 0.0
    
    emb = MODELO_IA.encode(pergunta, convert_to_tensor=True)
    melhor = None
    melhor_sim = -1.0
    for chave, embs in INTENCOES_EMBED.items():
        sim = float(util.cos_sim(emb, embs).max())
        if sim > melhor_sim:
            melhor_sim = sim
            melhor = chave
    return melhor, melhor_sim

def ultima_resposta_contexto(id_cliente: str) -> Optional[Dict[str,Any]]:
    with get_db() as db:
        cursor = db.execute(
            "SELECT * FROM conversas WHERE id_cliente = ? AND role = 'bot' ORDER BY time DESC LIMIT 1",
            (id_cliente,)
        )
        ultima = cursor.fetchone()
        return dict(ultima) if ultima else None

def procurar_item_por_texto_no_plano(id_cliente: str, texto: str) -> Optional[Dict[str,Any]]:
    match_emb = _encontrar_item_por_nome_por_embedding(id_cliente, texto)
    if match_emb:
        return match_emb[1] # Retorna o dicionário do item

    # Fallback para substring
    plano = listar_plano(id_cliente)
    texto_norm = normalizar_texto(texto)
    for refeicao, itens in plano.items():
        for item in itens:
            if normalizar_texto(item["nome"]) in texto_norm:
                return item
    return None

def mostrar_informacoes_cliente(id_cliente: str) -> str:
    cliente = get_cliente_por_id(id_cliente)
    if not cliente:
        return "Cliente não encontrado."
    
    bmr = calcular_bmr(cliente["peso_kg"], cliente["altura_cm"], cliente["idade"], cliente["sexo"])
    tdee = calcular_tdee(bmr, cliente.get("atividade", "sedentario"))
    agua_ml = recomendacao_agua_ml(cliente["peso_kg"]) if cliente.get("peso_kg") else None
    consumo_hoje, itens = consumo_total_hoje(id_cliente)
    
    linhas = [
        f"Nome: {cliente['nome']}",
        f"Idade: {cliente['idade']} | Sexo: {cliente['sexo']}",
        f"Peso atual: {cliente['peso_kg']} kg | Altura: {cliente['altura_cm']} cm",
        f"BMR ≈ {bmr:.0f} kcal/dia | TDEE ≈ {tdee:.0f} kcal/dia (atividade: {cliente.get('atividade')})",
        f"Consumido hoje: {consumo_hoje:.0f} kcal ({len(itens)} registros)",
    ]
    if agua_ml:
        linhas.append(f"Água sugerida: ~{int(agua_ml)} ml/dia (~{agua_ml/1000:.2f} L).")
    
    resposta = "\n".join(linhas)
    # Não salvamos isso como uma resposta de "bot" para não poluir o contexto de perguntas
    return resposta

def gerar_relatorio_completo_cliente(id_cliente: str) -> str:
    """Gera um relatório completo legível com todas as informações relevantes do cliente."""
    cliente = get_cliente_por_id(id_cliente)
    if not cliente:
        return "Cliente não encontrado."

    peso = cliente.get("peso_kg")
    altura = cliente.get("altura_cm")
    idade = cliente.get("idade")
    sexo = cliente.get("sexo", "F")
    atividade = cliente.get("atividade", "sedentario")

    # Cálculos
    imc = calcular_imc(peso, altura) if peso and altura else None
    imc_txt = f"{imc:.2f}" if imc else "—"
    imc_class = classificar_imc(imc)
    
    agua_txt = "—"
    if peso:
        ml = recomendacao_agua_ml(peso)
        agua_txt = f"~{int(ml)} ml/dia (~{ml/1000:.2f} L)"

    bmr_txt = "—"
    tdee_txt = "—"
    if peso and altura and idade:
        try:
            bmr = calcular_bmr(peso, altura, int(idade), sexo)
            tdee = calcular_tdee(bmr, atividade)
            bmr_txt = f"{bmr:.0f} kcal/dia"
            tdee_txt = f"{tdee:.0f} kcal/dia (atividade: {atividade})"
        except Exception:
            pass
    
    plano = listar_plano(id_cliente)
    consumo_hoje_total, ultimos_registros = consumo_total_hoje(id_cliente)
    conversas = get_historico_conversa(id_cliente)[-10:] # Pega as últimas 10

    linhas = [
        "=== RELATÓRIO COMPLETO DO CLIENTE ===",
        f"Nome: {cliente.get('nome', '—')}",
        f"Idade: {idade} | Sexo: {sexo}",
        f"Peso atual: {peso if peso else '—'} kg | Altura: {altura if altura else '—'} cm",
        f"Peso inicial: {cliente.get('peso_inicial', '—')} | Meta: {cliente.get('meta', '—')}",
        f"IMC: {imc_txt} — {imc_class}",
        f"Água recomendada: {agua_txt}",
        f"BMR: {bmr_txt} | TDEE: {tdee_txt}",
        f"Consumido hoje: {consumo_hoje_total:.1f} kcal ({len(ultimos_registros)} registros)"
    ]

    linhas.append("\n--- Resumo do plano alimentar ---")
    if not plano:
        linhas.append("Plano vazio.")
    else:
        for refeicao, itens in plano.items():
            linhas.append(f"- {refeicao}: {len(itens)} opções")
            if itens:
                first = itens[0]
                p = first.get("per_100g", {})
                linhas.append(f"  • Exemplo {refeicao}: {first.get('nome')} — {p.get('cal',0)} kcal/100g")

    linhas.append("\n--- Registros de consumo (hoje) ---")
    if not ultimos_registros:
        linhas.append("Sem registros de consumo hoje.")
    else:
        for r in ultimos_registros:
            linhas.append(f"* {r.get('data_hora')} | {r.get('refeicao')} | {r.get('nome_item')} {r.get('gramas')}g → {r.get('kcal'):.1f} kcal")

    linhas.append("\n--- Últimas mensagens (histórico) ---")
    if not conversas:
        linhas.append("Sem histórico de conversas.")
    else:
        for c in conversas:
            linhas.append(f"[{c.get('time')}] {c.get('role')}: {c.get('texto')}")

    return "\n".join(linhas)


def responder_pergunta(id_cliente: str, texto: str) -> str:
    """Função principal do chatbot, agora sem I/O direto."""
    
    # Salva a pergunta do usuário no histórico
    _salvar_conversa(id_cliente, "user", texto)
    
    texto_lower = texto.lower().strip()
    
    # --- Gatilhos e Intenções ---
    
    # 1. Gatilhos por Regra Fixa (Regex)
    if re.search(r'(forne(c|ç)a|me dê|me de|me mande|)\s+(todas as informa(c|ç)oes|meu resumo|meu relatório)', texto_lower):
        resposta = gerar_relatorio_completo_cliente(id_cliente)
        _salvar_conversa(id_cliente, "bot", "Gerando relatório completo...") # Log simples
        return resposta

    m_peso = re.search(r'\b(?:meu\s+)?peso\s*(?:é|=)?\s*(\d+(?:[.,]\d+)?)\s*(kg)?\b', texto_lower)
    if m_peso:
        peso_novo = float(m_peso.group(1).replace(",", "."))
        if atualizar_cliente(id_cliente, {"peso_kg": peso_novo}):
            resposta = f"Peso atualizado para {peso_novo:.1f} kg. Agora posso calcular sua água e calorias com esse valor."
        else:
            resposta = "Erro ao atualizar peso. Peça para a nutricionista atualizar manualmente."
        _salvar_conversa(id_cliente, "bot", resposta)
        return resposta

    if any(w in texto_lower for w in ["água", "agua", "quanta água", "quanta agua"]):
        cliente = get_cliente_por_id(id_cliente)
        if cliente and cliente.get("peso_kg"):
            ml = recomendacao_agua_ml(cliente["peso_kg"])
            resposta = f"Sugestão de ingestão de água: ~{int(ml)} ml/dia (~{ml/1000:.2f} L)."
        else:
            resposta = "Não tenho seu peso cadastrado. Peça para a nutricionista cadastrar ou escreva 'Meu peso 72kg' para atualizar."
        _salvar_conversa(id_cliente, "bot", resposta)
        return resposta

    # 2. Interpretação por IA (Embeddings)
    chave_intencao, sim = interpretar_intencao(texto_lower)
    
    if chave_intencao == "saudacoes" and sim > 0.5:
        return saudacoes_cliente(id_cliente) # Função já salva a resposta
    if chave_intencao == "perguntar_opcoes_cafe" and sim > 0.5:
        return recomendar_opcoes_refeicao(id_cliente, "cafe da manha") # Função já salva a resposta
    if chave_intencao == "perguntar_opcoes_almoco" and sim > 0.5:
        return recomendar_opcoes_refeicao(id_cliente, "almoco") # Função já salva a resposta
    if chave_intencao == "perguntar_opcoes_janta" and sim > 0.5:
        return recomendar_opcoes_refeicao(id_cliente, "janta") # Função já salva a resposta
    if chave_intencao == "calorias_disponiveis" and sim > 0.5:
        return recomendar_para_restante(id_cliente) # Função já salva a resposta
    if chave_intencao == "mostrar_info" and sim > 0.5:
        resposta = mostrar_informacoes_cliente(id_cliente)
        _salvar_conversa(id_cliente, "bot", resposta) # Salva manualmente
        return resposta

    # 3. Registro de Consumo
    if "comi" in texto_lower or "comemos" in texto_lower or "comeu" in texto_lower:
        refeicao_encontrada = "refeicao" # default
        for mk in MEAL_KEYS:
            if mk in texto_lower:
                refeicao_encontrada = mk
                break
        
        pares = extrair_itens_e_gramas(texto_lower)
        if not pares:
            resposta = "Não entendi o que você comeu. Exemplos: 'Comi arroz 200g no almoço'."
        else:
            mensagens = []
            for nome_item, gramas in pares:
                registro = registrar_consumo(id_cliente, refeicao_encontrada, nome_item, gramas)
                if registro:
                    mensagens.append(f"Registrado: {registro['nome_item']} {registro['gramas']}g → {registro['kcal']:.1f} kcal")
            resposta = "\n".join(mensagens)
        
        _salvar_conversa(id_cliente, "bot", resposta)
        return resposta

    # 4. Pergunta de Contexto (Calorias)
    if any(k in texto_lower for k in ["quanto isso", "quantas calorias", "quantas kcal", "quanto tem"]):
        ultima = ultima_resposta_contexto(id_cliente)
        if not ultima:
            resposta = "Não achei referência anterior clara."
        else:
            texto_bot = ultima.get("texto", "")
            m = re.search(r'(\d+(?:[.,]\d+)?)\s*kcal', texto_bot)
            if m:
                resposta = f"A resposta anterior indica ~{float(m.group(1))} kcal."
            else:
                resposta = "Não consegui inferir as calorias da mensagem anterior."
        
        _salvar_conversa(id_cliente, "bot", resposta)
        return resposta

    # 5. Fallback: Procurar item no plano
    match = procurar_item_por_texto_no_plano(id_cliente, texto_lower)
    if match:
        p = match["per_100g"]
        resposta = f"{match['nome']}: {p['cal']:.0f} kcal / 100g; prot {p.get('prot',0)}g; carb {p.get('carb',0)}g; gordura {p.get('fat',0)}g."
    else:
        # 6. Resposta Padrão (Não entendeu)
        resposta = "Desculpe, não entendi. Tente: 'O que eu posso comer?', 'Comi arroz 200g', ou 'Quantas calorias restam?'."
    
    _salvar_conversa(id_cliente, "bot", resposta)
    return resposta

# --- Novas Funções para a API ---

def buscar_alimento_base_dados(nome_alimento: str) -> List[Dict[str, Any]]:
    """Procura alimentos na base de dados (DF_ALIMENTOS) para o nutri."""
    if DF_ALIMENTOS is None:
        return []

    nome_alimento = nome_alimento.lower().strip()
    opcoes = DF_ALIMENTOS["descricao_alimento_norm"].tolist()
    
    # Usar 'extract' para pegar os 5 melhores, não apenas 'extractOne'
    resultados = process.extract(nome_alimento, opcoes, score_cutoff=60, limit=5)
    
    matches = []
    if resultados:
        for melhor, score, idx in resultados:
            alimento = DF_ALIMENTOS.iloc[idx].to_dict()
            # Limpar NaNs (que não são JSON serializáveis)
            alimento_limpo = {k: (v if pd.notna(v) else None) for k, v in alimento.items()}
            alimento_limpo['score'] = score # Adiciona o score
            matches.append(alimento_limpo)
            
    return matches
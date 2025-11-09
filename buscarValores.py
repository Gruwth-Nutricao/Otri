import pandas as pd
from rapidfuzz import process
from unidecode import unidecode


df = pd.read_excel(r"base-comidas-tratada.xlsx", sheet_name="basona")
df["descricao_alimento_norm"] = df["descricao_alimento"].str.lower().str.strip().apply(lambda x: unidecode(x))

def buscar_alimento(nome_alimento, quantidade=None, limite_similaridade=50):
    nome_alimento = nome_alimento.lower().strip()
    opcoes = df["descricao_alimento_norm"].tolist()
    resultado = process.extractOne(nome_alimento, opcoes, score_cutoff=limite_similaridade)
    
    if resultado:
        melhor, score, idx = resultado
        alimento = df.iloc[idx].to_dict()
        if quantidade:
            fator = quantidade / 100
            return {
                "descricao_alimento": alimento["descricao_alimento"],
                "quantidade_recomendada_g": quantidade,
                "energia_kcal": round(float(alimento["energia_kcal"]) * fator, 2),
                "proteina_g": round(float(alimento["proteina_g"]) * fator, 2),
                "carboidrato_g": round(float(alimento["carboidrato_g"]) * fator, 2),
                "lipideo_g": round(float(alimento["lipideo_g"]) * fator, 2)
            }
        return alimento
    else:
        print(f"Alimento '{nome_alimento}' não encontrado na base.")
        energia = float(input("Digite as calorias (kcal) por 100g: "))
        proteina = float(input("Digite as proteínas (g) por 100g: "))
        carb = float(input("Digite os carboidratos (g) por 100g: "))
        gordura = float(input("Digite as gorduras (g) por 100g: "))
        if quantidade:
            fator = quantidade / 100
            return {
                "descricao_alimento": nome_alimento,
                "quantidade_recomendada_g": quantidade,
                "energia_kcal": energia * fator,
                "proteina_g": proteina * fator,
                "carboidrato_g": carb * fator,
                "lipideo_g": gordura * fator
            }
        return {
            "descricao_alimento": nome_alimento,
            "energia_kcal": energia,
            "proteina_g": proteina,
            "carboidrato_g": carb,
            "lipideo_g": gordura
        }

def main():
    print("=== Sistema de Busca de Alimentos ===")
    print("Digite 'sair' para encerrar.")
    while True:
        alimento = input("\nDigite o nome do alimento: ")
        if alimento.lower() == "sair":
            break
        quantidade = input("Digite a quantidade recomendada em gramas: ")
        try:
            quantidade = float(quantidade)
        except:
            print("Quantidade inválida. Digite um número.")
            continue
        resultado = buscar_alimento(alimento, quantidade)
        print("\nResultado encontrado:")
        for k, v in resultado.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()

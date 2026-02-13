import sqlite3
import pandas as pd

DB = r"data\processed\imoveis_rurais.sqlite"

def q(sql: str, params=()):
    conn = sqlite3.connect(DB)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

print("\n1) Colunas da tabela enriquecida (amostra):")
print(q("SELECT * FROM imoveis_enriquecido LIMIT 1;").columns.tolist())

print("\n2) MF faltando (deve ser vazio):")
print(q("""
SELECT municipio, COUNT(*) qtd
FROM imoveis_enriquecido
WHERE mf_ha IS NULL
GROUP BY municipio
ORDER BY qtd DESC;
"""))

print("\n3) Distribuição por classe:")
print(q("""
SELECT classe_tamanho, COUNT(*) qtd
FROM imoveis_enriquecido
GROUP BY classe_tamanho
ORDER BY qtd DESC;
"""))

print("\n4) Amostra com cálculo MF:")
print(q("""
SELECT municipio, area_total_ha, mf_ha, area_em_mf, classe_tamanho
FROM imoveis_enriquecido
LIMIT 20;
"""))

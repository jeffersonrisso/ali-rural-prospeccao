from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

# Ajuste se sua estrutura for diferente:
BASE_DIR = Path(__file__).resolve().parents[2]  # src/etl -> raiz do projeto
DB_PATH = BASE_DIR / "data" / "processed" / "imoveis_rurais.sqlite"
REF_PATH = BASE_DIR / "data" / "reference" / "modulo_fiscal_er_jundiai.csv"


def classificar_por_mf(area_em_mf: float | None) -> str:
    if area_em_mf is None or pd.isna(area_em_mf):
        return "Sem MF"
    if area_em_mf <= 4:
        return "Pequena (<=4 MF)"
    if area_em_mf <= 15:
        return "Média (4–15 MF)"
    return "Grande (>15 MF)"


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"SQLite não encontrado: {DB_PATH}")
    if not REF_PATH.exists():
        raise FileNotFoundError(f"Referência MF não encontrada: {REF_PATH}")

    conn = sqlite3.connect(str(DB_PATH))

    try:
        im = pd.read_sql_query("SELECT * FROM imoveis;", conn)
        ref = pd.read_csv(REF_PATH, dtype={"municipio_norm": "string"})

        # Join usando municipio_norm (você já tem no banco)
        df = im.merge(ref[["municipio_norm", "mf_ha"]], on="municipio_norm", how="left")

        # Cálculos
        df["mf_ha"] = pd.to_numeric(df["mf_ha"], errors="coerce")
        df["area_em_mf"] = df["area_total_ha"] / df["mf_ha"]
        df["classe_tamanho"] = df["area_em_mf"].apply(classificar_por_mf)

        # Salva tabela enriquecida (sem mexer na original)
        df.to_sql("imoveis_enriquecido", conn, if_exists="replace", index=False)

        cur = conn.cursor()
        cur.execute("CREATE INDEX IF NOT EXISTS idx_enr_municipio ON imoveis_enriquecido (municipio);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_enr_area_mf ON imoveis_enriquecido (area_em_mf);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_enr_classe ON imoveis_enriquecido (classe_tamanho);")
        conn.commit()

        print("✅ Tabela criada/atualizada: imoveis_enriquecido")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

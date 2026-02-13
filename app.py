# app.py
# 🌾 ALI Rural — Prospecção de Propriedades (CAFIR) + Módulo Fiscal
# V1.2 (enriquecido com mf_ha, area_em_mf, classe_tamanho)

from __future__ import annotations

import sqlite3
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# =========================
# Caminhos (corrigido para sua estrutura real)
# =========================
BASE_DIR = Path(__file__).resolve().parent  # ALI_RURAL_PROSPECCAO/
DB_PATH = BASE_DIR / "data" / "processed" / "imoveis_rurais.sqlite"

# Metadados (opcional)
FONTE = "Dados Abertos CAFIR (RFB) + Enriquecimento por Módulo Fiscal (INCRA)"
REGIAO = "ER Jundiaí/SP (ALI Rural)"
DATA_BASE_TEXTO = "Imoveis_SP_01_02_2026.csv (origem) + modulo_fiscal_er_jundiai.csv (ref.)"

# =========================
# Streamlit config
# =========================
st.set_page_config(
    page_title="ALI Rural • Prospecção (CAFIR + MF)",
    layout="wide",
)

st.title("🌾 ALI Rural — Prospecção de Propriedades (CAFIR + Módulo Fiscal)")
st.caption(f"{REGIAO} • Fonte: {FONTE}")

# =========================
# Helpers
# =========================
def _connect() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH))

@st.cache_data(show_spinner=False)
def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = _connect()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

def df_to_excel(df: pd.DataFrame, sheet_name: str = "dados") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()

def fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")

def fmt_float(x: float | int | None, dec: int = 1) -> str:
    if x is None or pd.isna(x):
        return "-"
    s = f"{float(x):,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def table_exists(table_name: str) -> bool:
    df = run_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,),
    )
    return not df.empty

def clipboard_button(text: str, label: str):
    """
    Botão HTML/JS para copiar texto para a área de transferência do navegador.
    Funciona no Streamlit Web/Desktop.
    """
    safe = (
        str(text)
        .replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("$", "\\$")
        .replace("\r\n", "\n")
        .replace("\n", "\\n")
    )

    components.html(
        f"""
        <button style="
            width: 100%;
            padding: 10px 14px;
            border-radius: 10px;
            border: 1px solid #ddd;
            cursor: pointer;
            background: #fff;
            font-size: 14px;
        " onclick="navigator.clipboard.writeText(`{safe}`)">
            {label}
        </button>
        """,
        height=55,
    )

# =========================
# Verificação do DB
# =========================
if not DB_PATH.exists():
    st.error(
        "Banco SQLite não encontrado.\n\n"
        f"Esperado em:\n{DB_PATH}\n\n"
        "Confirme se o arquivo foi gerado no ETL."
    )
    st.stop()

# =========================
# Seleção da tabela base (fallback)
# =========================
TBL = "imoveis_enriquecido" if table_exists("imoveis_enriquecido") else "imoveis"
HAS_ENRICH = TBL == "imoveis_enriquecido"

if HAS_ENRICH:
    st.success("✅ Enriquecimento ativo: Módulo Fiscal (mf_ha), Área em MF (area_em_mf) e Classe (classe_tamanho).")
else:
    st.warning("ℹ️ Enriquecimento não encontrado. Usando tabela base `imoveis`.")

# =========================
# Layout: Tabs
# =========================
tabs = st.tabs(["📊 Dashboard", "🔎 Prospecção", "🏆 Ranking", "📦 Sobre a base"])

# =====================================================
# TAB 1 — DASHBOARD
# =====================================================
with tabs[0]:
    st.subheader("Visão geral")

    if HAS_ENRICH:
        df_stats = run_query(f"""
            SELECT
              COUNT(*) AS qtd,
              AVG(area_total_ha) AS area_media,
              AVG(area_em_mf) AS mf_media,
              MIN(area_total_ha) AS area_min,
              MAX(area_total_ha) AS area_max
            FROM {TBL};
        """)
        qtd = int(df_stats.loc[0, "qtd"])
        area_media = df_stats.loc[0, "area_media"]
        mf_media = df_stats.loc[0, "mf_media"]
        area_min = df_stats.loc[0, "area_min"]
        area_max = df_stats.loc[0, "area_max"]

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Imóveis", fmt_int(qtd))
        c2.metric("Área média (ha)", fmt_float(area_media, 1))
        c3.metric("Área média (MF)", fmt_float(mf_media, 2))
        c4.metric("Menor área (ha)", fmt_float(area_min, 1))
        c5.metric("Maior área (ha)", fmt_float(area_max, 1))
    else:
        df_stats = run_query(f"""
            SELECT
              COUNT(*) AS qtd,
              AVG(area_total_ha) AS area_media,
              MIN(area_total_ha) AS area_min,
              MAX(area_total_ha) AS area_max
            FROM {TBL};
        """)
        qtd = int(df_stats.loc[0, "qtd"])
        area_media = df_stats.loc[0, "area_media"]
        area_min = df_stats.loc[0, "area_min"]
        area_max = df_stats.loc[0, "area_max"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Imóveis", fmt_int(qtd))
        c2.metric("Área média (ha)", fmt_float(area_media, 1))
        c3.metric("Menor área (ha)", fmt_float(area_min, 1))
        c4.metric("Maior área (ha)", fmt_float(area_max, 1))

    colA, colB = st.columns([1, 1])

    with colA:
        st.markdown("#### Imóveis por município (Top 15)")
        df_mun = run_query(f"""
            SELECT municipio, COUNT(*) AS qtd
            FROM {TBL}
            GROUP BY municipio
            ORDER BY qtd DESC
            LIMIT 15;
        """)
        st.bar_chart(df_mun.set_index("municipio"))

    with colB:
        if HAS_ENRICH:
            st.markdown("#### Classes por Módulo Fiscal")
            df_cls = run_query(f"""
                SELECT classe_tamanho, COUNT(*) AS qtd
                FROM {TBL}
                GROUP BY classe_tamanho
                ORDER BY qtd DESC;
            """)
            st.bar_chart(df_cls.set_index("classe_tamanho"))
        else:
            st.markdown("#### Condição da pessoa (PF x PJ)")
            df_pf_pj = run_query(f"""
                SELECT condicao_pessoa, COUNT(*) AS qtd
                FROM {TBL}
                GROUP BY condicao_pessoa
                ORDER BY qtd DESC;
            """)
            st.bar_chart(df_pf_pj.set_index("condicao_pessoa"))

    st.markdown("#### Natureza jurídica (Top 15)")
    df_nat = run_query(f"""
        SELECT natureza_juridica, COUNT(*) AS qtd
        FROM {TBL}
        GROUP BY natureza_juridica
        ORDER BY qtd DESC
        LIMIT 15;
    """)
    st.dataframe(df_nat, use_container_width=True, hide_index=True)


# =====================================================
# TAB 2 — PROSPECÇÃO
# =====================================================

with tabs[1]:
    st.subheader("Filtros de prospecção")

    municipios = run_query(f"SELECT DISTINCT municipio FROM {TBL} ORDER BY municipio;")["municipio"].tolist()

    c1, c2, c3, c4 = st.columns(4)
    municipio = c1.selectbox("Município", ["Todos"] + municipios)
    condicao = c2.selectbox("Condição (PF/PJ)", ["Todas", "Física", "Jurídica"])
    area_min, area_max = c3.slider("Área total (ha)", 0.0, 5000.0, (0.0, 200.0), step=1.0)
    pct_min = c4.slider("% detenção mínima", 0.0, 100.0, 0.0, step=1.0)

    c5, c6 = st.columns(2)
    busca = c5.text_input("Busca (código do imóvel / denominação / titular)").strip()
    natureza = c6.text_input("Natureza jurídica (contém)").strip()

    # Filtros MF (somente se enriquecido)
    if HAS_ENRICH:
        c7, c8 = st.columns(2)
        classe = c7.selectbox(
            "Classe por módulo fiscal",
            ["Todas", "Pequena (<=4 MF)", "Média (4–15 MF)", "Grande (>15 MF)", "Sem MF"],
            index=0
        )
        area_mf_min, area_mf_max = c8.slider(
            "Área em módulos fiscais (MF)",
            0.0, 100.0, (0.0, 10.0), step=0.5
        )

    # WHERE
    where: list[str] = []
    params: list = []

    where.append("uf = ?")
    params.append("SP")

    where.append("area_total_ha BETWEEN ? AND ?")
    params.extend([area_min, area_max])

    where.append("percentual_detencao >= ?")
    params.append(float(pct_min))

    if municipio != "Todos":
        where.append("municipio = ?")
        params.append(municipio)

    if condicao != "Todas":
        where.append("condicao_pessoa = ?")
        params.append(condicao)

    if natureza:
        where.append("UPPER(natureza_juridica) LIKE ?")
        params.append(f"%{natureza.upper()}%")

    if busca:
        b = busca
        b_norm = busca.upper()
        where.append("""
        (
            codigo_imovel LIKE ?
            OR denominacao_norm LIKE ?
            OR titular_norm LIKE ?
        )
        """)
        params.extend([f"%{b}%", f"%{b_norm}%", f"%{b_norm}%"])

    if HAS_ENRICH:
        if classe != "Todas":
            where.append("classe_tamanho = ?")
            params.append(classe)

        where.append("area_em_mf BETWEEN ? AND ?")
        params.extend([area_mf_min, area_mf_max])

    where_sql = "WHERE " + " AND ".join([w.strip() for w in where]) if where else ""

    # paginação
    pg1, pg2, pg3, pg4 = st.columns([1, 1, 1, 2])
    page_size = pg1.selectbox("Linhas por página", [50, 100, 200, 500], index=1)
    page = pg2.number_input("Página", min_value=1, value=1, step=1)
    offset = (page - 1) * page_size
    show_adv = pg3.checkbox("Mostrar campos técnicos", value=True if HAS_ENRICH else False)

    total = int(run_query(f"SELECT COUNT(*) AS n FROM {TBL} {where_sql};", tuple(params)).iloc[0]["n"])
    pg4.info(f"Encontrados: {fmt_int(total)}")

    # SELECT cols
    base_cols = """
      codigo_imovel,
      denominacao,
      municipio,
      uf,
      area_total_ha,
      percentual_detencao,
      condicao_pessoa,
      natureza_juridica,
      titular,
      pais
    """
    adv_cols = "ibge_municipio"
    mf_cols = "mf_ha, area_em_mf, classe_tamanho" if HAS_ENRICH else ""

    cols_sql = base_cols
    extra_cols = []
    if show_adv:
        extra_cols.append(adv_cols)
    if HAS_ENRICH and show_adv:
        extra_cols.append(mf_cols)

    if extra_cols:
        cols_sql = cols_sql + ", " + ", ".join(extra_cols)

    sql = f"""
    SELECT {cols_sql}
    FROM {TBL}
    {where_sql}
    ORDER BY {"area_em_mf DESC, area_total_ha DESC" if HAS_ENRICH else "area_total_ha DESC"}
    LIMIT ? OFFSET ?;
    """
    df = run_query(sql, tuple(params + [page_size, offset]))
    st.dataframe(df, use_container_width=True, hide_index=True)

    b1, b2 = st.columns(2)
    b1.download_button(
        "⬇️ Excel (página atual)",
        df_to_excel(df, "prospeccao_pagina"),
        file_name="prospeccao_ali_rural_pagina.xlsx",
        use_container_width=True
    )

    export_limit = 200_000
    can_export_all = total <= export_limit
    if not can_export_all:
        b2.warning(f"Exportação total limitada a {fmt_int(export_limit)} linhas por segurança.")

    if b2.button("Gerar Excel (todos filtrados)", disabled=not can_export_all):
        df_all = run_query(
            f"""
            SELECT {cols_sql}
            FROM {TBL}
            {where_sql}
            ORDER BY {"area_em_mf DESC, area_total_ha DESC" if HAS_ENRICH else "area_total_ha DESC"};
            """,
            tuple(params),
        )
        st.download_button(
            "⬇️ Baixar Excel (todos filtrados)",
            df_to_excel(df_all, "prospeccao_filtrada"),
            file_name="prospeccao_ali_rural_todos_filtrados.xlsx",
            use_container_width=True
        )

    # --------- DETALHE + COPIAR ---------
    st.divider()
    st.subheader("📄 Detalhe do imóvel (por código)")

    codigo = st.text_input("Digite o código do imóvel (codigo_imovel)").strip()

    if codigo:
        det_cols = """
          codigo_imovel,
          denominacao,
          ibge_municipio,
          municipio,
          uf,
          area_total_ha,
          titular,
          natureza_juridica,
          condicao_pessoa,
          percentual_detencao,
          pais
        """
        if HAS_ENRICH:
            det_cols += ", mf_ha, area_em_mf, classe_tamanho"

        det = run_query(f"""
            SELECT {det_cols}
            FROM {TBL}
            WHERE codigo_imovel = ?;
        """, (codigo,))

        if det.empty:
            st.warning("Código não encontrado.")
        else:
            st.dataframe(det, use_container_width=True, hide_index=True)

            row = det.iloc[0].to_dict()

            linha1 = f"🏡 Imóvel CAFIR • Código: {row.get('codigo_imovel', '-')}"
            linha2 = f"📍 {row.get('municipio', '-')}/{row.get('uf', '-')}"
            linha3 = (
                f"📐 Área: {fmt_float(row.get('area_total_ha'), 2)} ha"
                f" • Detenção: {fmt_float(row.get('percentual_detencao'), 1)}%"
            )

            if HAS_ENRICH:
                linha_mf = (
                    f"📏 Módulo Fiscal: {fmt_float(row.get('mf_ha'), 0)} ha"
                    f" • Área em MF: {fmt_float(row.get('area_em_mf'), 2)}"
                    f" • Classe: {row.get('classe_tamanho', '-')}"
                )
            else:
                linha_mf = None

            linha4 = f"👤 Titular: {row.get('titular', '-')}"
            linha5 = f"🧾 Condição: {row.get('condicao_pessoa', '-')}"
            linha6 = f"🏛️ Natureza: {row.get('natureza_juridica', '-')}"
            linha7 = f"🌍 País: {row.get('pais', '-')}"

            linhas = [linha1, linha2, linha3]
            if linha_mf:
                linhas.append(linha_mf)
            linhas += [linha4, linha5, linha6, linha7]

            resumo_completo = "\n".join(linhas)

            resumo_curto = (
                f"{row.get('codigo_imovel','-')} • "
                f"{row.get('municipio','-')}/{row.get('uf','-')} • "
                f"{fmt_float(row.get('area_total_ha'),2)} ha • "
                f"{row.get('titular','-')}"
            )

            st.markdown("#### 📄 Resumo pronto para copiar")
            st.text_area("Resumo completo", resumo_completo, height=190)

            cbtn1, cbtn2 = st.columns(2)
            with cbtn1:
                clipboard_button(resumo_completo, "📋 Copiar resumo completo")
            with cbtn2:
                clipboard_button(resumo_curto, "📋 Copiar versão curta")

            st.caption("Dica: cole direto no WhatsApp, e-mail ou planilha de controle do atendimento.")

# =====================================================
# TAB 3 — RANKING
# =====================================================

with tabs[2]:
    st.subheader("Rankings úteis para priorização")

    r1, r2, r3 = st.columns(3)
    top_n = r1.selectbox("Top N", [50, 100, 200], index=1)

    if HAS_ENRICH:
        ranking_tipo = r2.selectbox("Tipo de ranking", ["Maior área em MF (recomendado)", "Maior área (ha)", "Maior % detenção", "Área x % (aprox.)"])
    else:
        ranking_tipo = r2.selectbox("Tipo de ranking", ["Maior área (ha)", "Maior % detenção", "Área x % (aprox.)"])

    municipios = run_query(f"SELECT DISTINCT municipio FROM {TBL} ORDER BY municipio;")["municipio"].tolist()
    municipio_rank = r3.selectbox("Filtrar município", ["Todos"] + municipios)

    where = ["uf = ?"]
    params = ["SP"]
    if municipio_rank != "Todos":
        where.append("municipio = ?")
        params.append(municipio_rank)
    where_sql = "WHERE " + " AND ".join(where)

    select_extra = ""
    if HAS_ENRICH and ranking_tipo == "Maior área em MF (recomendado)":
        order_sql = "ORDER BY area_em_mf DESC, area_total_ha DESC"
        select_extra = ", mf_ha, area_em_mf, classe_tamanho"
    elif ranking_tipo == "Maior área (ha)":
        order_sql = "ORDER BY area_total_ha DESC"
    elif ranking_tipo == "Maior % detenção":
        order_sql = "ORDER BY percentual_detencao DESC, area_total_ha DESC"
    else:
        select_extra = ", (area_total_ha * (percentual_detencao / 100.0)) AS area_ponderada_ha"
        order_sql = "ORDER BY area_ponderada_ha DESC, area_total_ha DESC"

    df_rank = run_query(
        f"""
        SELECT
          codigo_imovel,
          denominacao,
          municipio,
          uf,
          area_total_ha,
          percentual_detencao
          {select_extra},
          condicao_pessoa,
          natureza_juridica,
          titular
        FROM {TBL}
        {where_sql}
        {order_sql}
        LIMIT ?;
        """,
        tuple(params + [top_n]),
    )

    st.dataframe(df_rank, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇️ Excel (ranking)",
        df_to_excel(df_rank, "ranking"),
        file_name="ranking_ali_rural.xlsx",
        use_container_width=True
    )


# =====================================================
# TAB 4 — SOBRE A BASE
# =====================================================
with tabs[3]:
    st.subheader("Informações da base e transparência")

    c1, c2 = st.columns(2)
    c1.write(f"**Fonte:** {FONTE}")
    c1.write(f"**Região atendida:** {REGIAO}")
    c1.write(f"**Arquivo de origem:** {DATA_BASE_TEXTO}")
    c2.write(f"**Banco:** {DB_PATH}")
    c2.write(f"**Gerado em:** {datetime.fromtimestamp(DB_PATH.stat().st_mtime).strftime('%d/%m/%Y %H:%M')}")

    st.markdown(f"#### Tabela em uso: `{TBL}`")
    if HAS_ENRICH:
        st.success("Esta tabela inclui colunas: mf_ha, area_em_mf, classe_tamanho.")

    st.markdown("#### Colunas disponíveis")
    df_cols = run_query(f"PRAGMA table_info({TBL});")
    st.dataframe(df_cols[["name", "type"]], use_container_width=True, hide_index=True)

    st.markdown("#### Observação importante")
    st.info(
        "Nesta extração atual do CAFIR, **não há CPF/CNPJ** como coluna disponível. "
        "Se você obtiver uma nova base (ou integrar outra fonte) com documentos/contatos/endereço, "
        "basta atualizar o ETL/enriquecimento e refletir no app."
    )

    st.markdown("#### Recomendações LGPD (uso responsável)")
    st.markdown(
        "- Use apenas os campos necessários para a finalidade do ALI Rural.\n"
        "- Evite exportar e compartilhar bases completas sem necessidade.\n"
        "- Mantenha registro interno da origem (fonte pública) e da finalidade.\n"
    )

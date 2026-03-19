#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_experiment.py
=====================
Análise completa dos resultados do experimento de dissertação.

Lê o CSV gerado por run_all.py (15 linhas: 5 instâncias × 3 cenários) e produz:

  1. Validação de completude dos dados
  2. Tabela geral do experimento (Tabela Mestra)
  3. RQ1 — Impacto do bem-estar no custo (A vs B)
  4. RQ2 — Comparação de desempenho MILP vs GA (B vs C)
  5. Análise de escalabilidade
  6. Análise de violações de BE
  7. Testes estatísticos (Wilcoxon signed-rank)
  8. Gráficos de alta qualidade (PNG + PDF)
  9. Tabelas LaTeX para a dissertação

Uso:
  python scripts/analyze_experiment.py
  python scripts/analyze_experiment.py --input data/results/experiment_metrics.csv
"""

import argparse
import os
import sys
import warnings
import textwrap
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Dependências opcionais
# ------------------------------------------------------------------
try:
    from scipy.stats import wilcoxon
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    warnings.warn("scipy não instalado — testes de Wilcoxon desabilitados.")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    plt.rcParams.update({
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    warnings.warn("matplotlib não instalado — gráficos desabilitados.")


# ------------------------------------------------------------------
# Constantes
# ------------------------------------------------------------------
INSTANCE_ORDER = ["I1_SMALL", "I2_LARGE_05X", "I3_LARGE", "I4_LARGE_15X", "I5_LARGE_25X"]
INSTANCE_LABELS = {
    "I1_SMALL":      "I1 (220×60)",
    "I2_LARGE_05X":  "I2 (600×160)",
    "I3_LARGE":      "I3 (1200×320)",
    "I4_LARGE_15X":  "I4 (1800×480)",
    "I5_LARGE_25X":  "I5 (3000×800)",
}
INSTANCE_SIZES = {
    "I1_SMALL":      (220, 60),
    "I2_LARGE_05X":  (600, 160),
    "I3_LARGE":      (1200, 320),
    "I4_LARGE_15X":  (1800, 480),
    "I5_LARGE_25X":  (3000, 800),
}
SCENARIO_LABELS = {
    "A_GA_noBE": "GA s/ BE",
    "B_GA_BE":   "GA c/ BE",
    "C_MILP_BE": "MILP c/ BE",
}
SCENARIOS = ["C_MILP_BE", "A_GA_noBE", "B_GA_BE"]

# Cores consistentes
COLORS = {
    "A_GA_noBE": "#2196F3",   # azul
    "B_GA_BE":   "#4CAF50",   # verde
    "C_MILP_BE": "#9C27B0",   # roxo
}


# ====================================================================
# 1. CARREGAMENTO E VALIDAÇÃO
# ====================================================================

def load_and_validate(csv_path: str) -> pd.DataFrame:
    """Carrega e valida o CSV de métricas."""
    print("=" * 78)
    print("  VALIDAÇÃO DOS DADOS")
    print("=" * 78)

    if not os.path.isfile(csv_path):
        print(f"  ERRO: Arquivo não encontrado: {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path, encoding="utf-8")
    n = len(df)
    print(f"  Linhas carregadas: {n}")

    # Checar completude
    ok = True
    expected_pairs = [(inst, scen) for inst in INSTANCE_ORDER for scen in SCENARIOS]
    for inst, scen in expected_pairs:
        mask = (df["instance"] == inst) & (df["scenario"] == scen)
        if mask.sum() == 0:
            print(f"  ⚠ FALTANDO: {inst} × {scen}")
            ok = False
        elif mask.sum() > 1:
            print(f"  ⚠ DUPLICADA: {inst} × {scen} ({mask.sum()} linhas)")

    if n < 15:
        print(f"\n  ⚠ ATENÇÃO: {n}/15 execuções encontradas. Análise parcial será gerada.")
    elif ok:
        print(f"  ✔ 15/15 execuções presentes. Dados completos.")

    # Verificar colunas críticas sem NaN (exceto MILP que não tem GA params)
    crit_cols = ["custo_total_folha", "tempo_execucao_s", "perc_funcionarios_alocados"]
    for col in crit_cols:
        na_count = df[col].isna().sum()
        if na_count > 0:
            print(f"  ⚠ Coluna '{col}' tem {na_count} valores NaN")

    # Tipos numéricos
    num_cols = ["custo_total_folha", "tempo_execucao_s", "funcionarios_alocados",
                "total_funcionarios", "total_alocacoes", "projetos_ativos", "upgrades",
                "viol_distancia", "viol_autoexclusao", "viol_descompressao", "viol_treino"]
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Adicionar colunas derivadas
    df["instance_cat"] = pd.Categorical(df["instance"], categories=INSTANCE_ORDER, ordered=True)
    df["label"] = df["instance"].map(INSTANCE_LABELS)
    n_func = df["instance"].map(lambda x: INSTANCE_SIZES.get(x, (0, 0))[0])
    n_proj = df["instance"].map(lambda x: INSTANCE_SIZES.get(x, (0, 0))[1])
    df["problem_size"] = n_func * n_proj  # dimensão do espaço de busca

    # Violações BE totais
    viol_cols = ["viol_distancia", "viol_autoexclusao", "viol_descompressao"]
    df["viol_be_total"] = df[viol_cols].fillna(0).sum(axis=1).astype(int)

    print()
    return df


def pivot_metric(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Cria tabela pivotada instância × cenário para uma métrica."""
    pv = df.pivot_table(index="instance", columns="scenario", values=metric, aggfunc="first")
    pv = pv.reindex(index=INSTANCE_ORDER, columns=SCENARIOS)
    pv.index.name = "Instância"
    return pv


# ====================================================================
# 2. TABELA MESTRA — Visão geral do experimento
# ====================================================================

def tabela_mestra(df: pd.DataFrame, out: str):
    """Gera a tabela geral do experimento com todas as métricas chave."""
    print("=" * 78)
    print("  TABELA MESTRA DO EXPERIMENTO")
    print("=" * 78)

    table_rows = []
    for inst in INSTANCE_ORDER:
        for scen in SCENARIOS:
            row = df[(df["instance"] == inst) & (df["scenario"] == scen)]
            if row.empty:
                continue
            r = row.iloc[0]
            table_rows.append({
                "Instância":   INSTANCE_LABELS.get(inst, inst),
                "Cenário":     SCENARIO_LABELS.get(scen, scen),
                "Custo (R$M)": f"{r['custo_total_folha'] / 1e6:,.1f}",
                "Tempo (s)":   f"{r['tempo_execucao_s']:,.1f}",
                "%Func":       f"{r['perc_funcionarios_alocados']:.1f}%",
                "Alocações":   f"{int(r['total_alocacoes']):,}",
                "Upgrades":    f"{int(r.get('upgrades', 0)):,}" if pd.notna(r.get('upgrades')) else "—",
                "Viol BE":     f"{int(r['viol_be_total'])}" if pd.notna(r.get("viol_be_total")) else "0",
                "Viol Treino": f"{int(r.get('viol_treino', 0))}" if pd.notna(r.get("viol_treino")) else "—",
                "Ger GA":      f"{int(r['geracoes_ga'])}" if pd.notna(r.get("geracoes_ga")) else "—",
            })

    master = pd.DataFrame(table_rows)
    print(master.to_string(index=False))

    # Salvar CSV
    master.to_csv(os.path.join(out, "tabela_mestra.csv"), index=False, encoding="utf-8-sig")
    print(f"\n  Salvo: tabela_mestra.csv")

    # LaTeX
    latex_path = os.path.join(out, "tabela_mestra.tex")
    _to_latex(master, latex_path,
              caption="Resultados consolidados do experimento (5 instâncias × 3 cenários).",
              label="tab:tabela_mestra")


# ====================================================================
# 3. RQ1 — IMPACTO DO BEM-ESTAR NO CUSTO (A vs B)
# ====================================================================

def analyze_rq1(df: pd.DataFrame, out: str):
    """
    RQ1: Incorporar variáveis de bem-estar aumenta significativamente o custo?
    Compara cenário A (GA sem BE) com cenário B (GA com BE).
    """
    print("\n" + "=" * 78)
    print("  RQ1: IMPACTO DAS VARIÁVEIS DE BEM-ESTAR NO CUSTO")
    print("  Comparação: GA sem BE (A) vs GA com BE (B)")
    print("=" * 78)

    df_a = df[df["scenario"] == "A_GA_noBE"].sort_values("instance_cat").reset_index(drop=True)
    df_b = df[df["scenario"] == "B_GA_BE"].sort_values("instance_cat").reset_index(drop=True)

    if len(df_a) == 0 or len(df_b) == 0:
        print("  ⚠ Dados insuficientes para RQ1.")
        return

    n_pairs = min(len(df_a), len(df_b))

    # --- 3a. Tabela de custo ---
    comp = pd.DataFrame({
        "Instância":     df_a["label"].values[:n_pairs],
        "Custo_A (R$M)": (df_a["custo_total_folha"].values[:n_pairs] / 1e6).round(2),
        "Custo_B (R$M)": (df_b["custo_total_folha"].values[:n_pairs] / 1e6).round(2),
    })
    comp["Δ (R$M)"]  = (comp["Custo_B (R$M)"] - comp["Custo_A (R$M)"]).round(2)
    comp["Δ (%)"]    = ((comp["Custo_B (R$M)"] - comp["Custo_A (R$M)"]) / comp["Custo_A (R$M)"] * 100).round(2)

    print("\n  ┌─ Comparação de Custo Total ─────────────────────────────────────┐")
    print(comp.to_string(index=False))
    print(f"\n  Média Δ%:    {comp['Δ (%)'].mean():.2f}%")
    print(f"  Mediana Δ%:  {comp['Δ (%)'].median():.2f}%")
    print(f"  Intervalo:   [{comp['Δ (%)'].min():.2f}%, {comp['Δ (%)'].max():.2f}%]")
    print("  └─────────────────────────────────────────────────────────────────┘")

    # --- 3b. Tabela de tempo  ---
    comp_t = pd.DataFrame({
        "Instância":     df_a["label"].values[:n_pairs],
        "Tempo_A (s)":   df_a["tempo_execucao_s"].values[:n_pairs].round(1),
        "Tempo_B (s)":   df_b["tempo_execucao_s"].values[:n_pairs].round(1),
    })
    comp_t["Δ Tempo (%)"] = (((comp_t["Tempo_B (s)"] - comp_t["Tempo_A (s)"])
                               / comp_t["Tempo_A (s)"] * 100)).round(1)

    print("\n  ┌─ Comparação de Tempo de Execução ───────────────────────────────┐")
    print(comp_t.to_string(index=False))
    print("  └─────────────────────────────────────────────────────────────────┘")

    # --- 3c. Tabela de violações BE  ---
    be_cols = ["viol_distancia", "viol_autoexclusao", "viol_descompressao"]
    be_table = pd.DataFrame({"Instância": df_a["label"].values[:n_pairs]})
    for col in be_cols:
        short = col.replace("viol_", "")
        be_table[f"{short}_A"] = df_a[col].fillna(0).values[:n_pairs].astype(int)
        be_table[f"{short}_B"] = df_b[col].fillna(0).values[:n_pairs].astype(int)
    be_table["Total_A"] = df_a["viol_be_total"].values[:n_pairs]
    be_table["Total_B"] = df_b["viol_be_total"].values[:n_pairs]

    print("\n  ┌─ Violações de Bem-Estar ────────────────────────────────────────┐")
    print(be_table.to_string(index=False))
    total_a = be_table["Total_A"].sum()
    total_b = be_table["Total_B"].sum()
    reduction = ((total_a - total_b) / total_a * 100) if total_a > 0 else 0
    print(f"\n  Total violações A: {total_a}   |   Total violações B: {total_b}")
    print(f"  Redução com BE ativado: {reduction:.1f}%")
    print("  └─────────────────────────────────────────────────────────────────┘")

    # --- 3d. Tabela de cobertura funcional ---
    cob = pd.DataFrame({
        "Instância":  df_a["label"].values[:n_pairs],
        "%Func_A":    df_a["perc_funcionarios_alocados"].values[:n_pairs],
        "%Func_B":    df_b["perc_funcionarios_alocados"].values[:n_pairs],
        "Alloc_A":    df_a["total_alocacoes"].values[:n_pairs].astype(int),
        "Alloc_B":    df_b["total_alocacoes"].values[:n_pairs].astype(int),
    })
    print("\n  ┌─ Cobertura e Qualidade ─────────────────────────────────────────┐")
    print(cob.to_string(index=False))
    print("  └─────────────────────────────────────────────────────────────────┘")

    # --- 3e. Teste de Wilcoxon ---
    _wilcoxon_test(
        df_a["custo_total_folha"].values[:n_pairs],
        df_b["custo_total_folha"].values[:n_pairs],
        name="RQ1 — Custo (A vs B)",
        label_x="GA s/ BE", label_y="GA c/ BE"
    )

    # --- 3f. Gráficos ---
    if HAS_MPL:
        _plot_rq1(comp, be_table, out)

    # --- 3g. Salvar CSVs e LaTeX ---
    comp.to_csv(os.path.join(out, "RQ1_custo_comparison.csv"), index=False, encoding="utf-8-sig")
    be_table.to_csv(os.path.join(out, "RQ1_violacoes_BE.csv"), index=False, encoding="utf-8-sig")

    _to_latex(comp, os.path.join(out, "RQ1_custo.tex"),
              caption="RQ1 — Comparação de custo: GA sem BE (A) vs GA com BE (B).",
              label="tab:rq1_custo")
    _to_latex(be_table, os.path.join(out, "RQ1_violacoes.tex"),
              caption="RQ1 — Violações de bem-estar por instância e cenário.",
              label="tab:rq1_violacoes")


# ====================================================================
# 4. RQ2 — COMPARAÇÃO MILP vs GA (B vs C)
# ====================================================================

def analyze_rq2(df: pd.DataFrame, out: str):
    """
    RQ2: GA com BE é uma alternativa viável ao MILP para instâncias grandes?
    Compara cenário B (GA+BE) com cenário C (MILP+BE).
    """
    print("\n" + "=" * 78)
    print("  RQ2: COMPARAÇÃO DE DESEMPENHO — MILP vs GA (ambos com BE)")
    print("  Comparação: GA com BE (B) vs MILP com BE (C)")
    print("=" * 78)

    df_b = df[df["scenario"] == "B_GA_BE"].sort_values("instance_cat").reset_index(drop=True)
    df_c = df[df["scenario"] == "C_MILP_BE"].sort_values("instance_cat").reset_index(drop=True)

    if len(df_b) == 0 or len(df_c) == 0:
        print("  ⚠ Dados insuficientes para RQ2.")
        return

    n_pairs = min(len(df_b), len(df_c))

    # --- 4a. Gap de qualidade (custo) ---
    custo_comp = pd.DataFrame({
        "Instância":       df_b["label"].values[:n_pairs],
        "Custo_GA (R$M)":  (df_b["custo_total_folha"].values[:n_pairs] / 1e6).round(2),
        "Custo_MILP (R$M)":(df_c["custo_total_folha"].values[:n_pairs] / 1e6).round(2),
    })
    custo_comp["Gap (%)"] = (((custo_comp["Custo_GA (R$M)"] - custo_comp["Custo_MILP (R$M)"])
                              / custo_comp["Custo_MILP (R$M)"] * 100)).round(2)

    print("\n  ┌─ Gap de Qualidade (Custo) ──────────────────────────────────────┐")
    print(custo_comp.to_string(index=False))
    print(f"\n  Média Gap:    {custo_comp['Gap (%)'].mean():.2f}%")
    print(f"  Mediana Gap:  {custo_comp['Gap (%)'].median():.2f}%")
    print(f"  Intervalo:    [{custo_comp['Gap (%)'].min():.2f}%, {custo_comp['Gap (%)'].max():.2f}%]")

    # Interpretação
    mean_gap = custo_comp["Gap (%)"].mean()
    if mean_gap < 0:
        print(f"  → GA produz custo MENOR que MILP em média ({mean_gap:.1f}%) — "
              "GA aloca mais funcionários com menor custo por explorar upgrades.")
    elif mean_gap < 5:
        print(f"  → Gap médio de {mean_gap:.1f}% — GA é competitivo com MILP.")
    else:
        print(f"  → Gap médio de {mean_gap:.1f}% — MILP produz solução significativamente melhor.")
    print("  └─────────────────────────────────────────────────────────────────┘")

    # --- 4b. Comparação de tempo ---
    tempo_comp = pd.DataFrame({
        "Instância":       df_b["label"].values[:n_pairs],
        "Tempo_GA (s)":    df_b["tempo_execucao_s"].values[:n_pairs].round(1),
        "Tempo_MILP (s)":  df_c["tempo_execucao_s"].values[:n_pairs].round(1),
    })
    # Speedup: > 1 = MILP mais rápido; < 1 = GA mais rápido
    tempo_comp["Razão GA/MILP"] = (tempo_comp["Tempo_GA (s)"] / tempo_comp["Tempo_MILP (s)"]).round(2)
    tempo_comp["Mais rápido"] = tempo_comp.apply(
        lambda r: "GA" if r["Tempo_GA (s)"] < r["Tempo_MILP (s)"] else "MILP", axis=1)

    print("\n  ┌─ Comparação de Tempo ───────────────────────────────────────────┐")
    print(tempo_comp.to_string(index=False))
    print("  └─────────────────────────────────────────────────────────────────┘")

    # --- 4c. Cobertura e violações ---
    qual_comp = pd.DataFrame({
        "Instância":       df_b["label"].values[:n_pairs],
        "%Func_GA":        df_b["perc_funcionarios_alocados"].values[:n_pairs],
        "%Func_MILP":      df_c["perc_funcionarios_alocados"].values[:n_pairs],
        "Viol_BE_GA":      df_b["viol_be_total"].values[:n_pairs].astype(int),
        "Viol_BE_MILP":    df_c["viol_be_total"].values[:n_pairs].astype(int),
        "Viol_Treino_GA":  df_b["viol_treino"].fillna(0).values[:n_pairs].astype(int),
        "Viol_Treino_MILP": df_c["viol_treino"].fillna(0).values[:n_pairs].astype(int),
    })
    print("\n  ┌─ Qualidade da Solução ──────────────────────────────────────────┐")
    print(qual_comp.to_string(index=False))
    print("\n  Nota: MILP garante 0 violações de BE (restrições obrigatórias).")
    print("  GA utiliza penalidades na função fitness — pode residuar violações.")
    print("  └─────────────────────────────────────────────────────────────────┘")

    # --- 4d. Testes de Wilcoxon ---
    _wilcoxon_test(
        df_b["custo_total_folha"].values[:n_pairs],
        df_c["custo_total_folha"].values[:n_pairs],
        name="RQ2 — Custo (GA vs MILP)",
        label_x="GA c/ BE", label_y="MILP c/ BE"
    )
    _wilcoxon_test(
        df_b["tempo_execucao_s"].values[:n_pairs],
        df_c["tempo_execucao_s"].values[:n_pairs],
        name="RQ2 — Tempo (GA vs MILP)",
        label_x="GA c/ BE", label_y="MILP c/ BE"
    )

    # --- 4e. Gráficos ---
    if HAS_MPL:
        _plot_rq2(custo_comp, tempo_comp, qual_comp, out)

    # --- 4f. Salvar ---
    custo_comp.to_csv(os.path.join(out, "RQ2_custo_gap.csv"), index=False, encoding="utf-8-sig")
    tempo_comp.to_csv(os.path.join(out, "RQ2_tempo_comparison.csv"), index=False, encoding="utf-8-sig")
    qual_comp.to_csv(os.path.join(out, "RQ2_qualidade.csv"), index=False, encoding="utf-8-sig")

    _to_latex(custo_comp, os.path.join(out, "RQ2_custo.tex"),
              caption="RQ2 — Gap de custo: GA com BE vs MILP com BE.",
              label="tab:rq2_custo")
    _to_latex(tempo_comp, os.path.join(out, "RQ2_tempo.tex"),
              caption="RQ2 — Comparação de tempo de execução.",
              label="tab:rq2_tempo")


# ====================================================================
# 5. ANÁLISE DE ESCALABILIDADE
# ====================================================================

def analyze_scalability(df: pd.DataFrame, out: str):
    """Analisa como custo e tempo escalam com o tamanho da instância."""
    print("\n" + "=" * 78)
    print("  ANÁLISE DE ESCALABILIDADE")
    print("=" * 78)

    for scen in SCENARIOS:
        sub = df[df["scenario"] == scen].sort_values("instance_cat").reset_index(drop=True)
        if sub.empty:
            continue
        n_func_col = sub["instance"].map(lambda x: INSTANCE_SIZES.get(x, (0,0))[0])
        print(f"\n  {SCENARIO_LABELS.get(scen, scen)}:")
        print(f"  {'Instância':<18} {'N Func':>8} {'Custo (R$M)':>13} {'Tempo (s)':>12} {'Tempo/func (s)':>15}")
        print("  " + "-" * 68)
        for _, r in sub.iterrows():
            nf = INSTANCE_SIZES.get(r["instance"], (0,0))[0]
            custo_m = r["custo_total_folha"] / 1e6
            tempo = r["tempo_execucao_s"]
            tempo_por_func = tempo / nf if nf > 0 else 0
            print(f"  {INSTANCE_LABELS.get(r['instance'], r['instance']):<18} {nf:>8} {custo_m:>13,.1f} {tempo:>12,.1f} {tempo_por_func:>15.2f}")

    # Gráfico de escalabilidade
    if HAS_MPL:
        _plot_scalability(df, out)


# ====================================================================
# 6. RESUMO EXECUTIVO
# ====================================================================

def executive_summary(df: pd.DataFrame, out: str):
    """Gera o resumo executivo do experimento."""
    print("\n" + "=" * 78)
    print("  RESUMO EXECUTIVO")
    print("=" * 78)

    n_instances = df["instance"].nunique()
    n_scenarios = df["scenario"].nunique()
    n_runs = len(df)

    print(f"\n  Execuções realizadas:  {n_runs} / 15")
    print(f"  Instâncias testadas:   {n_instances}")
    print(f"  Cenários comparados:   {n_scenarios}")

    # RQ1 recap
    df_a = df[df["scenario"] == "A_GA_noBE"].sort_values("instance_cat")
    df_b = df[df["scenario"] == "B_GA_BE"].sort_values("instance_cat")
    if len(df_a) > 0 and len(df_b) > 0:
        n = min(len(df_a), len(df_b))
        custos_a = df_a["custo_total_folha"].values[:n]
        custos_b = df_b["custo_total_folha"].values[:n]
        delta_pct = ((custos_b - custos_a) / custos_a * 100)
        print(f"\n  RQ1 — Impacto do Bem-Estar:")
        print(f"    Δ média de custo (B-A):   {delta_pct.mean():.2f}%")
        print(f"    Δ mediana de custo (B-A): {np.median(delta_pct):.2f}%")
        viol_a = df_a["viol_be_total"].sum()
        viol_b = df_b["viol_be_total"].sum()
        print(f"    Violações BE: A={int(viol_a)} → B={int(viol_b)} "
              f"(redução de {(viol_a-viol_b)/viol_a*100:.0f}%)" if viol_a > 0 else "")

    # RQ2 recap
    df_c = df[df["scenario"] == "C_MILP_BE"].sort_values("instance_cat")
    if len(df_b) > 0 and len(df_c) > 0:
        n = min(len(df_b), len(df_c))
        custos_b2 = df_b["custo_total_folha"].values[:n]
        custos_c = df_c["custo_total_folha"].values[:n]
        gap = ((custos_b2 - custos_c) / custos_c * 100)
        print(f"\n  RQ2 — GA vs MILP:")
        print(f"    Gap médio de custo GA/MILP: {gap.mean():.2f}%")
        tempo_b = df_b["tempo_execucao_s"].values[:n]
        tempo_c = df_c["tempo_execucao_s"].values[:n]
        print(f"    Tempo médio GA:   {tempo_b.mean():,.0f}s")
        print(f"    Tempo médio MILP: {tempo_c.mean():,.0f}s")
        print(f"    MILP garante 0 violações BE;  GA residua {int(df_b['viol_be_total'].sum())} violações.")

    # Findings
    print("\n  ──── ACHADOS PRINCIPAIS ────")
    if len(df_a) > 0 and len(df_b) > 0:
        if delta_pct.mean() < 0:
            print("  1. Incorporar BE REDUZ o custo (contra-intuitivo) — as restrições")
            print("     de BE guiam a busca do GA para soluções de melhor qualidade.")
        elif abs(delta_pct.mean()) < 5:
            print("  1. Incorporar BE tem impacto MARGINAL no custo (< 5%).")
        else:
            print("  1. Incorporar BE AUMENTA o custo moderadamente.")

    if len(df_b) > 0 and len(df_c) > 0:
        if gap.mean() < 0:
            print("  2. GA produz custo menor que MILP — explora upgrades e flexibilidade")
            print("     de alocação que o MILP com gap=1% não otimiza.")
        elif gap.mean() < 10:
            print("  2. GA é competitivo com MILP em custo (gap < 10%).")
        else:
            print("  2. MILP supera GA em qualidade de solução.")

    print()

    # Salvar
    summary_txt = os.path.join(out, "resumo_executivo.txt")
    # Redirect print to file
    from io import StringIO
    buf = StringIO()
    buf.write(f"RESUMO EXECUTIVO — Experimento Dissertação\n")
    buf.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    buf.write(f"Execuções: {n_runs}/15\n")
    if len(df_a) > 0 and len(df_b) > 0:
        buf.write(f"\nRQ1 — Δ média custo BE: {delta_pct.mean():.2f}%\n")
        buf.write(f"RQ1 — Redução violações BE: {int(viol_a)}→{int(viol_b)}\n")
    if len(df_b) > 0 and len(df_c) > 0:
        buf.write(f"\nRQ2 — Gap médio GA/MILP: {gap.mean():.2f}%\n")
        buf.write(f"RQ2 — Violações BE GA: {int(df_b['viol_be_total'].sum())}\n")
        buf.write(f"RQ2 — Violações BE MILP: 0\n")
    with open(summary_txt, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"  Salvo: {summary_txt}")


# ====================================================================
# UTILITÁRIOS — Wilcoxon
# ====================================================================

def _wilcoxon_test(x, y, name: str, label_x: str, label_y: str):
    """Executa e imprime resultado do teste de Wilcoxon pareado."""
    print(f"\n  ── Teste de Wilcoxon: {name} ──")
    diffs = y - x
    if np.all(diffs == 0):
        print(f"    Diferenças todas zero — teste não aplicável.")
        return

    if not HAS_SCIPY:
        print(f"    ⚠ scipy não instalado. Instale: pip install scipy")
        return

    n = len(x)
    if n < 5:
        print(f"    n={n} < 5 — poder estatístico insuficiente.")

    try:
        stat, p_value = wilcoxon(x, y, alternative="two-sided")
        sig = "SIM" if p_value < 0.05 else "NÃO"
        print(f"    n={n}, W={stat}, p={p_value:.4f}")
        print(f"    Significante (α=0.05): {sig}")

        if p_value >= 0.05:
            print(f"    → Não há evidência estatística de diferença entre {label_x} e {label_y}.")
        else:
            med_diff = np.median(diffs)
            if med_diff > 0:
                print(f"    → {label_y} tende a ter valores MAIORES que {label_x}.")
            else:
                print(f"    → {label_y} tende a ter valores MENORES que {label_x}.")

        # Effect size: r = Z / sqrt(n)
        from scipy.stats import norm
        z = norm.ppf(p_value / 2)
        r_effect = abs(z) / np.sqrt(n)
        magnitude = "grande" if r_effect >= 0.5 else "médio" if r_effect >= 0.3 else "pequeno"
        print(f"    Tamanho de efeito: r={r_effect:.3f} ({magnitude})")

    except Exception as e:
        print(f"    Falha: {e}")


# ====================================================================
# UTILITÁRIOS — Gráficos
# ====================================================================

def _plot_rq1(comp: pd.DataFrame, be_table: pd.DataFrame, out: str):
    """Gráficos para RQ1."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

    x = np.arange(len(comp))
    w = 0.35

    # (a) Custo lado a lado
    ax = axes[0]
    ax.bar(x - w/2, comp["Custo_A (R$M)"], w, label="GA s/ BE (A)", color=COLORS["A_GA_noBE"])
    ax.bar(x + w/2, comp["Custo_B (R$M)"], w, label="GA c/ BE (B)", color=COLORS["B_GA_BE"])
    ax.set_ylabel("Custo Total (R$ milhões)")
    ax.set_title("(a) Custo Total de Folha")
    ax.set_xticks(x)
    ax.set_xticklabels(comp["Instância"], rotation=35, ha="right")
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    # (b) Delta percentual
    ax = axes[1]
    colors_delta = ["#f44336" if d > 0 else "#4CAF50" for d in comp["Δ (%)"]]
    bars = ax.bar(x, comp["Δ (%)"], color=colors_delta, edgecolor="white", linewidth=0.5)
    ax.set_ylabel("Δ Custo (%)")
    ax.set_title("(b) Impacto do BE no Custo")
    ax.set_xticks(x)
    ax.set_xticklabels(comp["Instância"], rotation=35, ha="right")
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.grid(axis="y", alpha=0.3)
    # Anotar valores
    for bar_item, val in zip(bars, comp["Δ (%)"]):
        ypos = bar_item.get_height() if val >= 0 else bar_item.get_height()
        ax.text(bar_item.get_x() + bar_item.get_width() / 2, ypos,
                f"{val:+.1f}%", ha="center",
                va="bottom" if val >= 0 else "top", fontsize=9, fontweight="bold")

    # (c) Violações BE
    ax = axes[2]
    if "Total_A" in be_table.columns:
        ax.bar(x - w/2, be_table["Total_A"], w, label="Sem BE (A)", color=COLORS["A_GA_noBE"], alpha=0.8)
        ax.bar(x + w/2, be_table["Total_B"], w, label="Com BE (B)", color=COLORS["B_GA_BE"], alpha=0.8)
        ax.set_ylabel("Nº Violações BE")
        ax.set_title("(c) Violações de Bem-Estar")
        ax.set_xticks(x)
        ax.set_xticklabels(be_table["Instância"], rotation=35, ha="right")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

    plt.suptitle("RQ1 — Impacto das Variáveis de Bem-Estar", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    for ext in ["png", "pdf"]:
        fig_path = os.path.join(out, f"RQ1_impacto_BE.{ext}")
        fig.savefig(fig_path)
    plt.close(fig)
    print(f"  Gráfico RQ1 salvo: RQ1_impacto_BE.png / .pdf")


def _plot_rq2(custo_comp, tempo_comp, qual_comp, out):
    """Gráficos para RQ2."""
    fig, axes = plt.subplots(2, 2, figsize=(15, 11))

    x = np.arange(len(custo_comp))
    w = 0.35

    # (a) Custo
    ax = axes[0, 0]
    ax.bar(x - w/2, custo_comp["Custo_GA (R$M)"], w, label="GA c/ BE", color=COLORS["B_GA_BE"])
    ax.bar(x + w/2, custo_comp["Custo_MILP (R$M)"], w, label="MILP c/ BE", color=COLORS["C_MILP_BE"])
    ax.set_ylabel("Custo (R$ milhões)")
    ax.set_title("(a) Custo Total de Folha")
    ax.set_xticks(x)
    ax.set_xticklabels(custo_comp["Instância"], rotation=35, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    # (b) Gap de custo
    ax = axes[0, 1]
    colors_gap = ["#f44336" if d > 0 else "#4CAF50" for d in custo_comp["Gap (%)"]]
    bars = ax.bar(x, custo_comp["Gap (%)"], color=colors_gap, edgecolor="white")
    ax.set_ylabel("Gap GA vs MILP (%)")
    ax.set_title("(b) Gap de Qualidade")
    ax.set_xticks(x)
    ax.set_xticklabels(custo_comp["Instância"], rotation=35, ha="right")
    ax.axhline(y=0, color="black", linewidth=0.8)
    ax.grid(axis="y", alpha=0.3)
    for bar_item, val in zip(bars, custo_comp["Gap (%)"]):
        ypos = bar_item.get_height()
        ax.text(bar_item.get_x() + bar_item.get_width() / 2, ypos,
                f"{val:+.1f}%", ha="center",
                va="bottom" if val >= 0 else "top", fontsize=9, fontweight="bold")

    # (c) Tempo (log scale)
    ax = axes[1, 0]
    ax.bar(x - w/2, tempo_comp["Tempo_GA (s)"], w, label="GA c/ BE", color=COLORS["B_GA_BE"])
    ax.bar(x + w/2, tempo_comp["Tempo_MILP (s)"], w, label="MILP c/ BE", color=COLORS["C_MILP_BE"])
    ax.set_ylabel("Tempo (s) — escala log")
    ax.set_title("(c) Tempo de Execução")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(tempo_comp["Instância"], rotation=35, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3, which="both")

    # (d) Violações BE + treinamento
    ax = axes[1, 1]
    if "Viol_BE_GA" in qual_comp.columns:
        be_ga = qual_comp["Viol_BE_GA"]
        be_milp = qual_comp["Viol_BE_MILP"]
        tr_ga = qual_comp["Viol_Treino_GA"]
        tr_milp = qual_comp["Viol_Treino_MILP"]

        bar_w = 0.2
        ax.bar(x - 1.5*bar_w, be_ga,   bar_w, label="Viol BE — GA",    color=COLORS["B_GA_BE"])
        ax.bar(x - 0.5*bar_w, be_milp,  bar_w, label="Viol BE — MILP",  color=COLORS["C_MILP_BE"])
        ax.bar(x + 0.5*bar_w, tr_ga,    bar_w, label="Viol Treino — GA", color=COLORS["B_GA_BE"], alpha=0.5, hatch="//")
        ax.bar(x + 1.5*bar_w, tr_milp,  bar_w, label="Viol Treino — MILP", color=COLORS["C_MILP_BE"], alpha=0.5, hatch="//")
        ax.set_ylabel("Nº Violações")
        ax.set_title("(d) Violações — GA vs MILP")
        ax.set_xticks(x)
        ax.set_xticklabels(qual_comp["Instância"], rotation=35, ha="right")
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(axis="y", alpha=0.3)

    plt.suptitle("RQ2 — Comparação GA com BE vs MILP com BE", fontsize=14, fontweight="bold", y=1.01)
    plt.tight_layout()

    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(out, f"RQ2_GA_vs_MILP.{ext}"))
    plt.close(fig)
    print(f"  Gráfico RQ2 salvo: RQ2_GA_vs_MILP.png / .pdf")


def _plot_scalability(df: pd.DataFrame, out: str):
    """Gráfico de escalabilidade: tempo e custo vs tamanho."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    for scen in SCENARIOS:
        sub = df[df["scenario"] == scen].sort_values("instance_cat")
        if sub.empty:
            continue
        sizes = sub["instance"].map(lambda x: INSTANCE_SIZES.get(x, (0,0))[0])
        label = SCENARIO_LABELS.get(scen, scen)
        color = COLORS.get(scen, "gray")
        marker = "s" if scen.startswith("C") else "o" if scen.endswith("noBE") else "^"

        axes[0].plot(sizes, sub["tempo_execucao_s"], "-", label=label, color=color, marker=marker, markersize=7)
        axes[1].plot(sizes, sub["custo_total_folha"] / 1e6, "-", label=label, color=color, marker=marker, markersize=7)

    axes[0].set_xlabel("Nº Funcionários")
    axes[0].set_ylabel("Tempo (s)")
    axes[0].set_title("(a) Escalabilidade — Tempo")
    axes[0].set_yscale("log")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3, which="both")

    axes[1].set_xlabel("Nº Funcionários")
    axes[1].set_ylabel("Custo (R$ milhões)")
    axes[1].set_title("(b) Escalabilidade — Custo")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    plt.suptitle("Análise de Escalabilidade", fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()

    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(out, f"escalabilidade.{ext}"))
    plt.close(fig)
    print(f"  Gráfico salvo: escalabilidade.png / .pdf")


def _plot_all_scenarios_heatmap(df: pd.DataFrame, out: str):
    """Gráfico de barras agrupadas: 3 cenários × 5 instâncias para custo."""
    fig, ax = plt.subplots(figsize=(12, 6))

    instances = [inst for inst in INSTANCE_ORDER if inst in df["instance"].values]
    x = np.arange(len(instances))
    n_scen = len(SCENARIOS)
    w = 0.25

    for i, scen in enumerate(SCENARIOS):
        sub = df[df["scenario"] == scen].set_index("instance")
        vals = [sub.loc[inst, "custo_total_folha"] / 1e6 if inst in sub.index else 0
                for inst in instances]
        offset = (i - (n_scen - 1) / 2) * w
        ax.bar(x + offset, vals, w, label=SCENARIO_LABELS.get(scen, scen),
               color=COLORS.get(scen, "gray"), edgecolor="white")

    ax.set_xlabel("Instância")
    ax.set_ylabel("Custo Total (R$ milhões)")
    ax.set_title("Comparação de Custo — Todos os Cenários")
    ax.set_xticks(x)
    ax.set_xticklabels([INSTANCE_LABELS.get(i, i) for i in instances], rotation=35, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(out, f"todos_cenarios_custo.{ext}"))
    plt.close(fig)
    print(f"  Gráfico salvo: todos_cenarios_custo.png / .pdf")


# ====================================================================
# UTILITÁRIOS — LaTeX
# ====================================================================

def _to_latex(df: pd.DataFrame, path: str, caption: str, label: str):
    """Exporta DataFrame como tabela LaTeX (sem dependência de jinja2)."""
    try:
        cols = df.columns.tolist()
        col_fmt = "l" + "r" * (len(cols) - 1)
        lines = []
        lines.append(r"\begin{table}[htbp]")
        lines.append(r"\centering")
        lines.append(f"\\caption{{{caption}}}")
        lines.append(f"\\label{{{label}}}")
        lines.append(f"\\begin{{tabular}}{{{col_fmt}}}")
        lines.append(r"\hline\hline")
        # Header
        header = " & ".join(str(c).replace("_", "\\_").replace("%", "\\%").replace("#", "\\#")
                             for c in cols)
        lines.append(header + r" \\")
        lines.append(r"\hline")
        # Rows
        for _, row in df.iterrows():
            vals = []
            for c in cols:
                v = row[c]
                s = str(v) if pd.notna(v) else "—"
                s = s.replace("_", "\\_").replace("%", "\\%").replace("#", "\\#")
                vals.append(s)
            lines.append(" & ".join(vals) + r" \\")
        lines.append(r"\hline\hline")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        latex = "\n".join(lines)

        with open(path, "w", encoding="utf-8") as f:
            f.write(latex)
        print(f"  LaTeX: {os.path.basename(path)}")
    except Exception as e:
        print(f"  ⚠ Falha ao gerar LaTeX {path}: {e}")


# ====================================================================
# MAIN
# ====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Análise completa dos resultados do experimento."
    )
    parser.add_argument(
        "--input", type=str,
        default="data/results/experiment_metrics.csv",
        help="CSV de métricas gerado por run_all.py"
    )
    parser.add_argument(
        "--output", type=str,
        default="data/results/analysis/",
        help="Diretório de saída para gráficos e tabelas"
    )
    args = parser.parse_args()

    # Resolver caminhos
    base = Path(__file__).resolve().parent.parent
    csv_path = (base / args.input) if not os.path.isabs(args.input) else Path(args.input)
    out_dir  = (base / args.output) if not os.path.isabs(args.output) else Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = str(out_dir)

    print()
    print("╔" + "═" * 76 + "╗")
    print("║   ANÁLISE DE RESULTADOS — EXPERIMENTO DISSERTAÇÃO                       ║")
    print("║   5 instâncias × 3 cenários × métricas                                  ║")
    print("╚" + "═" * 76 + "╝")
    print(f"\n  Entrada:  {csv_path}")
    print(f"  Saída:    {out_dir}")

    # 1. Carregar e validar
    df = load_and_validate(str(csv_path))

    # 2. Tabela mestra
    tabela_mestra(df, out)

    # 3. RQ1
    analyze_rq1(df, out)

    # 4. RQ2
    analyze_rq2(df, out)

    # 5. Escalabilidade
    analyze_scalability(df, out)

    # 6. Gráfico consolidado
    if HAS_MPL:
        _plot_all_scenarios_heatmap(df, out)

    # 7. Resumo executivo
    executive_summary(df, out)

    print("\n" + "=" * 78)
    print("  ANÁLISE CONCLUÍDA")
    print(f"  Artefatos em: {out_dir}")
    print("=" * 78)


if __name__ == "__main__":
    main()

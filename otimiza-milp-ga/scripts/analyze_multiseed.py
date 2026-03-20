#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_multiseed.py — Consolidação e análise multi-seed
========================================================
Consolida os resultados de múltiplas seeds do GA com os resultados
originais (seed=42) e MILP, e roda testes estatísticos com n=25.

Saídas geradas em data/results/analysis/:
  - multiseed_consolidated.csv     — CSV com todas as linhas (seed 42 + novas)
  - multiseed_summary.csv          — Média/desvio por instância × cenário
  - multiseed_RQ1_custo.csv/.tex   — RQ1 com 5 seeds
  - multiseed_RQ2_custo.csv/.tex   — RQ2 com 5 seeds
  - multiseed_statistical_tests.txt — Testes de Wilcoxon (n=25)
  - multiseed_*.png/pdf            — Gráficos atualizados

Uso:
  python scripts/analyze_multiseed.py
  python scripts/analyze_multiseed.py --original data/results/experiment_metrics.csv
  python scripts/analyze_multiseed.py --multiseed data/results/experiment_metrics_multiseed.csv
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

# ── Dependências opcionais ────────────────────────────────────────────────
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
    plt.rcParams.update({
        "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 12,
        "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 10,
        "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    })
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ── Constantes ────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "data", "results")
ANALYSIS_DIR = os.path.join(RESULTS_DIR, "analysis")

INSTANCE_ORDER = ["I1_SMALL", "I2_LARGE_05X", "I3_LARGE", "I4_LARGE_15X", "I5_LARGE_25X"]
INSTANCE_LABELS = {
    "I1_SMALL":      "I1 (220×60)",
    "I2_LARGE_05X":  "I2 (600×160)",
    "I3_LARGE":      "I3 (1200×320)",
    "I4_LARGE_15X":  "I4 (1800×480)",
    "I5_LARGE_25X":  "I5 (3000×800)",
}
SCENARIO_LABELS = {
    "A_GA_noBE":  "GA s/ BE",
    "B_GA_BE":    "GA c/ BE",
    "C_MILP_BE":  "MILP c/ BE",
    "D_MILP_noBE": "MILP s/ BE",
}
COLORS = {
    "A_GA_noBE":  "#2196F3",
    "B_GA_BE":    "#4CAF50",
    "C_MILP_BE":  "#9C27B0",
    "D_MILP_noBE": "#FF9800",
}


# ====================================================================
# 1. CARREGAMENTO E CONSOLIDAÇÃO
# ====================================================================

def load_and_consolidate(original_csv: str, multiseed_csv: str,
                         milp_nobe_csv: str = None) -> pd.DataFrame:
    """Carrega e consolida dados originais (seed 42) + multi-seed + MILP noBE."""
    print("=" * 78)
    print("  CONSOLIDAÇÃO DOS DADOS MULTI-SEED")
    print("=" * 78)

    # Original (seed 42): 15 linhas = 5 inst × 3 cen
    if not os.path.isfile(original_csv):
        print(f"  ERRO: Arquivo original não encontrado: {original_csv}")
        sys.exit(1)
    df_orig = pd.read_csv(original_csv, encoding="utf-8")
    print(f"  Original (seed 42): {len(df_orig)} linhas")

    # Multi-seed (seeds 123, 456, 789, 2026): até 40 linhas = 4 seeds × 5 inst × 2 cen
    if not os.path.isfile(multiseed_csv):
        print(f"  ERRO: Arquivo multi-seed não encontrado: {multiseed_csv}")
        sys.exit(1)
    df_multi = pd.read_csv(multiseed_csv, encoding="utf-8")
    print(f"  Multi-seed: {len(df_multi)} linhas")

    seeds_found = sorted(df_multi["ga_seed"].dropna().unique().astype(int).tolist())
    print(f"  Seeds nos dados: {seeds_found}")

    # Consolidar: GA rows from original + multi-seed + MILP from original
    df_ga_orig = df_orig[df_orig["model"] == "GA"].copy()
    df_milp = df_orig[df_orig["model"] == "MILP"].copy()

    parts = [df_ga_orig, df_multi, df_milp]

    # MILP sem BE (cenário D)
    if milp_nobe_csv and os.path.isfile(milp_nobe_csv):
        df_milp_nobe = pd.read_csv(milp_nobe_csv, encoding="utf-8")
        print(f"  MILP s/ BE: {len(df_milp_nobe)} linhas")
        if "model" not in df_milp_nobe.columns:
            df_milp_nobe["model"] = "MILP"
        parts.append(df_milp_nobe)
    else:
        print("  ⚠ Arquivo MILP s/ BE não encontrado — comparação MILP com/sem BE desabilitada.")

    df_all = pd.concat(parts, ignore_index=True)

    # Tipos numéricos
    num_cols = ["custo_total_folha", "tempo_execucao_s", "funcionarios_alocados",
                "total_funcionarios", "total_alocacoes", "projetos_ativos", "upgrades",
                "viol_distancia", "viol_autoexclusao", "viol_descompressao", "viol_treino",
                "perc_funcionarios_alocados", "ga_seed"]
    for col in num_cols:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

    # Violações BE totais
    viol_cols = ["viol_distancia", "viol_autoexclusao", "viol_descompressao"]
    df_all["viol_be_total"] = df_all[viol_cols].fillna(0).sum(axis=1).astype(int)

    df_all["label"] = df_all["instance"].map(INSTANCE_LABELS)
    df_all["instance_cat"] = pd.Categorical(df_all["instance"], categories=INSTANCE_ORDER, ordered=True)

    # Validação
    all_seeds = sorted(df_all[df_all["model"] == "GA"]["ga_seed"].dropna().unique().astype(int).tolist())
    print(f"\n  Seeds GA consolidadas: {all_seeds}")
    for inst in INSTANCE_ORDER:
        for scen in ["A_GA_noBE", "B_GA_BE"]:
            n = len(df_all[(df_all["instance"] == inst) & (df_all["scenario"] == scen)])
            status = "✔" if n >= 5 else "⚠"
            print(f"    {status} {inst} × {scen}: {n} seeds")
    for inst in INSTANCE_ORDER:
        n = len(df_all[(df_all["instance"] == inst) & (df_all["scenario"] == "C_MILP_BE")])
        print(f"    {'✔' if n >= 1 else '⚠'} {inst} × C_MILP_BE: {n} (MILP, determinístico)")
    for inst in INSTANCE_ORDER:
        n = len(df_all[(df_all["instance"] == inst) & (df_all["scenario"] == "D_MILP_noBE")])
        print(f"    {'✔' if n >= 1 else '⚠'} {inst} × D_MILP_noBE: {n} (MILP, determinístico)")

    print(f"\n  Total consolidado: {len(df_all)} linhas")
    return df_all


# ====================================================================
# 2. TABELA DE RESUMO — Média ± desvio
# ====================================================================

def summary_table(df: pd.DataFrame, out: str):
    """Gera tabela resumo com média ± desvio-padrão por instância × cenário."""
    print("\n" + "=" * 78)
    print("  TABELA RESUMO — MÉDIA ± DESVIO POR INSTÂNCIA × CENÁRIO")
    print("=" * 78)

    rows = []
    for inst in INSTANCE_ORDER:
        for scen in ["A_GA_noBE", "B_GA_BE", "C_MILP_BE", "D_MILP_noBE"]:
            mask = (df["instance"] == inst) & (df["scenario"] == scen)
            sub = df[mask]
            if sub.empty:
                continue
            n = len(sub)
            custo = sub["custo_total_folha"]
            tempo = sub["tempo_execucao_s"]
            perc = sub["perc_funcionarios_alocados"]
            viol_be = sub["viol_be_total"]

            rows.append({
                "Instância": INSTANCE_LABELS.get(inst, inst),
                "Cenário":   SCENARIO_LABELS.get(scen, scen),
                "n":         n,
                "Custo_Média (R$M)": round(custo.mean() / 1e6, 2),
                "Custo_DP (R$M)":    round(custo.std() / 1e6, 2) if n > 1 else 0,
                "Tempo_Média (s)":   round(tempo.mean(), 1),
                "Tempo_DP (s)":      round(tempo.std(), 1) if n > 1 else 0,
                "%Func_Média":       round(perc.mean(), 2),
                "Viol_BE_Média":     round(viol_be.mean(), 1),
                "Viol_BE_DP":        round(viol_be.std(), 1) if n > 1 else 0,
            })

    summary = pd.DataFrame(rows)
    print(summary.to_string(index=False))
    summary.to_csv(os.path.join(out, "multiseed_summary.csv"), index=False, encoding="utf-8-sig")
    print(f"\n  Salvo: multiseed_summary.csv")

    _to_latex(summary, os.path.join(out, "multiseed_summary.tex"),
              caption="Resumo multi-seed: média ± desvio-padrão por instância e cenário (5 seeds).",
              label="tab:multiseed_summary")
    return summary


# ====================================================================
# 3. RQ1 — MULTI-SEED: GA sem BE vs GA com BE
# ====================================================================

def analyze_rq1_multiseed(df: pd.DataFrame, out: str):
    """RQ1: compara custo com/sem BE para cada modelo (GA e MILP)."""
    print("\n" + "=" * 78)
    print("  RQ1 MULTI-SEED: IMPACTO DO BEM-ESTAR NO CUSTO")
    print("  (a) GA sem BE vs GA com BE — pareado por seed")
    print("  (b) MILP sem BE vs MILP com BE — determinístico")
    print("=" * 78)

    df_a = df[df["scenario"] == "A_GA_noBE"].copy()
    df_b = df[df["scenario"] == "B_GA_BE"].copy()

    if df_a.empty or df_b.empty:
        print("  ⚠ Dados insuficientes.")
        return

    # Merge pareado por (instance, seed)
    merged = pd.merge(
        df_a[["instance", "ga_seed", "custo_total_folha", "tempo_execucao_s",
              "viol_be_total", "perc_funcionarios_alocados"]],
        df_b[["instance", "ga_seed", "custo_total_folha", "tempo_execucao_s",
              "viol_be_total", "perc_funcionarios_alocados"]],
        on=["instance", "ga_seed"],
        suffixes=("_A", "_B"),
    )
    merged["label"] = merged["instance"].map(INSTANCE_LABELS)
    merged["delta_pct"] = ((merged["custo_total_folha_B"] - merged["custo_total_folha_A"])
                           / merged["custo_total_folha_A"] * 100).round(2)

    print(f"\n  Pares encontrados: {len(merged)} (esperado: {5 * len(merged['instance'].unique())})")

    # Tabela por instância (média das seeds)
    inst_summary = []
    for inst in INSTANCE_ORDER:
        m = merged[merged["instance"] == inst]
        if m.empty:
            continue
        inst_summary.append({
            "Instância": INSTANCE_LABELS[inst],
            "n_seeds": len(m),
            "Custo_A_Média (R$M)": round(m["custo_total_folha_A"].mean() / 1e6, 2),
            "Custo_B_Média (R$M)": round(m["custo_total_folha_B"].mean() / 1e6, 2),
            "Δ_Média (%)": round(m["delta_pct"].mean(), 2),
            "Δ_DP (%)": round(m["delta_pct"].std(), 2) if len(m) > 1 else 0,
            "Viol_BE_A": round(m["viol_be_total_A"].mean(), 1),
            "Viol_BE_B": round(m["viol_be_total_B"].mean(), 1),
        })

    rq1_df = pd.DataFrame(inst_summary)
    print("\n  ┌─ RQ1: Custo A vs B (média das seeds) ──────────────────────────┐")
    print(rq1_df.to_string(index=False))
    print(f"\n  Δ% global (média):   {merged['delta_pct'].mean():.2f}%")
    print(f"  Δ% global (mediana): {merged['delta_pct'].median():.2f}%")
    print("  └─────────────────────────────────────────────────────────────────┘")

    rq1_df.to_csv(os.path.join(out, "multiseed_RQ1_custo.csv"), index=False, encoding="utf-8-sig")
    _to_latex(rq1_df, os.path.join(out, "multiseed_RQ1_custo.tex"),
              caption="RQ1 multi-seed — Impacto do bem-estar no custo (5 seeds por instância).",
              label="tab:rq1_multiseed")

    # Teste de Wilcoxon pareado (todos os pares)
    _wilcoxon_test(
        merged["custo_total_folha_A"].values,
        merged["custo_total_folha_B"].values,
        name="RQ1 — Custo (A vs B) — Multi-seed",
        label_x="GA s/ BE", label_y="GA c/ BE", out=out,
    )

    # Gráfico boxplot
    if HAS_MPL:
        _plot_rq1_multiseed(merged, rq1_df, out)

    # ── RQ1b: MILP sem BE vs MILP com BE ──────────────────────────────
    _analyze_rq1_milp(df, out)

    return merged


def _analyze_rq1_milp(df: pd.DataFrame, out: str):
    """RQ1b: MILP sem BE (D) vs MILP com BE (C) — determinístico (1 valor por instância)."""
    print("\n" + "-" * 78)
    print("  RQ1b: MILP sem BE (D) vs MILP com BE (C)")
    print("-" * 78)

    df_c = df[df["scenario"] == "C_MILP_BE"].copy()
    df_d = df[df["scenario"] == "D_MILP_noBE"].copy()

    if df_d.empty:
        print("  ⚠ Dados MILP sem BE não disponíveis.")
        return
    if df_c.empty:
        print("  ⚠ Dados MILP com BE não disponíveis.")
        return

    rows = []
    for inst in INSTANCE_ORDER:
        c = df_c[df_c["instance"] == inst]
        d = df_d[df_d["instance"] == inst]
        if c.empty or d.empty:
            continue
        custo_c = c.iloc[0]["custo_total_folha"]
        custo_d = d.iloc[0]["custo_total_folha"]
        delta_pct = ((custo_c - custo_d) / custo_d * 100) if custo_d != 0 else 0
        viol_c = int(c.iloc[0].get("viol_be_total", 0))
        viol_d = int(d.iloc[0].get("viol_be_total", 0))
        rows.append({
            "Instância": INSTANCE_LABELS[inst],
            "Custo_MILP_noBE (R$M)": round(custo_d / 1e6, 2),
            "Custo_MILP_BE (R$M)": round(custo_c / 1e6, 2),
            "Δ (%)": round(delta_pct, 2),
            "Viol_BE_noBE": viol_d,
            "Viol_BE_cBE": viol_c,
        })

    milp_df = pd.DataFrame(rows)
    print(milp_df.to_string(index=False))

    if rows:
        avg_delta = np.mean([r["Δ (%)"] for r in rows])
        print(f"\n  Δ% médio MILP (c/ BE vs s/ BE): {avg_delta:.2f}%")

    milp_df.to_csv(os.path.join(out, "multiseed_RQ1_milp.csv"), index=False, encoding="utf-8-sig")
    _to_latex(milp_df, os.path.join(out, "multiseed_RQ1_milp.tex"),
              caption="RQ1 — Impacto do bem-estar no custo do MILP.",
              label="tab:rq1_milp")
    print(f"  Salvo: multiseed_RQ1_milp.csv/tex")

    # Gráfico comparativo MILP
    if HAS_MPL and len(rows) > 0:
        fig, ax = plt.subplots(figsize=(8, 5))
        instances = [r["Instância"] for r in rows]
        x = np.arange(len(instances))
        w = 0.35
        vals_d = [r["Custo_MILP_noBE (R$M)"] for r in rows]
        vals_c = [r["Custo_MILP_BE (R$M)"] for r in rows]
        ax.bar(x - w/2, vals_d, w, label="MILP s/ BE", color=COLORS["D_MILP_noBE"], alpha=0.8)
        ax.bar(x + w/2, vals_c, w, label="MILP c/ BE", color=COLORS["C_MILP_BE"], alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(instances, rotation=35, ha="right")
        ax.set_ylabel("Custo Total (R$ milhões)")
        ax.set_title("RQ1b — Custo MILP: sem BE vs com BE")
        ax.legend()
        plt.tight_layout()
        for ext in ["png", "pdf"]:
            fig.savefig(os.path.join(out, f"multiseed_RQ1_milp.{ext}"))
        plt.close()
        print("  Gráfico salvo: multiseed_RQ1_milp.png/pdf")


# ====================================================================
# 4. RQ2 — MULTI-SEED: GA com BE vs MILP
# ====================================================================

def analyze_rq2_multiseed(df: pd.DataFrame, out: str):
    """RQ2 com 5 seeds: compara GA-BE (B) vs MILP (C). MILP é 1 valor por instância."""
    print("\n" + "=" * 78)
    print("  RQ2 MULTI-SEED: COMPARAÇÃO GA vs MILP (ambos com BE)")
    print("  GA com BE (5 seeds) vs MILP com BE (1 valor, determinístico)")
    print("=" * 78)

    df_b = df[df["scenario"] == "B_GA_BE"].copy()
    df_c = df[df["scenario"] == "C_MILP_BE"].copy()

    if df_b.empty or df_c.empty:
        print("  ⚠ Dados insuficientes.")
        return

    # Para cada instância: compara cada seed-GA vs valor MILP fixo
    rows_all = []
    inst_summary = []
    for inst in INSTANCE_ORDER:
        ga = df_b[df_b["instance"] == inst].copy()
        milp = df_c[df_c["instance"] == inst]
        if ga.empty or milp.empty:
            continue
        milp_cost = milp.iloc[0]["custo_total_folha"]
        milp_time = milp.iloc[0]["tempo_execucao_s"]
        milp_viol = int(milp.iloc[0].get("viol_be_total", 0))

        ga["gap_pct"] = ((ga["custo_total_folha"] - milp_cost) / milp_cost * 100).round(2)
        ga["milp_cost"] = milp_cost
        ga["milp_time"] = milp_time
        rows_all.append(ga)

        inst_summary.append({
            "Instância": INSTANCE_LABELS[inst],
            "n_seeds": len(ga),
            "Custo_GA_Média (R$M)": round(ga["custo_total_folha"].mean() / 1e6, 2),
            "Custo_GA_DP (R$M)": round(ga["custo_total_folha"].std() / 1e6, 2) if len(ga) > 1 else 0,
            "Custo_MILP (R$M)": round(milp_cost / 1e6, 2),
            "Gap_Média (%)": round(ga["gap_pct"].mean(), 2),
            "Gap_DP (%)": round(ga["gap_pct"].std(), 2) if len(ga) > 1 else 0,
            "Tempo_GA_Média (s)": round(ga["tempo_execucao_s"].mean(), 1),
            "Tempo_MILP (s)": round(milp_time, 1),
            "Viol_BE_GA_Média": round(ga["viol_be_total"].mean(), 1),
            "Viol_BE_MILP": milp_viol,
        })

    rq2_df = pd.DataFrame(inst_summary)
    print("\n  ┌─ RQ2: Gap GA vs MILP (média das seeds) ────────────────────────┐")
    print(rq2_df.to_string(index=False))
    print("  └─────────────────────────────────────────────────────────────────┘")

    rq2_df.to_csv(os.path.join(out, "multiseed_RQ2_custo.csv"), index=False, encoding="utf-8-sig")
    _to_latex(rq2_df, os.path.join(out, "multiseed_RQ2_custo.tex"),
              caption="RQ2 multi-seed — Gap de custo GA vs MILP (5 seeds por instância).",
              label="tab:rq2_multiseed")

    # Wilcoxon pareado: para cada instância, compara cada seed GA vs valor MILP
    if rows_all:
        df_merged = pd.concat(rows_all, ignore_index=True)
        _wilcoxon_test(
            df_merged["milp_cost"].values,
            df_merged["custo_total_folha"].values,
            name="RQ2 — Custo (MILP vs GA-BE) — Multi-seed",
            label_x="MILP c/ BE", label_y="GA c/ BE", out=out,
        )

    # Gráficos
    if HAS_MPL:
        _plot_rq2_multiseed(rq2_df, out)

    return rq2_df


# ====================================================================
# 5. ANÁLISE DE VARIABILIDADE INTER-SEED
# ====================================================================

def analyze_variability(df: pd.DataFrame, out: str):
    """Analisa variabilidade do GA entre seeds (CV, range)."""
    print("\n" + "=" * 78)
    print("  VARIABILIDADE INTER-SEED DO GA")
    print("=" * 78)

    rows = []
    for inst in INSTANCE_ORDER:
        for scen in ["A_GA_noBE", "B_GA_BE"]:
            mask = (df["instance"] == inst) & (df["scenario"] == scen)
            sub = df[mask]
            if len(sub) < 2:
                continue
            custo = sub["custo_total_folha"]
            tempo = sub["tempo_execucao_s"]
            rows.append({
                "Instância": INSTANCE_LABELS[inst],
                "Cenário":   SCENARIO_LABELS[scen],
                "n":         len(sub),
                "Custo_CV (%)": round(custo.std() / custo.mean() * 100, 2) if custo.mean() != 0 else 0,
                "Custo_Min (R$M)": round(custo.min() / 1e6, 2),
                "Custo_Max (R$M)": round(custo.max() / 1e6, 2),
                "Custo_Range (R$M)": round((custo.max() - custo.min()) / 1e6, 2),
                "Tempo_CV (%)": round(tempo.std() / tempo.mean() * 100, 2) if tempo.mean() != 0 else 0,
                "Tempo_Min (s)": round(tempo.min(), 1),
                "Tempo_Max (s)": round(tempo.max(), 1),
            })

    var_df = pd.DataFrame(rows)
    print(var_df.to_string(index=False))
    var_df.to_csv(os.path.join(out, "multiseed_variability.csv"), index=False, encoding="utf-8-sig")
    _to_latex(var_df, os.path.join(out, "multiseed_variability.tex"),
              caption="Variabilidade inter-seed do GA: coeficiente de variação e amplitude.",
              label="tab:variability")

    print(f"\n  Salvo: multiseed_variability.csv")
    return var_df


# ====================================================================
# UTILITÁRIOS
# ====================================================================

def _wilcoxon_test(x, y, name: str, label_x: str, label_y: str, out: str = None):
    """Executa e imprime teste de Wilcoxon pareado."""
    print(f"\n  ── Teste de Wilcoxon: {name} ──")
    diffs = y - x
    n = len(x)

    report = [f"Teste de Wilcoxon: {name}", f"  n = {n}", f"  {label_x} vs {label_y}"]

    if np.all(diffs == 0):
        msg = "    Diferenças todas zero — teste não aplicável."
        print(msg)
        report.append(msg)
        _append_stats_report(report, out)
        return

    if not HAS_SCIPY:
        print("    ⚠ scipy não instalado.")
        return

    try:
        stat, p_value = wilcoxon(x, y, alternative="two-sided")
        sig = "SIM" if p_value < 0.05 else "NÃO"
        print(f"    n={n}, W={stat}, p={p_value:.6f}")
        print(f"    Significante (α=0.05): {sig}")
        report.extend([f"  W = {stat}", f"  p = {p_value:.6f}", f"  Significante (α=0.05): {sig}"])

        if p_value >= 0.05:
            msg = f"    → Não há evidência estatística de diferença entre {label_x} e {label_y}."
        else:
            med_diff = np.median(diffs)
            if med_diff > 0:
                msg = f"    → {label_y} tende a ter valores MAIORES que {label_x}."
            else:
                msg = f"    → {label_y} tende a ter valores MENORES que {label_x}."
        print(msg)
        report.append(msg)

        # Effect size: r = Z / sqrt(n)
        from scipy.stats import norm
        z = norm.ppf(p_value / 2)
        r_effect = abs(z) / np.sqrt(n)
        magnitude = "grande" if r_effect >= 0.5 else "médio" if r_effect >= 0.3 else "pequeno"
        es_msg = f"    Tamanho de efeito: r={r_effect:.3f} ({magnitude})"
        print(es_msg)
        report.append(es_msg)

    except Exception as e:
        msg = f"    Falha: {e}"
        print(msg)
        report.append(msg)

    _append_stats_report(report, out)


def _append_stats_report(lines: list, out: str):
    """Appends statistical test results to the report file."""
    if out is None:
        return
    path = os.path.join(out, "multiseed_statistical_tests.txt")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + "\n".join(lines) + "\n" + "-" * 60 + "\n")


def _to_latex(df, path, caption="", label=""):
    """Salva DataFrame como tabela LaTeX."""
    try:
        n_cols = len(df.columns)
        col_fmt = "l" + "r" * (n_cols - 1)
        latex = df.to_latex(
            index=False, column_format=col_fmt, escape=True,
            caption=caption, label=label, position="htbp",
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(latex)
    except Exception:
        pass


# ── Gráficos ──────────────────────────────────────────────────────────

def _plot_rq1_multiseed(merged, rq1_df, out):
    """Boxplot RQ1: custo A vs B por instância (multi-seed)."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # (a) Boxplot custo
    ax = axes[0]
    instances = rq1_df["Instância"].tolist()
    data_a, data_b = [], []
    for inst in INSTANCE_ORDER:
        m = merged[merged["instance"] == inst]
        data_a.append((m["custo_total_folha_A"] / 1e6).values)
        data_b.append((m["custo_total_folha_B"] / 1e6).values)

    x = np.arange(len(instances))
    w = 0.35
    bp_a = ax.boxplot(data_a, positions=x - w/2, widths=w*0.8, patch_artist=True,
                      boxprops=dict(facecolor=COLORS["A_GA_noBE"], alpha=0.7))
    bp_b = ax.boxplot(data_b, positions=x + w/2, widths=w*0.8, patch_artist=True,
                      boxprops=dict(facecolor=COLORS["B_GA_BE"], alpha=0.7))
    ax.set_xticks(x)
    ax.set_xticklabels(instances, rotation=35, ha="right")
    ax.set_ylabel("Custo Total (R$ milhões)")
    ax.set_title("(a) Distribuição de Custo — GA s/ BE vs GA c/ BE")
    ax.legend([bp_a["boxes"][0], bp_b["boxes"][0]], ["GA s/ BE (A)", "GA c/ BE (B)"])

    # (b) Δ% por instância (boxplot)
    ax = axes[1]
    delta_data = []
    for inst in INSTANCE_ORDER:
        m = merged[merged["instance"] == inst]
        delta_data.append(m["delta_pct"].values)
    ax.boxplot(delta_data, labels=instances)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.7)
    ax.set_ylabel("Δ Custo (%)")
    ax.set_title("(b) Variação de Custo com BE ativado")
    ax.set_xticklabels(instances, rotation=35, ha="right")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(out, f"multiseed_RQ1_boxplot.{ext}"))
    plt.close()
    print("  Gráfico salvo: multiseed_RQ1_boxplot.png/pdf")


def _plot_rq2_multiseed(rq2_df, out):
    """Gráfico RQ2: gap GA vs MILP com barras de erro."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    instances = rq2_df["Instância"].tolist()
    x = np.arange(len(instances))

    # (a) Custo GA (com DP) vs MILP
    ax = axes[0]
    ga_mean = rq2_df["Custo_GA_Média (R$M)"].values
    ga_dp = rq2_df["Custo_GA_DP (R$M)"].values
    milp_val = rq2_df["Custo_MILP (R$M)"].values
    w = 0.35
    ax.bar(x - w/2, milp_val, w, label="MILP c/ BE", color=COLORS["C_MILP_BE"], alpha=0.8)
    ax.bar(x + w/2, ga_mean, w, yerr=ga_dp, label="GA c/ BE (média±DP)", color=COLORS["B_GA_BE"],
           alpha=0.8, capsize=4)
    ax.set_xticks(x)
    ax.set_xticklabels(instances, rotation=35, ha="right")
    ax.set_ylabel("Custo Total (R$ milhões)")
    ax.set_title("(a) Custo: MILP vs GA (5 seeds)")
    ax.legend()

    # (b) Gap % com barras de erro
    ax = axes[1]
    gap_mean = rq2_df["Gap_Média (%)"].values
    gap_dp = rq2_df["Gap_DP (%)"].values
    colors = ["#4CAF50" if g < 0 else "#F44336" for g in gap_mean]
    ax.bar(x, gap_mean, yerr=gap_dp, color=colors, alpha=0.8, capsize=4)
    ax.axhline(y=0, color="gray", linestyle="--", alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(instances, rotation=35, ha="right")
    ax.set_ylabel("Gap (%)")
    ax.set_title("(b) Gap de Custo GA vs MILP (média±DP)")

    plt.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(os.path.join(out, f"multiseed_RQ2_gap.{ext}"))
    plt.close()
    print("  Gráfico salvo: multiseed_RQ2_gap.png/pdf")


# ====================================================================
# MAIN
# ====================================================================

def main():
    parser = argparse.ArgumentParser(description="Análise consolidada multi-seed")
    parser.add_argument("--original", default=os.path.join(RESULTS_DIR, "experiment_metrics.csv"),
                        help="CSV dos resultados originais (seed 42)")
    parser.add_argument("--multiseed", default=os.path.join(RESULTS_DIR, "experiment_metrics_multiseed.csv"),
                        help="CSV dos resultados multi-seed")
    parser.add_argument("--milp-nobe", default=os.path.join(RESULTS_DIR, "experiment_metrics_milp_noBE.csv"),
                        help="CSV dos resultados MILP sem BE")
    args = parser.parse_args()

    os.makedirs(ANALYSIS_DIR, exist_ok=True)

    # Limpar relatório estatístico anterior
    stats_path = os.path.join(ANALYSIS_DIR, "multiseed_statistical_tests.txt")
    with open(stats_path, "w", encoding="utf-8") as f:
        f.write(f"TESTES ESTATÍSTICOS — MULTI-SEED\n")
        f.write(f"Gerado: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write("=" * 60 + "\n")

    # 1. Carregar e consolidar
    df = load_and_consolidate(args.original, args.multiseed, args.milp_nobe)

    # Salvar CSV consolidado
    consolidated_path = os.path.join(ANALYSIS_DIR, "multiseed_consolidated.csv")
    df.to_csv(consolidated_path, index=False, encoding="utf-8-sig")
    print(f"  Salvo: {consolidated_path}")

    # 2. Tabela resumo
    summary_table(df, ANALYSIS_DIR)

    # 3. RQ1 multi-seed
    analyze_rq1_multiseed(df, ANALYSIS_DIR)

    # 4. RQ2 multi-seed
    analyze_rq2_multiseed(df, ANALYSIS_DIR)

    # 5. Variabilidade
    analyze_variability(df, ANALYSIS_DIR)

    print("\n" + "=" * 78)
    print("  ANÁLISE MULTI-SEED CONCLUÍDA")
    print(f"  Resultados em: {ANALYSIS_DIR}")
    print("=" * 78)


if __name__ == "__main__":
    main()

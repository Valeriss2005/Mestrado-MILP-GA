#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_results.py
==================
Análise estatística dos resultados do experimento.

Lê o CSV de métricas (15 linhas: 5 instâncias × 3 cenários) e produz:
  1. Tabelas comparativas formatadas
  2. Teste de Wilcoxon pareado (RQ1: BE vs sem-BE; RQ2: MILP vs GA)
  3. Gráficos comparativos
  4. Resumo executivo

Uso:
  python scripts/analyze_results.py --input data/results/experiment_metrics.csv
"""

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd

# Tenta importar scipy; se não disponível, pula testes
try:
    from scipy.stats import wilcoxon
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# ============================================================================
# CARREGAMENTO
# ============================================================================

def load_metrics(csv_path):
    """Carrega o CSV de métricas."""
    df = pd.read_csv(csv_path, encoding='utf-8')
    print(f"Métricas carregadas: {len(df)} linhas de {csv_path}")
    return df


# ============================================================================
# RQ1: IMPACTO DO BEM-ESTAR NO CUSTO
# ============================================================================

def analyze_rq1(df, output_dir):
    """
    RQ1: Vale a pena incorporar variáveis de bem-estar?
    Compara: GA sem BE (cenário A) vs GA com BE (cenário B)
    """
    print("\n" + "=" * 75)
    print("  RQ1: IMPACTO DAS VARIÁVEIS DE BEM-ESTAR NO CUSTO")
    print("=" * 75)

    df_a = df[df["scenario_id"] == "A_GA_noBE"].sort_values("instance_id").reset_index(drop=True)
    df_b = df[df["scenario_id"] == "B_GA_BE"].sort_values("instance_id").reset_index(drop=True)

    if len(df_a) == 0 or len(df_b) == 0:
        print("  ERRO: Dados insuficientes para RQ1. Verifique se os cenários A e B foram executados.")
        return

    # Tabela comparativa
    comp = pd.DataFrame({
        "Instância": df_a["instance_id"].values,
        "Custo_sem_BE": df_a["custo_total_folha"].values,
        "Custo_com_BE": df_b["custo_total_folha"].values,
    })
    comp["Delta_R$"] = comp["Custo_com_BE"] - comp["Custo_sem_BE"]
    comp["Delta_%"] = ((comp["Custo_com_BE"] - comp["Custo_sem_BE"]) / comp["Custo_sem_BE"] * 100).round(2)

    print("\n  Comparação de Custo Total de Folha:")
    print("  " + "-" * 70)
    print(comp.to_string(index=False))
    print("  " + "-" * 70)

    # Estatísticas descritivas
    print(f"\n  Média Δ%:   {comp['Delta_%'].mean():.2f}%")
    print(f"  Mediana Δ%: {comp['Delta_%'].median():.2f}%")
    print(f"  Min Δ%:     {comp['Delta_%'].min():.2f}%")
    print(f"  Max Δ%:     {comp['Delta_%'].max():.2f}%")

    # Violações de BE
    if "viol_distancia" in df_b.columns:
        be_table = pd.DataFrame({
            "Instância": df_b["instance_id"].values,
            "Viol_Dist_semBE": df_a["viol_distancia"].fillna(0).values,
            "Viol_Dist_comBE": df_b["viol_distancia"].fillna(0).values,
            "Viol_Auto_semBE": df_a["viol_autoexclusao"].fillna(0).values,
            "Viol_Auto_comBE": df_b["viol_autoexclusao"].fillna(0).values,
            "Viol_Desc_semBE": df_a["viol_descompressao"].fillna(0).values,
            "Viol_Desc_comBE": df_b["viol_descompressao"].fillna(0).values,
        })
        print("\n  Violações de Bem-Estar:")
        print("  " + "-" * 70)
        print(be_table.to_string(index=False))

    # Teste de Wilcoxon
    if HAS_SCIPY and len(comp) >= 5:
        custo_sem = comp["Custo_sem_BE"].values.astype(float)
        custo_com = comp["Custo_com_BE"].values.astype(float)
        diffs = custo_com - custo_sem

        if np.all(diffs == 0):
            print("\n  Teste de Wilcoxon: Diferenças todas zero — não aplicável.")
        else:
            try:
                stat, p_value = wilcoxon(custo_sem, custo_com, alternative='two-sided')
                print(f"\n  Teste de Wilcoxon (bicaudal, n={len(comp)}):")
                print(f"    Estatística W:  {stat}")
                print(f"    p-valor:        {p_value:.4f}")
                print(f"    Significante (α=0.05): {'SIM' if p_value < 0.05 else 'NÃO'}")

                if p_value < 0.05:
                    direction = "AUMENTA" if comp["Delta_%"].median() > 0 else "DIMINUI"
                    print(f"    Conclusão: Incorporar BE {direction} significativamente o custo.")
                else:
                    print(f"    Conclusão: Não há evidência estatística de diferença significativa no custo.")
            except Exception as e:
                print(f"\n  Teste de Wilcoxon falhou: {e}")
    elif not HAS_SCIPY:
        print("\n  ⚠ scipy não instalado — teste de Wilcoxon não disponível.")
        print("    Instale com: pip install scipy")

    # Gráfico
    if HAS_MATPLOTLIB:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        x = np.arange(len(comp))
        width = 0.35

        ax1.bar(x - width/2, comp["Custo_sem_BE"] / 1e6, width, label='Sem BE', color='#2196F3')
        ax1.bar(x + width/2, comp["Custo_com_BE"] / 1e6, width, label='Com BE', color='#4CAF50')
        ax1.set_xlabel('Instância')
        ax1.set_ylabel('Custo Total (R$ milhões)')
        ax1.set_title('RQ1: Custo Total — Sem BE vs Com BE')
        ax1.set_xticks(x)
        ax1.set_xticklabels(comp["Instância"], rotation=45, ha='right')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)

        ax2.bar(x, comp["Delta_%"], color=['#f44336' if d > 0 else '#4CAF50' for d in comp["Delta_%"]])
        ax2.set_xlabel('Instância')
        ax2.set_ylabel('Δ Custo (%)')
        ax2.set_title('RQ1: Impacto Percentual do Bem-Estar no Custo')
        ax2.set_xticks(x)
        ax2.set_xticklabels(comp["Instância"], rotation=45, ha='right')
        ax2.axhline(y=0, color='black', linewidth=0.5)
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        fig_path = os.path.join(output_dir, "RQ1_custo_BE_comparison.png")
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n  Gráfico salvo: {fig_path}")

    # Salvar tabela
    comp_path = os.path.join(output_dir, "RQ1_comparison_table.csv")
    comp.to_csv(comp_path, index=False, encoding='utf-8')
    print(f"  Tabela salva: {comp_path}")


# ============================================================================
# RQ2: MILP vs GA (DESEMPENHO)
# ============================================================================

def analyze_rq2(df, output_dir):
    """
    RQ2: Qual abordagem resolve melhor o problema com BE?
    Compara: GA com BE (cenário B) vs MILP com BE (cenário C)
    """
    print("\n" + "=" * 75)
    print("  RQ2: COMPARAÇÃO DE DESEMPENHO — MILP vs GA")
    print("=" * 75)

    df_b = df[df["scenario_id"] == "B_GA_BE"].sort_values("instance_id").reset_index(drop=True)
    df_c = df[df["scenario_id"] == "C_MILP_BE"].sort_values("instance_id").reset_index(drop=True)

    if len(df_b) == 0 or len(df_c) == 0:
        print("  ERRO: Dados insuficientes para RQ2. Verifique se os cenários B e C foram executados.")
        return

    # Tabela de custo
    comp_custo = pd.DataFrame({
        "Instância": df_b["instance_id"].values,
        "Custo_GA": df_b["custo_total_folha"].values,
        "Custo_MILP": df_c["custo_total_folha"].values,
    })
    comp_custo["Delta_%"] = ((comp_custo["Custo_GA"] - comp_custo["Custo_MILP"]) / comp_custo["Custo_MILP"] * 100).round(2)

    print("\n  Comparação de Custo (GA vs MILP, ambos com BE):")
    print("  " + "-" * 70)
    print(comp_custo.to_string(index=False))
    print("  " + "-" * 70)

    # Tabela de tempo
    comp_tempo = pd.DataFrame({
        "Instância": df_b["instance_id"].values,
        "Tempo_GA_s": df_b["tempo_execucao_s"].values,
        "Tempo_MILP_s": df_c["tempo_execucao_s"].values,
    })
    comp_tempo["Speedup"] = (comp_tempo["Tempo_MILP_s"] / comp_tempo["Tempo_GA_s"]).round(2)

    print("\n  Comparação de Tempo de Execução:")
    print("  " + "-" * 70)
    print(comp_tempo.to_string(index=False))
    print("  " + "-" * 70)

    # Tabela de cobertura
    comp_cob = pd.DataFrame({
        "Instância": df_b["instance_id"].values,
        "%Func_GA": df_b["perc_funcionarios_alocados"].values,
        "%Func_MILP": df_c["perc_funcionarios_alocados"].values,
        "Status_MILP": df_c["status_solver"].values,
    })
    print("\n  Comparação de Cobertura e Status:")
    print("  " + "-" * 70)
    print(comp_cob.to_string(index=False))

    # Testes de Wilcoxon
    if HAS_SCIPY and len(comp_custo) >= 5:
        print(f"\n  Testes de Wilcoxon (bicaudal, n={len(comp_custo)}):")

        # Custo
        try:
            custo_ga = comp_custo["Custo_GA"].values.astype(float)
            custo_milp = comp_custo["Custo_MILP"].values.astype(float)
            if not np.all(custo_ga == custo_milp):
                stat_c, p_c = wilcoxon(custo_ga, custo_milp, alternative='two-sided')
                print(f"\n    CUSTO: W={stat_c}, p={p_c:.4f} — {'Significante' if p_c < 0.05 else 'Não significante'}")
                if p_c < 0.05:
                    melhor = "MILP" if comp_custo["Delta_%"].median() > 0 else "GA"
                    print(f"    → {melhor} produz custo significativamente menor.")
            else:
                print(f"\n    CUSTO: Valores idênticos — sem diferença.")
        except Exception as e:
            print(f"\n    CUSTO: Teste falhou — {e}")

        # Tempo
        try:
            tempo_ga = comp_tempo["Tempo_GA_s"].values.astype(float)
            tempo_milp = comp_tempo["Tempo_MILP_s"].values.astype(float)
            if not np.all(tempo_ga == tempo_milp):
                stat_t, p_t = wilcoxon(tempo_ga, tempo_milp, alternative='two-sided')
                print(f"\n    TEMPO: W={stat_t}, p={p_t:.4f} — {'Significante' if p_t < 0.05 else 'Não significante'}")
                if p_t < 0.05:
                    mais_rapido = "GA" if comp_tempo["Speedup"].median() > 1 else "MILP"
                    print(f"    → {mais_rapido} é significativamente mais rápido.")
            else:
                print(f"\n    TEMPO: Valores idênticos — sem diferença.")
        except Exception as e:
            print(f"\n    TEMPO: Teste falhou — {e}")

    # Gráficos
    if HAS_MATPLOTLIB:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        x = np.arange(len(comp_custo))
        width = 0.35

        # Custo
        axes[0].bar(x - width/2, comp_custo["Custo_GA"] / 1e6, width, label='GA', color='#FF9800')
        axes[0].bar(x + width/2, comp_custo["Custo_MILP"] / 1e6, width, label='MILP', color='#9C27B0')
        axes[0].set_xlabel('Instância')
        axes[0].set_ylabel('Custo (R$ milhões)')
        axes[0].set_title('RQ2: Custo Total — GA vs MILP')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(comp_custo["Instância"], rotation=45, ha='right')
        axes[0].legend()
        axes[0].grid(axis='y', alpha=0.3)

        # Tempo (log scale)
        axes[1].bar(x - width/2, comp_tempo["Tempo_GA_s"], width, label='GA', color='#FF9800')
        axes[1].bar(x + width/2, comp_tempo["Tempo_MILP_s"], width, label='MILP', color='#9C27B0')
        axes[1].set_xlabel('Instância')
        axes[1].set_ylabel('Tempo (s)')
        axes[1].set_title('RQ2: Tempo de Execução — GA vs MILP')
        axes[1].set_yscale('log')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(comp_tempo["Instância"], rotation=45, ha='right')
        axes[1].legend()
        axes[1].grid(axis='y', alpha=0.3)

        # Gap de custo (%)
        axes[2].bar(x, comp_custo["Delta_%"],
                     color=['#f44336' if d > 0 else '#4CAF50' for d in comp_custo["Delta_%"]])
        axes[2].set_xlabel('Instância')
        axes[2].set_ylabel('Δ Custo GA vs MILP (%)')
        axes[2].set_title('RQ2: Gap de Qualidade do GA')
        axes[2].axhline(y=0, color='black', linewidth=0.5)
        axes[2].set_xticks(x)
        axes[2].set_xticklabels(comp_custo["Instância"], rotation=45, ha='right')
        axes[2].grid(axis='y', alpha=0.3)

        plt.tight_layout()
        fig_path = os.path.join(output_dir, "RQ2_MILP_vs_GA_comparison.png")
        plt.savefig(fig_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n  Gráfico salvo: {fig_path}")

    # Salvar tabelas
    comp_custo.to_csv(os.path.join(output_dir, "RQ2_cost_comparison.csv"), index=False)
    comp_tempo.to_csv(os.path.join(output_dir, "RQ2_time_comparison.csv"), index=False)
    print(f"  Tabelas salvas em: {output_dir}")


# ============================================================================
# RESUMO EXECUTIVO
# ============================================================================

def executive_summary(df, output_dir):
    """Gera um resumo executivo do experimento."""

    print("\n" + "=" * 75)
    print("  RESUMO EXECUTIVO DO EXPERIMENTO")
    print("=" * 75)

    n_instances = df["instance_id"].nunique()
    n_scenarios = df["scenario_id"].nunique()
    n_runs = len(df)

    print(f"\n  Instâncias:  {n_instances}")
    print(f"  Cenários:    {n_scenarios}")
    print(f"  Execuções:   {n_runs}")

    # Overview por cenário
    overview = df.groupby("scenario_id").agg({
        "custo_total_folha": ["mean", "std"],
        "tempo_execucao_s": ["mean", "std"],
        "perc_funcionarios_alocados": ["mean"],
        "total_alocacoes": ["mean"],
    }).round(2)

    print(f"\n  Resumo por Cenário:")
    print(overview.to_string())

    # Salvar resumo completo
    summary_path = os.path.join(output_dir, "experiment_summary.csv")
    df.to_csv(summary_path, index=False, encoding='utf-8')
    print(f"\n  Resumo completo salvo: {summary_path}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Análise estatística dos resultados do experimento."
    )
    parser.add_argument(
        "--input", type=str, default="data/results/experiment_metrics.csv",
        help="CSV de métricas"
    )
    parser.add_argument(
        "--output", type=str, default="data/results/",
        help="Diretório de saída para gráficos e tabelas"
    )

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"ERRO: Arquivo de métricas não encontrado: {args.input}")
        print(f"\nAntes de analisar, execute o experimento e preencha o CSV.")
        print(f"Use: python scripts/run_experiment.py --config configs/experiment_config.json")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    df = load_metrics(args.input)

    if len(df) < 10:
        print(f"\nAVISO: Apenas {len(df)} execuções encontradas. Esperadas 15.")
        print(f"Os testes estatísticos podem não ser significativos.")

    # Análises
    analyze_rq1(df, args.output)
    analyze_rq2(df, args.output)
    executive_summary(df, args.output)

    print("\n" + "=" * 75)
    print("  ANÁLISE CONCLUÍDA")
    print("=" * 75)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_multiseed.py — Execução de seeds adicionais para o GA
==========================================================
Roda cenários A e B do GA com múltiplas seeds para aumentar
o poder estatístico do experimento (n=5 → n=25 com 5 seeds).

O MILP é determinístico e não precisa ser re-executado.

Uso:
  python scripts/run_multiseed.py                          # 4 seeds novas (123,456,789,2026)
  python scripts/run_multiseed.py --seeds 123 456          # Seeds específicas
  python scripts/run_multiseed.py --instance I1_SMALL      # Só uma instância
  python scripts/run_multiseed.py --scenario A             # Só cenário A
  python scripts/run_multiseed.py --instance I1_SMALL --seeds 123  # 1 run específico

Resultados salvos em: data/results/experiment_metrics_multiseed.csv
"""

import sys, os, csv, time, gc, argparse
from datetime import datetime

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ["PYTHONUTF8"] = "1"

import numpy as np
import pandas as pd

INSTANCES_DIR = os.path.join(ROOT, "data", "instances")
RESULTS_DIR   = os.path.join(ROOT, "data", "results")
METRICS_CSV   = os.path.join(RESULTS_DIR, "experiment_metrics_multiseed.csv")

os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Reuse definitions from run_all ────────────────────────────────────────
INSTANCES = {
    "I1_SMALL":     {"zip": "SMALL_V15.zip",      "nf": 220,  "np": 60},
    "I2_LARGE_05X": {"zip": "LARGE_05X_V01.zip",  "nf": 600,  "np": 160},
    "I3_LARGE":     {"zip": "LARGE_V31.zip",       "nf": 1200, "np": 320},
    "I4_LARGE_15X": {"zip": "LARGE_15X_V01.zip",  "nf": 1800, "np": 480},
    "I5_LARGE_25X": {"zip": "LARGE_25X_V01.zip",  "nf": 3000, "np": 800},
}

DEFAULT_TOLS = {
    "TOL_COMPOSICAO":          0.01,
    "TOL_TREINO":              0.02,
    "TOL_PESSOAS_ALOCADAS":    0.05,
    "TOL_COBERTURA_PROJETOS":  0.00,
    "TOL_PAPEIS":              0.00,
    "TOL_LIM_FUNC_SOC_DIR_GS": 0.00,
    "TOL_LIM_FUNC_OUTROS":    0.00,
    "TOL_DIST":                0.00,
    "TOL_AUTO":                0.00,
    "TOL_DESC":                0.00,
    "TOL_SDEM_GLOBAL":         0.00,
    "TOL_SDEM_LOCAL":          0.00,
}

NEW_SEEDS = [123, 456, 789, 2026]

CSV_HEADER = [
    "run_id", "instance", "scenario", "model", "ativar_bem_estar",
    "zip_file", "timestamp",
    "TOL_COMPOSICAO", "TOL_TREINO", "TOL_PESSOAS_ALOCADAS",
    "status_solver", "custo_total_folha",
    "funcionarios_alocados", "total_funcionarios", "perc_funcionarios_alocados",
    "total_alocacoes", "projetos_ativos", "total_projetos",
    "upgrades", "perc_upgrades", "media_pessoas_projeto",
    "viol_distancia", "viol_autoexclusao", "viol_descompressao", "viol_treino",
    "fitness_final", "tempo_execucao_s", "gap_otimalidade", "geracoes_ga",
    "ga_seed", "ga_geracoes_max", "ga_ilhas", "ga_pop_ilha",
    "PESO_DIST", "PESO_AUTO", "PESO_DESC", "PESO_TREINO",
    "PESO_HARD", "PESO_DESVIO_COMP", "PESO_SDEM",
]

# ── Helpers ───────────────────────────────────────────────────────────────

def get_zip_path(inst_id):
    return os.path.join(INSTANCES_DIR, INSTANCES[inst_id]["zip"])


def set_tolerances(par_dict):
    for k, v in DEFAULT_TOLS.items():
        par_dict[k] = v


def init_csv():
    if not os.path.isfile(METRICS_CSV):
        with open(METRICS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADER).writeheader()
        print(f"  CSV criado: {METRICS_CSV}")


def append_csv(row):
    with open(METRICS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER, extrasaction="ignore")
        w.writerow(row)


def is_run_done(inst_id, scenario, seed):
    """Check if a specific run (instance+scenario+seed) already exists."""
    if not os.path.isfile(METRICS_CSV):
        return False
    with open(METRICS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("instance") == inst_id
                    and row.get("scenario") == scenario
                    and str(row.get("ga_seed")) == str(seed)):
                return True
    return False


def format_time(seconds):
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ── Import BE violations calculator from run_all ─────────────────────────
# (avoid duplicating ~100 lines of code)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from run_all import compute_be_violations


# ── Run GA with specific seed ────────────────────────────────────────────

def run_ga_seed(inst_id, ativar_bem_estar, seed, run_label):
    """Run GA for one instance/scenario/seed. Returns a metrics dict."""
    # Reimport to reset module state between runs
    import importlib
    import models.ga_model as gm
    importlib.reload(gm)
    from models.ga_model import executar_ga_completo, PAR as GA_PAR

    zip_path = get_zip_path(inst_id)
    scenario = "B_GA_BE" if ativar_bem_estar else "A_GA_noBE"

    # Output directory: per instance/scenario/seed
    run_dir = os.path.join(RESULTS_DIR, f"{inst_id}_{scenario}_seed{seed}")
    os.makedirs(run_dir, exist_ok=True)
    gm.OUTPUT_DIR = run_dir

    print(f"\n{'='*70}")
    print(f"  RUN {run_label}: {inst_id} | {scenario} | seed={seed}")
    print(f"  ZIP: {INSTANCES[inst_id]['zip']}")
    print(f"  BE:  {'ATIVADO' if ativar_bem_estar else 'DESATIVADO'}")
    print(f"{'='*70}")

    # Set tolerances and seed
    set_tolerances(GA_PAR)
    GA_PAR["ARQUIVO_ZIP"] = zip_path
    GA_PAR["GA_SEED"] = seed

    t0 = time.time()
    resultado_ga, case, metricas = executar_ga_completo(
        zip_path, ativar_bem_estar=ativar_bem_estar, skip_reports=True
    )
    tempo_total = time.time() - t0

    # ── Extract violations ──
    x_active = set(resultado_ga["x"].keys())
    print(f"\n  Computando violações de BE...")
    viol_dist, viol_auto, viol_desc = compute_be_violations(x_active, zip_path)

    viol_treino = 0
    if hasattr(case, '__contains__') and "treino" in case:
        treino_mask = case["treino"]
        func_ids = case["func_ids"]
        proj_ids = case["proj_ids"]
        f2i = {int(fid): i for i, fid in enumerate(func_ids)}
        p2j = {int(pid): j for j, pid in enumerate(proj_ids)}
        for (fid, pid) in x_active:
            i = f2i.get(fid)
            j = p2j.get(pid)
            if i is not None and j is not None and treino_mask[i, j]:
                viol_treino += 1

    row = {
        "run_id": run_label,
        "instance": inst_id,
        "scenario": scenario,
        "model": "GA",
        "ativar_bem_estar": ativar_bem_estar,
        "zip_file": INSTANCES[inst_id]["zip"],
        "timestamp": datetime.now().isoformat(),
        "TOL_COMPOSICAO": DEFAULT_TOLS["TOL_COMPOSICAO"],
        "TOL_TREINO": DEFAULT_TOLS["TOL_TREINO"],
        "TOL_PESSOAS_ALOCADAS": DEFAULT_TOLS["TOL_PESSOAS_ALOCADAS"],
        "status_solver": metricas["status"],
        "custo_total_folha": round(metricas["custo_total"], 2),
        "funcionarios_alocados": metricas["funcionarios_alocados"],
        "total_funcionarios": metricas["total_funcionarios"],
        "perc_funcionarios_alocados": round(metricas["perc_funcionarios_alocados"], 2),
        "total_alocacoes": metricas["total_alocacoes"],
        "projetos_ativos": metricas["projetos_ativos"],
        "total_projetos": metricas["total_projetos"],
        "upgrades": metricas["upgrades"],
        "perc_upgrades": round(metricas["perc_upgrades"], 2),
        "media_pessoas_projeto": round(metricas["media_pessoas_projeto"], 2),
        "viol_distancia": viol_dist,
        "viol_autoexclusao": viol_auto,
        "viol_descompressao": viol_desc,
        "viol_treino": viol_treino,
        "fitness_final": round(resultado_ga["fitness"][0], 2),
        "tempo_execucao_s": round(metricas["tempo_execucao"], 2),
        "gap_otimalidade": "",
        "geracoes_ga": resultado_ga.get("geracoes", ""),
        "ga_seed": seed,
        "ga_geracoes_max": GA_PAR["GA_GER"],
        "ga_ilhas": GA_PAR["ILHAS_NUM"],
        "ga_pop_ilha": GA_PAR["ILHA_POP"],
        "PESO_DIST": GA_PAR["PESO_DIST"],
        "PESO_AUTO": GA_PAR["PESO_AUTO"],
        "PESO_DESC": GA_PAR["PESO_DESC"],
        "PESO_TREINO": GA_PAR["PESO_TREINO"],
        "PESO_HARD": GA_PAR["PESO_HARD"],
        "PESO_DESVIO_COMP": GA_PAR["PESO_DESVIO_COMP"],
        "PESO_SDEM": GA_PAR["PESO_SDEM"],
    }

    append_csv(row)

    print(f"\n  {'─'*50}")
    print(f"  ✓ Seed:       {seed}")
    print(f"  ✓ Custo:      R$ {metricas['custo_total']:,.2f}")
    print(f"  ✓ Fitness:    {resultado_ga['fitness'][0]:,.0f}")
    print(f"  ✓ Tempo:      {metricas['tempo_execucao']:.1f}s ({format_time(metricas['tempo_execucao'])})")
    print(f"  ✓ Alocações:  {metricas['total_alocacoes']}")
    print(f"  ✓ Func aloc:  {metricas['funcionarios_alocados']}/{metricas['total_funcionarios']}")
    print(f"  ✓ Proj ativos: {metricas['projetos_ativos']}/{metricas['total_projetos']}")
    print(f"  ✓ Violações:  dist={viol_dist}, auto={viol_auto}, desc={viol_desc}, treino={viol_treino}")
    print(f"  ✓ Gerações:   {resultado_ga.get('geracoes', '?')}")
    print(f"  {'─'*50}")

    del resultado_ga, case, metricas
    gc.collect()

    return row


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Executa seeds adicionais do GA para aumentar poder estatístico"
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=NEW_SEEDS,
                        help=f"Seeds a executar (default: {NEW_SEEDS})")
    parser.add_argument("--instance", type=str,
                        help="Rodar só uma instância (I1_SMALL, etc.)")
    parser.add_argument("--scenario", type=str, choices=["A", "B"],
                        help="Rodar só um cenário (A=GA-noBE, B=GA-BE)")
    parser.add_argument("--force", action="store_true",
                        help="Forçar re-execução mesmo se run já existe")
    args = parser.parse_args()

    seeds = args.seeds
    instances = list(INSTANCES.keys())
    if args.instance:
        if args.instance not in INSTANCES:
            print(f"ERRO: Instância desconhecida: {args.instance}")
            sys.exit(1)
        instances = [args.instance]

    scenarios = [("A", "A_GA_noBE", False), ("B", "B_GA_BE", True)]
    if args.scenario:
        scenarios = [s for s in scenarios if s[0] == args.scenario]

    total_runs = len(seeds) * len(instances) * len(scenarios)

    print("=" * 70)
    print("  EXPERIMENTO — SEEDS ADICIONAIS DO GA")
    print("=" * 70)
    print(f"  Data:        {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Seeds:       {seeds}")
    print(f"  Instâncias:  {', '.join(instances)}")
    print(f"  Cenários:    {', '.join(s[0] for s in scenarios)}")
    print(f"  Total runs:  {total_runs}")
    print(f"  Resultados:  {METRICS_CSV}")
    print()

    # Estimated times based on seed=42 results
    est_times = {
        "I1_SMALL":     {"A": 147, "B": 23},
        "I2_LARGE_05X": {"A": 734, "B": 149},
        "I3_LARGE":     {"A": 2542, "B": 508},
        "I4_LARGE_15X": {"A": 4791, "B": 5453},
        "I5_LARGE_25X": {"A": 33759, "B": 16200},
    }
    total_est = 0
    for seed in seeds:
        for inst_id in instances:
            for skey, slabel, be in scenarios:
                total_est += est_times.get(inst_id, {}).get(skey, 0)
    print(f"  Tempo estimado total: {format_time(total_est)} (sequencial)")
    print("=" * 70)

    # Verify ZIPs exist
    for inst_id in instances:
        zp = get_zip_path(inst_id)
        if not os.path.isfile(zp):
            print(f"ERRO: ZIP não encontrado: {zp}")
            sys.exit(1)

    init_csv()

    # ── Execute: for each seed, run all instances × scenarios ──
    run_number = 0
    completed = 0
    skipped = 0
    failed = 0
    total_t0 = time.time()

    for seed in seeds:
        print(f"\n{'#'*70}")
        print(f"  SEED {seed}")
        print(f"{'#'*70}")

        for skey, slabel, be in scenarios:
            for inst_id in instances:
                run_number += 1
                run_label = f"S{seed}_{run_number:02d}"

                if not args.force and is_run_done(inst_id, slabel, seed):
                    print(f"\n  SKIP {run_label}: {inst_id} × {slabel} × seed={seed} (já existe)")
                    skipped += 1
                    continue

                try:
                    run_ga_seed(inst_id, be, seed, run_label)
                    completed += 1

                    elapsed = time.time() - total_t0
                    remaining_runs = total_runs - run_number
                    avg_time = elapsed / max(completed, 1)
                    eta = avg_time * remaining_runs
                    print(f"\n  Progresso: {run_number}/{total_runs} "
                          f"| Tempo: {format_time(elapsed)} "
                          f"| ETA: {format_time(eta)}")

                except Exception as e:
                    print(f"\n  ERRO em {run_label}: {e}")
                    import traceback
                    traceback.print_exc()
                    failed += 1
                    continue

    total_elapsed = time.time() - total_t0

    print(f"\n{'='*70}")
    print(f"  EXECUÇÃO FINALIZADA")
    print(f"  Tempo total:  {format_time(total_elapsed)}")
    print(f"  Completados:  {completed}")
    print(f"  Pulados:      {skipped}")
    print(f"  Falhados:     {failed}")
    print(f"  Resultados:   {METRICS_CSV}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

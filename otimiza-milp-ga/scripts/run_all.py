#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all.py — Execução formal das 15 rodadas do experimento
===========================================================
5 instâncias × 3 cenários = 15 execuções

Cenários:
  A (GA_noBE)  — GA sem variáveis de bem-estar (baseline)
  B (GA_BE)    — GA com variáveis de bem-estar
  C (MILP_BE)  — MILP com variáveis de bem-estar (importado de calibração)

Uso:
  python scripts/run_all.py                         # Roda tudo (15 runs)
  python scripts/run_all.py --instance I1_SMALL     # Roda 1 instância (3 cenários)
  python scripts/run_all.py --scenario A            # Roda só cenário A (5 instâncias)
  python scripts/run_all.py --instance I1_SMALL --scenario A  # 1 run específico
  python scripts/run_all.py --skip-milp             # Pula Cenário C (só GA)
  python scripts/run_all.py --rerun-milp            # Re-executa MILP ao invés de importar

Resultados salvos em: data/results/experiment_metrics.csv
"""

import sys, os, csv, json, time, math, argparse, zipfile, gc
from datetime import datetime, timedelta

# ── Path setup ────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ["PYTHONUTF8"] = "1"

import numpy as np
import pandas as pd

INSTANCES_DIR = os.path.join(ROOT, "data", "instances")
RESULTS_DIR   = os.path.join(ROOT, "data", "results")
CONFIG_PATH   = os.path.join(ROOT, "configs", "experiment_config.json")
CALIB_PATH    = os.path.join(RESULTS_DIR, "calibration_results.json")
METRICS_CSV   = os.path.join(RESULTS_DIR, "experiment_metrics.csv")

os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Instance definitions (new v5 design) ─────────────────────────────────
INSTANCES = {
    "I1_SMALL":     {"zip": "SMALL_V15.zip",      "nf": 220,  "np": 60},
    "I2_LARGE_05X": {"zip": "LARGE_05X_V01.zip",  "nf": 600,  "np": 160},
    "I3_LARGE":     {"zip": "LARGE_V31.zip",       "nf": 1200, "np": 320},
    "I4_LARGE_15X": {"zip": "LARGE_15X_V01.zip",  "nf": 1800, "np": 480},
    "I5_LARGE_25X": {"zip": "LARGE_25X_V01.zip",  "nf": 3000, "np": 800},
}

# Default tolerances (calibrated via grid-search)
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

# ── CSV schema ────────────────────────────────────────────────────────────
CSV_HEADER = [
    "run_id", "instance", "scenario", "model", "ativar_bem_estar",
    "zip_file", "timestamp",
    # Tolerâncias
    "TOL_COMPOSICAO", "TOL_TREINO", "TOL_PESSOAS_ALOCADAS",
    # Resultados
    "status_solver", "custo_total_folha",
    "funcionarios_alocados", "total_funcionarios", "perc_funcionarios_alocados",
    "total_alocacoes", "projetos_ativos", "total_projetos",
    "upgrades", "perc_upgrades", "media_pessoas_projeto",
    # Violações BE
    "viol_distancia", "viol_autoexclusao", "viol_descompressao",
    "viol_treino",
    # Performance
    "fitness_final", "tempo_execucao_s", "gap_otimalidade",
    "geracoes_ga",
    # GA config
    "ga_seed", "ga_geracoes_max", "ga_ilhas", "ga_pop_ilha",
    # GA penalty weights (for reproducibility)
    "PESO_DIST", "PESO_AUTO", "PESO_DESC", "PESO_TREINO",
    "PESO_HARD", "PESO_DESVIO_COMP", "PESO_SDEM",
]


# ── Helpers ───────────────────────────────────────────────────────────────

def get_zip_path(inst_id):
    return os.path.join(INSTANCES_DIR, INSTANCES[inst_id]["zip"])


def set_tolerances(par_dict, tols=None):
    """Apply tolerances to a module-level PAR dict."""
    t = tols or DEFAULT_TOLS
    for k, v in DEFAULT_TOLS.items():
        par_dict[k] = t.get(k, v)


def init_csv():
    """Create CSV with header if it doesn't exist."""
    if not os.path.isfile(METRICS_CSV):
        with open(METRICS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADER).writeheader()
        print(f"  CSV criado: {METRICS_CSV}")


def append_csv(row):
    """Append a result row to the CSV."""
    with open(METRICS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER, extrasaction="ignore")
        w.writerow(row)


def is_run_done(inst_id, scenario):
    """Check if a run already exists in the CSV."""
    if not os.path.isfile(METRICS_CSV):
        return False
    with open(METRICS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("instance") == inst_id and row.get("scenario") == scenario:
                return True
    return False


def _read_csv_zip(z, endswith_name, sep=";"):
    """Read a CSV from a zipfile using endswith matching (handles prefix)."""
    names = [n for n in z.namelist() if n.endswith(endswith_name)]
    if not names:
        return pd.DataFrame()
    with z.open(names[0]) as f:
        df = pd.read_csv(f, sep=sep, dtype=str, keep_default_na=False)
    df.columns = [c.encode("utf-8").decode("utf-8-sig").strip() for c in df.columns]
    return df


def _to_float(s):
    return pd.to_numeric(
        s.astype(str).str.replace(",", ".", regex=False),
        errors="coerce"
    )


def _haversine(lat1, lon1, lat2, lon2):
    """Haversine distance in km (scalar)."""
    R = 6371.0
    rlat1, rlon1 = math.radians(lat1), math.radians(lon1)
    rlat2, rlon2 = math.radians(lat2), math.radians(lon2)
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat/2)**2 + math.cos(rlat1)*math.cos(rlat2)*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def compute_be_violations(x_pairs, zip_path):
    """
    Compute BE violation counts for a set of active allocations.
    Works regardless of whether BE was active during optimization.

    Parameters:
      x_pairs: set of (func_id, proj_id) tuples with active allocations
      zip_path: path to instance ZIP

    Returns:
      (viol_dist, viol_auto, viol_desc)
    """
    with zipfile.ZipFile(zip_path, "r") as z:
        df_func = _read_csv_zip(z, "TbFuncionarios.csv")
        df_proj = _read_csv_zip(z, "TbProjetos.csv")
        df_cli  = _read_csv_zip(z, "TbClientes.csv")
        df_auto_df = _read_csv_zip(z, "TbProjetos_Autoexclusao.csv")

    # All columns are strings from _read_csv_zip — convert to numeric
    df_func["ID_Func"] = pd.to_numeric(df_func.get("ID_Func"), errors="coerce").astype("Int64")
    df_proj["ID_Proj"] = pd.to_numeric(df_proj.get("ID_Proj"), errors="coerce").astype("Int64")
    df_proj["ID_Cli"]  = pd.to_numeric(df_proj.get("ID_Cli"), errors="coerce").astype("Int64")
    df_cli["ID_Cli"]   = pd.to_numeric(df_cli.get("ID_Cli"), errors="coerce").astype("Int64")

    # ── Auto-exclusion violations ──
    viol_auto = 0
    if not df_auto_df.empty and "ID_Func" in df_auto_df.columns:
        df_auto_df["ID_Func"] = pd.to_numeric(df_auto_df["ID_Func"], errors="coerce").astype("Int64")
        df_auto_df["ID_Proj"] = pd.to_numeric(df_auto_df["ID_Proj"], errors="coerce").astype("Int64")
        auto_set = set(zip(df_auto_df["ID_Func"].astype(int), df_auto_df["ID_Proj"].astype(int)))
        viol_auto = sum(1 for p in x_pairs if p in auto_set)

    # ── Distance violations (> KM_MAX = 20 km) ──
    viol_dist = 0
    f_lat = {}; f_lon = {}
    if "Latitude_Func" in df_func.columns:
        df_func["Latitude_Func"]  = _to_float(df_func["Latitude_Func"])
        df_func["Longitude_Func"] = _to_float(df_func["Longitude_Func"])
        f_lat = dict(zip(df_func["ID_Func"].dropna().astype(int),
                         df_func["Latitude_Func"]))
        f_lon = dict(zip(df_func["ID_Func"].dropna().astype(int),
                         df_func["Longitude_Func"]))

    c_lat = {}; c_lon = {}
    if "Latitude_Cli" in df_cli.columns:
        df_cli["Latitude_Cli"]  = _to_float(df_cli["Latitude_Cli"])
        df_cli["Longitude_Cli"] = _to_float(df_cli["Longitude_Cli"])
        c_lat = dict(zip(df_cli["ID_Cli"].dropna().astype(int),
                         df_cli["Latitude_Cli"]))
        c_lon = dict(zip(df_cli["ID_Cli"].dropna().astype(int),
                         df_cli["Longitude_Cli"]))

    p_cli = dict(zip(df_proj["ID_Proj"].dropna().astype(int),
                     df_proj["ID_Cli"].dropna().astype(int)))

    KM_MAX = 20.0
    for (fid, pid) in x_pairs:
        cli = p_cli.get(pid)
        if cli is None:
            continue
        la1 = f_lat.get(fid); lo1 = f_lon.get(fid)
        la2 = c_lat.get(cli); lo2 = c_lon.get(cli)
        if la1 is not None and lo1 is not None and la2 is not None and lo2 is not None:
            if not (math.isnan(la1) or math.isnan(lo1) or math.isnan(la2) or math.isnan(lo2)):
                d = _haversine(la1, lo1, la2, lo2)
                if d > KM_MAX:
                    viol_dist += 1

    # ── Decompression violations ──
    # Check if any employee is allocated to two projects that conflict on dates
    viol_desc = 0
    DESC_DIAS = {"P": 1, "M": 2, "G": 3}

    df_proj["Data_Inicio_Proj"] = pd.to_datetime(df_proj.get("Data_Inicio_Proj"), errors="coerce")
    df_proj["Data_Fim_Proj"]    = pd.to_datetime(df_proj.get("Data_Fim_Proj"), errors="coerce")

    col_tam = "Tam_Proj"
    if col_tam not in df_proj.columns:
        for alt in ["Tamanho", "tam_proj", "TAM_PROJ"]:
            if alt in df_proj.columns:
                col_tam = alt
                break

    proj_info = {}
    for _, r in df_proj.iterrows():
        pid = int(r["ID_Proj"]) if pd.notna(r["ID_Proj"]) else None
        if pid is None:
            continue
        proj_info[pid] = {
            "ini": r["Data_Inicio_Proj"],
            "fim": r["Data_Fim_Proj"],
            "tam": str(r.get(col_tam, "M"))
        }

    # Group allocations by employee
    func_projs = {}
    for (fid, pid) in x_pairs:
        func_projs.setdefault(fid, []).append(pid)

    for fid, pids in func_projs.items():
        if len(pids) < 2:
            continue
        for i_idx in range(len(pids)):
            pj = pids[i_idx]
            if pj not in proj_info:
                continue
            info_j = proj_info[pj]
            fim_j = info_j["fim"]
            tam_j = info_j["tam"]
            if pd.isna(fim_j):
                continue
            dias = DESC_DIAS.get(tam_j, 0)
            janela = fim_j + timedelta(days=dias)
            for k_idx in range(len(pids)):
                if i_idx == k_idx:
                    continue
                pk = pids[k_idx]
                if pk not in proj_info:
                    continue
                ini_k = proj_info[pk]["ini"]
                if pd.isna(ini_k):
                    continue
                if ini_k > fim_j and ini_k < janela:
                    viol_desc += 1

    # Each conflict pair is counted twice (j→k and k→j might both trigger)
    # but the MILP counts each direction separately, so we keep it as-is

    return viol_dist, viol_auto, viol_desc


# ── Run GA ────────────────────────────────────────────────────────────────

def run_ga(inst_id, ativar_bem_estar, run_label):
    """Run GA for one instance/scenario. Returns a metrics dict."""
    from models.ga_model import executar_ga_completo, PAR as GA_PAR
    import models.ga_model as gm

    zip_path = get_zip_path(inst_id)
    scenario = "B_GA_BE" if ativar_bem_estar else "A_GA_noBE"
    be_suffix = "BE" if ativar_bem_estar else "NBE"

    # Output directory per run
    run_dir = os.path.join(RESULTS_DIR, f"{inst_id}_{scenario}")
    os.makedirs(run_dir, exist_ok=True)
    gm.OUTPUT_DIR = run_dir

    print(f"\n{'='*70}")
    print(f"  RUN {run_label}: {inst_id} | {scenario} | GA")
    print(f"  ZIP: {INSTANCES[inst_id]['zip']}")
    print(f"  BE:  {'ATIVADO' if ativar_bem_estar else 'DESATIVADO'}")
    print(f"{'='*70}")

    # Set tolerances
    set_tolerances(GA_PAR)
    GA_PAR["ARQUIVO_ZIP"] = zip_path
    GA_PAR["GA_SEED"] = 42

    t0 = time.time()
    resultado_ga, case, metricas = executar_ga_completo(
        zip_path, ativar_bem_estar=ativar_bem_estar
    )
    tempo_total = time.time() - t0

    # ── Extract violation counts ──
    x_active = set(resultado_ga["x"].keys())

    # Compute BE violations post-hoc (works even when BE was disabled)
    print(f"\n  Computando violações de BE...")
    viol_dist, viol_auto, viol_desc = compute_be_violations(x_active, zip_path)

    # Training violations: count allocations where func lacks required training
    # (approximated from the GA fitness breakdown - violations are penalized)
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

    # Build row
    row = {
        "run_id": run_label,
        "instance": inst_id,
        "scenario": scenario,
        "model": "GA",
        "ativar_bem_estar": ativar_bem_estar,
        "zip_file": INSTANCES[inst_id]["zip"],
        "timestamp": datetime.now().isoformat(),
        # Tolerances
        "TOL_COMPOSICAO": DEFAULT_TOLS["TOL_COMPOSICAO"],
        "TOL_TREINO": DEFAULT_TOLS["TOL_TREINO"],
        "TOL_PESSOAS_ALOCADAS": DEFAULT_TOLS["TOL_PESSOAS_ALOCADAS"],
        # Results
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
        # BE violations
        "viol_distancia": viol_dist,
        "viol_autoexclusao": viol_auto,
        "viol_descompressao": viol_desc,
        "viol_treino": viol_treino,
        # Performance
        "fitness_final": round(resultado_ga["fitness"][0], 2),
        "tempo_execucao_s": round(metricas["tempo_execucao"], 2),
        "gap_otimalidade": "",
        "geracoes_ga": resultado_ga.get("geracoes", ""),
        # GA config
        "ga_seed": GA_PAR["GA_SEED"],
        "ga_geracoes_max": GA_PAR["GA_GER"],
        "ga_ilhas": GA_PAR["ILHAS_NUM"],
        "ga_pop_ilha": GA_PAR["ILHA_POP"],
        # Penalty weights
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
    print(f"  ✓ Custo:      R$ {metricas['custo_total']:,.2f}")
    print(f"  ✓ Fitness:    {resultado_ga['fitness'][0]:,.0f}")
    print(f"  ✓ Tempo:      {metricas['tempo_execucao']:.1f}s")
    print(f"  ✓ Alocações:  {metricas['total_alocacoes']}")
    print(f"  ✓ Func aloc:  {metricas['funcionarios_alocados']}/{metricas['total_funcionarios']}")
    print(f"  ✓ Proj ativos: {metricas['projetos_ativos']}/{metricas['total_projetos']}")
    print(f"  ✓ Upgrades:   {metricas['upgrades']}")
    print(f"  ✓ Violações:  dist={viol_dist}, auto={viol_auto}, desc={viol_desc}, treino={viol_treino}")
    print(f"  ✓ Gerações:   {resultado_ga.get('geracoes', '?')}")
    print(f"  ✓ Salvo em:   {METRICS_CSV}")
    print(f"  {'─'*50}")

    # Free memory
    del resultado_ga, case, metricas
    gc.collect()

    return row


# ── Import MILP from calibration ─────────────────────────────────────────

def import_milp_from_calibration(inst_id, run_label):
    """Import MILP Cenário C results from calibration_results.json."""

    with open(CALIB_PATH, "r", encoding="utf-8") as f:
        calib = json.load(f)

    data = calib.get(inst_id)
    if data is None:
        print(f"  ERRO: {inst_id} não encontrada em {CALIB_PATH}")
        return None

    nf = data["total_funcionarios"]
    np_ = data["total_projetos"]
    fa = data["funcionarios_alocados"]
    pa = data["projetos_ativos"]
    ta = data["total_alocacoes"]
    media_pp = round(ta / pa, 2) if pa > 0 else 0

    row = {
        "run_id": run_label,
        "instance": inst_id,
        "scenario": "C_MILP_BE",
        "model": "MILP",
        "ativar_bem_estar": True,
        "zip_file": INSTANCES[inst_id]["zip"],
        "timestamp": datetime.now().isoformat(),
        # Tolerances
        "TOL_COMPOSICAO": data.get("TOL_COMPOSICAO", 0.01),
        "TOL_TREINO": data.get("TOL_TREINO", 0.02),
        "TOL_PESSOAS_ALOCADAS": data.get("TOL_PESSOAS_ALOCADAS", 0.05),
        # Results
        "status_solver": data["status"],
        "custo_total_folha": round(data["custo_total_folha"], 2),
        "funcionarios_alocados": fa,
        "total_funcionarios": nf,
        "perc_funcionarios_alocados": round(data["perc_funcionarios_alocados"], 2),
        "total_alocacoes": ta,
        "projetos_ativos": pa,
        "total_projetos": np_,
        "upgrades": data.get("upgrades", ""),
        "perc_upgrades": data.get("perc_upgrades", ""),
        "media_pessoas_projeto": media_pp,
        # BE violations (MILP with TOL_*=0 → all zero)
        "viol_distancia": data.get("viol_distancia", 0),
        "viol_autoexclusao": data.get("viol_autoexclusao", 0),
        "viol_descompressao": 0,  # TOL_DESC=0 → hard constraint
        "viol_treino": data.get("viol_treino", ""),
        # Performance
        "fitness_final": round(data["custo_total_folha"], 2),
        "tempo_execucao_s": round(data["tempo_total_s"], 2),
        "gap_otimalidade": 0.01,  # GAPREL setting; status=Optimal guarantees ≤ this
        "geracoes_ga": "",
        # GA config (N/A for MILP)
        "ga_seed": "",
        "ga_geracoes_max": "",
        "ga_ilhas": "",
        "ga_pop_ilha": "",
    }

    append_csv(row)

    print(f"\n  ✓ MILP importado de calibração:")
    print(f"    Custo:  R$ {data['custo_total_folha']:,.2f}")
    print(f"    Tempo:  {data['tempo_total_s']:.1f}s")
    print(f"    Status: {data['status']}")
    print(f"    Func:   {fa}/{nf} ({data['perc_funcionarios_alocados']:.1f}%)")
    print(f"    Proj:   {pa}/{np_}")
    print(f"    Viol:   dist={row['viol_distancia']}, auto={row['viol_autoexclusao']}")

    return row


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Executa as 15 rodadas do experimento")
    parser.add_argument("--instance", type=str, help="Rodar só uma instância (I1_SMALL, I2_LARGE_05X, etc.)")
    parser.add_argument("--scenario", type=str, choices=["A", "B", "C"],
                        help="Rodar só um cenário (A=GA-noBE, B=GA-BE, C=MILP-BE)")
    parser.add_argument("--skip-milp", action="store_true",
                        help="Pular Cenário C (MILP) — executar apenas GA")
    parser.add_argument("--rerun-milp", action="store_true",
                        help="Re-executar MILP ao invés de importar da calibração")
    parser.add_argument("--force", action="store_true",
                        help="Forçar re-execução mesmo se run já existe no CSV")
    args = parser.parse_args()

    # ── Determine runs ──
    instances = list(INSTANCES.keys())
    if args.instance:
        if args.instance not in INSTANCES:
            print(f"ERRO: Instância desconhecida: {args.instance}")
            print(f"  Disponíveis: {', '.join(INSTANCES.keys())}")
            sys.exit(1)
        instances = [args.instance]

    scenarios = ["C", "A", "B"]  # MILP first (per protocol), then GA A, then GA B
    if args.scenario:
        scenarios = [args.scenario]
    if args.skip_milp and "C" in scenarios:
        scenarios.remove("C")

    scenario_map = {
        "A": "A_GA_noBE",
        "B": "B_GA_BE",
        "C": "C_MILP_BE",
    }

    total_runs = len(instances) * len(scenarios)

    print("=" * 70)
    print("  EXPERIMENTO DA DISSERTAÇÃO — EXECUÇÃO FORMAL")
    print("=" * 70)
    print(f"  Data:        {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Instâncias:  {', '.join(instances)}")
    print(f"  Cenários:    {', '.join(scenarios)}")
    print(f"  Total runs:  {total_runs}")
    print(f"  Resultados:  {METRICS_CSV}")
    print(f"  MILP fonte:  {'Re-execução' if args.rerun_milp else 'Importado de calibração'}")
    print("=" * 70)

    # Verify instance files exist
    for inst_id in instances:
        zp = get_zip_path(inst_id)
        if not os.path.isfile(zp):
            print(f"ERRO: ZIP não encontrado: {zp}")
            sys.exit(1)

    # Verify calibration file exists (if using it)
    if "C" in scenarios and not args.rerun_milp:
        if not os.path.isfile(CALIB_PATH):
            print(f"ERRO: Calibração não encontrada: {CALIB_PATH}")
            print(f"  Execute --rerun-milp ou rode a calibração primeiro.")
            sys.exit(1)

    # Init CSV
    init_csv()

    # ── Execute ──
    results = []
    run_number = 0
    total_t0 = time.time()

    for scenario_key in scenarios:
        scenario_label = scenario_map[scenario_key]

        for inst_id in instances:
            run_number += 1
            run_label = f"{run_number:02d}"

            # Check if already done
            if not args.force and is_run_done(inst_id, scenario_label):
                print(f"\n  SKIP {run_label}: {inst_id} × {scenario_label} (já existe no CSV)")
                continue

            try:
                if scenario_key == "C":
                    # ── Cenário C: MILP+BE ──
                    if args.rerun_milp:
                        print(f"\n  Re-execução MILP não implementada nesta versão.")
                        print(f"  Use scripts/_calibrate_all.py ou importe da calibração.")
                        continue
                    else:
                        print(f"\n  RUN {run_label}: {inst_id} | C_MILP_BE | MILP (importado)")
                        row = import_milp_from_calibration(inst_id, run_label)

                elif scenario_key == "A":
                    # ── Cenário A: GA sem BE ──
                    row = run_ga(inst_id, ativar_bem_estar=False, run_label=run_label)

                elif scenario_key == "B":
                    # ── Cenário B: GA com BE ──
                    row = run_ga(inst_id, ativar_bem_estar=True, run_label=run_label)

                if row:
                    results.append(row)

            except Exception as e:
                print(f"\n  ERRO no RUN {run_label} ({inst_id} × {scenario_label}): {e}")
                import traceback
                traceback.print_exc()

    total_elapsed = time.time() - total_t0

    # ── Summary ──
    print(f"\n\n{'='*70}")
    print(f"  RESUMO DO EXPERIMENTO")
    print(f"{'='*70}")
    print(f"  Runs completados: {len(results)} / {total_runs}")
    print(f"  Tempo total:      {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")
    print(f"  CSV:              {METRICS_CSV}")

    if results:
        print(f"\n  {'Inst':<15} {'Cenário':<12} {'Modelo':<5} {'Custo':>17} {'Tempo':>8} {'Status':<8}")
        print(f"  {'-'*65}")
        for r in results:
            custo = float(r['custo_total_folha']) if r['custo_total_folha'] else 0
            tempo = float(r['tempo_execucao_s']) if r['tempo_execucao_s'] else 0
            print(f"  {r['instance']:<15} {r['scenario']:<12} {r['model']:<5} "
                  f"R$ {custo:>13,.2f} {tempo:>6.0f}s {r['status_solver']:<8}")

    print(f"\n{'='*70}")
    print(f"  Para análise estatística:")
    print(f"    python scripts/analyze_results.py")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

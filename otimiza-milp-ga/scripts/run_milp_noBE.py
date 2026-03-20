#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_milp_noBE.py — Executa MILP SEM bem-estar para as 5 instâncias
===================================================================
Gera cenário D_MILP_noBE para complementar a análise RQ1.
Salva resultados em data/results/experiment_metrics_milp_noBE.csv
"""

import sys, os, csv, time, math
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ["PYTHONUTF8"] = "1"

from models.milp_model import executar_modelo, PAR

INSTANCES_DIR = os.path.join(ROOT, "data", "instances")
RESULTS_DIR   = os.path.join(ROOT, "data", "results")
OUTPUT_CSV    = os.path.join(RESULTS_DIR, "experiment_metrics_milp_noBE.csv")

INSTANCES = {
    "I1_SMALL":     {"zip": "SMALL_V15.zip",      "nf": 220,  "np": 60},
    "I2_LARGE_05X": {"zip": "LARGE_05X_V01.zip",  "nf": 600,  "np": 160},
    "I3_LARGE":     {"zip": "LARGE_V31.zip",       "nf": 1200, "np": 320},
    "I4_LARGE_15X": {"zip": "LARGE_15X_V01.zip",  "nf": 1800, "np": 480},
    "I5_LARGE_25X": {"zip": "LARGE_25X_V01.zip",  "nf": 3000, "np": 800},
}

CSV_HEADER = [
    "instance", "scenario", "model", "ativar_bem_estar",
    "custo_total_folha", "funcionarios_alocados", "total_funcionarios",
    "perc_funcionarios_alocados", "total_alocacoes", "projetos_ativos",
    "total_projetos", "upgrades",
    "viol_distancia", "viol_autoexclusao", "viol_descompressao",
    "tempo_execucao_s", "status_solver",
]

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


def is_done(inst_id):
    """Check if this instance already has a result."""
    if not os.path.isfile(OUTPUT_CSV):
        return False
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("instance") == inst_id:
                return True
    return False


def run_milp_noBE(inst_id):
    """Run MILP without BE for one instance and return metrics dict."""
    zip_path = os.path.join(INSTANCES_DIR, INSTANCES[inst_id]["zip"])
    if not os.path.isfile(zip_path):
        print(f"  ERRO: ZIP não encontrado: {zip_path}")
        return None

    # Set tolerances
    for k, v in DEFAULT_TOLS.items():
        PAR[k] = v

    print(f"\n{'='*70}")
    print(f"  MILP SEM BE — {inst_id}")
    print(f"  ZIP: {INSTANCES[inst_id]['zip']}")
    print(f"{'='*70}")

    t0 = time.time()
    resultado = executar_modelo(zip_path, ativar_bem_estar=False)
    elapsed = time.time() - t0

    status = resultado.get("status_txt", "???")
    print(f"\n  Status: {status}")
    print(f"  Tempo: {elapsed:.1f}s")

    if status != "Optimal":
        print(f"  ⚠ MILP não atingiu Optimal: {status}")

    # Extract metrics from result dict
    x = resultado.get("x", {})
    y = resultado.get("y", {})
    upgrade_cat = resultado.get("upgrade_cat", {})
    perc_tempo = resultado.get("perc_tempo", {})

    total_x = sum(1 for (i, j) in x if (x[i, j].varValue or 0) >= 0.9)
    total_y = sum(1 for j in y if (y[j].varValue or 0) >= 0.5)
    func_set = set(i for (i, j) in x if (x[i, j].varValue or 0) >= 0.9)
    func_alocados = len(func_set)
    nf = len(resultado.get("funcionarios", []))
    np_ = len(resultado.get("projetos", []))
    perc_func = 100.0 * func_alocados / max(1, nf)

    # Count upgrades
    df_func = resultado["dfs"][0]
    df_proj = resultado["dfs"][1]
    orig_cat = dict(zip(df_func["ID_Func"], df_func["ID_Categ"].astype(int)))
    upgrades = sum(1 for (i, j) in x if (x[i, j].varValue or 0) >= 0.9
                   and upgrade_cat.get(i, orig_cat.get(i, 0)) != orig_cat.get(i, 0))

    # Compute cost
    _categ_map = dict(zip(df_func["ID_Func"], df_func["ID_Categ"].astype(int)))
    _sal_map   = dict(zip(df_func["ID_Func"], df_func["Salario_Hora"].astype(float)))
    _horas_map = dict(zip(df_proj["ID_Proj"], df_proj["Qt_horas_Previstas"].astype(float)))
    custo = 0.0
    for (i, j) in x:
        v = x[i, j].varValue or 0.0
        if v >= 0.9:
            c = _categ_map.get(i, 0)
            horas = _horas_map.get(j, 0.0)
            sal = _sal_map.get(i, 0.0)
            perc = float(perc_tempo.get(c, 100.0)) / 100.0
            custo += sal * horas * perc

    # BE violations: compute post-hoc (even though BE was off, we count what WOULD be violated)
    # Uses the same logic as run_all.py compute_be_violations
    import zipfile
    import pandas as pd
    active_pairs = set((i, j) for (i, j) in x if (x[i, j].varValue or 0) >= 0.9)

    with zipfile.ZipFile(zip_path, "r") as z:
        def _read(name):
            names = [n for n in z.namelist() if n.endswith(name)]
            if not names:
                return pd.DataFrame()
            with z.open(names[0]) as f:
                df = pd.read_csv(f, sep=";", dtype=str, keep_default_na=False)
            df.columns = [c.encode("utf-8").decode("utf-8-sig").strip() for c in df.columns]
            return df

        df_f = _read("TbFuncionarios.csv")
        df_p = _read("TbProjetos.csv")
        df_c = _read("TbClientes.csv")
        df_auto = _read("TbAutoExclusao.csv")

    # Distance violations
    viol_dist = 0
    KM_MAX = PAR.get("KM_MAX", 100)
    try:
        cli_pos = df_c[["ID_Cli", "Latitude_Cli", "Longitude_Cli"]].dropna()
        fun_pos = df_f[["ID_Func", "Latitude_Func", "Longitude_Func"]].dropna()
        proj_cli = dict(zip(
            pd.to_numeric(df_p["ID_Proj"], errors="coerce").dropna().astype(int),
            pd.to_numeric(df_p["ID_Cli"], errors="coerce").dropna().astype(int)
        ))
        lat_c = dict(zip(pd.to_numeric(cli_pos["ID_Cli"]).astype(int),
                         pd.to_numeric(cli_pos["Latitude_Cli"].str.replace(",", ".")).astype(float)))
        lon_c = dict(zip(pd.to_numeric(cli_pos["ID_Cli"]).astype(int),
                         pd.to_numeric(cli_pos["Longitude_Cli"].str.replace(",", ".")).astype(float)))
        lat_f = dict(zip(pd.to_numeric(fun_pos["ID_Func"]).astype(int),
                         pd.to_numeric(fun_pos["Latitude_Func"].str.replace(",", ".")).astype(float)))
        lon_f = dict(zip(pd.to_numeric(fun_pos["ID_Func"]).astype(int),
                         pd.to_numeric(fun_pos["Longitude_Func"].str.replace(",", ".")).astype(float)))

        for (i, j) in active_pairs:
            c = proj_cli.get(j)
            if c in lat_c and i in lat_f:
                R = 6371.0
                rlat1, rlon1 = math.radians(lat_f[i]), math.radians(lon_f[i])
                rlat2, rlon2 = math.radians(lat_c[c]), math.radians(lon_c[c])
                dlat = rlat2 - rlat1
                dlon = rlon2 - rlon1
                a = math.sin(dlat/2)**2 + math.cos(rlat1)*math.cos(rlat2)*math.sin(dlon/2)**2
                d = R * 2 * math.asin(math.sqrt(a))
                if d > KM_MAX:
                    viol_dist += 1
    except Exception as e:
        print(f"  Aviso: Erro ao calcular violações de distância: {e}")

    # Auto-exclusion violations
    viol_auto = 0
    if not df_auto.empty:
        try:
            for _, r in df_auto.iterrows():
                fi = int(float(r["ID_Func"]))
                pj = int(float(r["ID_Proj"]))
                if (fi, pj) in active_pairs:
                    viol_auto += 1
        except Exception as e:
            print(f"  Aviso: Erro ao calcular violações de autoexclusão: {e}")

    # Descompressão: not computed post-hoc (needs temporal analysis, set to 0)
    viol_desc = 0

    row = {
        "instance": inst_id,
        "scenario": "D_MILP_noBE",
        "model": "MILP",
        "ativar_bem_estar": False,
        "custo_total_folha": round(custo, 2),
        "funcionarios_alocados": func_alocados,
        "total_funcionarios": nf,
        "perc_funcionarios_alocados": round(perc_func, 2),
        "total_alocacoes": total_x,
        "projetos_ativos": total_y,
        "total_projetos": np_,
        "upgrades": upgrades,
        "viol_distancia": viol_dist,
        "viol_autoexclusao": viol_auto,
        "viol_descompressao": viol_desc,
        "tempo_execucao_s": round(elapsed, 2),
        "status_solver": status,
    }

    print(f"\n  Custo:      R$ {custo:,.2f}")
    print(f"  Func aloc:  {func_alocados}/{nf} ({perc_func:.1f}%)")
    print(f"  Proj ativos: {total_y}/{np_}")
    print(f"  Alocações:  {total_x}")
    print(f"  Upgrades:   {upgrades}")
    print(f"  Viol dist:  {viol_dist}")
    print(f"  Viol auto:  {viol_auto}")
    print(f"  Tempo:      {elapsed:.1f}s")

    return row


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Executa MILP sem BE")
    parser.add_argument("--instance", type=str, help="Uma instância específica")
    parser.add_argument("--force", action="store_true", help="Re-executar mesmo se já existir")
    args = parser.parse_args()

    instances = list(INSTANCES.keys())
    if args.instance:
        if args.instance not in INSTANCES:
            print(f"ERRO: Instância desconhecida: {args.instance}")
            sys.exit(1)
        instances = [args.instance]

    # Init CSV
    if not os.path.isfile(OUTPUT_CSV):
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADER).writeheader()

    total_t0 = time.time()
    for inst_id in instances:
        if not args.force and is_done(inst_id):
            print(f"\n  SKIP: {inst_id} (já existe em {OUTPUT_CSV})")
            continue

        row = run_milp_noBE(inst_id)
        if row:
            with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CSV_HEADER, extrasaction="ignore")
                w.writerow(row)
            print(f"  ✓ Salvo em {OUTPUT_CSV}")

    elapsed = time.time() - total_t0
    print(f"\n{'='*70}")
    print(f"  CONCLUÍDO — Tempo total: {elapsed:.1f}s")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

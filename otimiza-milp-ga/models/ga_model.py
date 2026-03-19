# ============================================================================
# GA MODEL - Converted from GA_GitH.ipynb for local execution
# Usage:
#   from models.ga_model import executar_ga_completo, PAR
#   PAR["ARQUIVO_ZIP"] = "data/instances/XSMALL_V01.zip"
#   resultado, case, metricas = executar_ga_completo("data/instances/XSMALL_V01.zip", True)
# ============================================================================
import os as _os
import builtins as _builtins
OUTPUT_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'data', 'results')
_os.makedirs(OUTPUT_DIR, exist_ok=True)

QUIET_MODE = True

def _status(msg: str) -> None:
    _builtins.print(msg, flush=True)

def print(*args, **kwargs):
    if not QUIET_MODE:
        return _builtins.print(*args, **kwargs)

# 1
# ============================================================================
# Instalação das bibliotecas
# ============================================================================
# (deps already installed locally)

# 2
# ============================================================================
# Importação das bibliotecas
# ============================================================================

import os, io, zipfile, random, math, time, multiprocessing as mp
from datetime import timedelta
import numpy as np, pandas as pd
from numba import njit
from deap import base, creator, tools
import matplotlib.pyplot as plt
import networkx as nx
from geopy.distance import geodesic





# 3
# =============================
# PARÂMETROS
# =============================

PAR = {
    "ARQUIVO_ZIP": os.path.join(OUTPUT_DIR, "LARGE_V31.zip"),

    "COL_TAM": "Tam_Proj",
    "DESC_DIAS": {"P": 1, "M": 2, "G": 3},
    "KM_MAX": 20,

    # Tolerâncias
    "TOL_COMPOSICAO": 0.01,
    "TOL_PESSOAS_ALOCADAS": 0.05,
    "TOL_TREINO": 0.02,
    "TOL_COBERTURA_PROJETOS": 0.0,
    "TOL_PAPEIS": 0.0,
    "TOL_LIM_FUNC_SOC_DIR_GS": 0.0,
    "TOL_LIM_FUNC_OUTROS": 0.0,
    "TOL_DIST": 0.0,
    "TOL_AUTO": 0.0,
    "TOL_DESC": 0.0,
    "TOL_SDEM_GLOBAL": 0.0,
    "TOL_SDEM_LOCAL": 0.0,

    # Pesos — Penalidades Hierárquicas Normalizadas pela Escala de Custo
    # Técnica: W_k = β_k · c̄, onde c̄ ≈ 200k (custo médio/alocação)
    # Garante W_BE / max(c_ij) ≥ 20 → nenhuma alocação compensa uma violação
    # Nível 0 (hard):  β=500  → 100M  | Indisponibilidade, liderança
    # Nível 1:         β=250  → 50M   | Composição
    # Nível 2:         β=50   → 10M   | Demanda, BE (dist, auto, desc)
    # Nível 3:         β=5    → 1M    | Falta papel, Treino
    # Nível 4:         β=0    → 0     | Upgrades
    "PESO_UPGRADE": 0.0,
    "PESO_DESVIO_COMP": 50_000_000.0,
    "PESO_FALTA_PAPEL": 1_000_000.0,
    "PESO_TREINO": 1_000_000.0,
    "PESO_DESC": 10_000_000.0,
    "PESO_DIST": 10_000_000.0,
    "PESO_AUTO": 10_000_000.0,
    "PESO_HARD": 100_000_000.0,
    "PESO_SDEM": 10_000_000.0,

    # Promoção funcional
    "MAX_UP_FRAC": 0.10,
    "PESO_UP_SOFT": 0.0,

    # GA - hiperparâmetros
    "GA_SEED": 42,
    "GA_GER": 400,
    "GA_CXPB": 0.80,
    "GA_MUTPB": 0.30,
    "GA_TOURN": 4,

    # Multi-island
    "ILHAS_NUM": 4,
    "ILHA_POP": 40,
    "ILHA_MIG_INTERVAL": 20,
    "ILHA_MIG_TAMANHO": 6,

    # Mutação
    "MUT_INDPB": 0.03,

    # Early stopping
    "EARLY_PATIENCE": 25,

    # Paralelização
    "CHUNKSIZE": 64,

    # Metas desligadas (testadas e não usadas)
    "ALVO_UNICOS_ABS": 0,
    "PESO_HARD_UNICOS_GAP": 0,
    "PESO_ESPALHAMENTO": 0,
}




# 4
# ============================================================================
# Esta seção concentra utilitários de entrada de dados:
# lê os CSVs dentro do .zip (bases SMALL/LARGE), remove prefixos dos nomes,
# e padroniza tipos (IDs, números com vírgula, datas) para gerar DataFrames prontos para o modelo.
# ============================================================================

def _basename_no_prefix(p):
    b = os.path.basename(p)
    if b.startswith("SMALL_"): b = b[len("SMALL_"):]
    if b.startswith("LARGE_"): b = b[len("LARGE_"):]
    return b

def _to_float(sr):
    return pd.to_numeric(sr.astype(str).str.replace(",", ".", regex=False), errors="coerce")

def _parse_date_series(sr):
    x = pd.to_datetime(sr, errors="coerce", format="%Y-%m-%d")
    mask = x.isna()
    if mask.any():
        x.loc[mask] = pd.to_datetime(sr[mask], dayfirst=True, errors="coerce")
    return x

def read_csv_from_zip(zf, endswith_name, sep=";"):
    names = [n for n in zf.namelist() if n.endswith(endswith_name)]
    if not names: return pd.DataFrame()
    with zf.open(names[0]) as f:
        df = pd.read_csv(f, sep=sep, dtype=str, keep_default_na=False)
    df.columns = [c.encode("utf-8").decode("utf-8-sig").strip() for c in df.columns]
    return df

def carregar_tabelas_zip(zip_path):
    req = {"TbFuncionarios","TbProjetos","TbCategorias","TbClientes",
           "TbProjetos_Alocacao","TbFuncionarios_Skill","TbComposicao",
           "TbFuncionarios_Indisponiveis","TbFuncionarios_Treinamentos_Obrigatorios",
           "TbTreinamentos_Obrigatorios","TbProjetos_Autoexclusao","TbProjetos_Descompressao",
           "TbProjetos_Independencia"}

    tabs = {k: pd.DataFrame() for k in req}
    with zipfile.ZipFile(zip_path, 'r') as z:
        for nm in z.namelist():
            if not nm.lower().endswith(".csv"): continue
            base = _basename_no_prefix(nm).replace(".csv","")
            if base in req:
                tabs[base] = read_csv_from_zip(z, nm.split("/")[-1])
    return tabs

def preparar_bases(tabs, col_tam="Tam_Proj"):
    df_func = tabs["TbFuncionarios"].copy()
    df_proj = tabs["TbProjetos"].copy()
    df_categ= tabs["TbCategorias"].copy()
    df_cli  = tabs["TbClientes"].copy()
    df_aloc = tabs["TbProjetos_Alocacao"].copy()
    df_sk   = tabs["TbFuncionarios_Skill"].copy()
    df_comp = tabs["TbComposicao"].copy()
    df_ind  = tabs["TbFuncionarios_Indisponiveis"].copy()
    df_tf   = tabs["TbFuncionarios_Treinamentos_Obrigatorios"].copy()
    df_tc   = tabs["TbTreinamentos_Obrigatorios"].copy()
    df_auto = tabs["TbProjetos_Autoexclusao"].copy()
    df_desc = tabs["TbProjetos_Descompressao"].copy()
    df_indep= tabs["TbProjetos_Independencia"].copy()

    df_func["ID_Func"]  = pd.to_numeric(df_func.get("ID_Func"), errors="coerce").astype("Int64")
    df_func["ID_Categ"] = pd.to_numeric(df_func.get("ID_Categ"), errors="coerce").astype("Int64")
    df_func["Salario_Hora"] = _to_float(df_func.get("Salario_Hora", pd.Series([0]*len(df_func))))
    for col in ["Latitude_Func","Longitude_Func"]:
        if col in df_func.columns: df_func[col] = _to_float(df_func[col])

    df_proj["ID_Proj"] = pd.to_numeric(df_proj.get("ID_Proj"), errors="coerce").astype("Int64")
    df_proj["ID_Cli"]  = pd.to_numeric(df_proj.get("ID_Cli"), errors="coerce").astype("Int64")
    df_proj[col_tam]   = df_proj[col_tam].astype(str)

    for c in ["Qt_horas_Previstas","Max_Pessoas"]:
        if c in df_proj.columns: df_proj[c] = _to_float(df_proj[c])

    for c in ["Data_Inicio_Proj","Data_Fim_Proj"]:
        if c in df_proj.columns: df_proj[c] = _parse_date_series(df_proj[c])

    df_categ["ID_Categ"]        = pd.to_numeric(df_categ.get("ID_Categ"), errors="coerce").astype("Int64")
    df_categ["Perc_Tempo_Proj"] = _to_float(df_categ.get("Perc_Tempo_Proj", pd.Series([100]*len(df_categ))))
    df_categ["Lim_Proj"]        = _to_float(df_categ.get("Lim_Proj", pd.Series([5]*len(df_categ))))

    for col in ["Latitude_Cli","Longitude_Cli"]:
        if col in df_cli.columns: df_cli[col] = _to_float(df_cli[col])

    if not df_aloc.empty:
        for c in ["ID_Func","ID_Proj"]:
            df_aloc[c] = pd.to_numeric(df_aloc[c], errors="coerce").astype("Int64")

    if not df_sk.empty:
        for c in ["ID_Func","ID_Skill"]:
            if c in df_sk.columns:
                df_sk[c] = pd.to_numeric(df_sk[c], errors="coerce").astype("Int64")

    if not df_comp.empty:
        df_comp["Categoria"] = pd.to_numeric(df_comp.get("Categoria"), errors="coerce").astype("Int64")
        df_comp[col_tam] = df_comp[col_tam].astype(str)
        df_comp["Qt_Ideal"] = pd.to_numeric(df_comp.get("Qt_Ideal"), errors="coerce").fillna(0).astype(int)

    if not df_ind.empty:
        df_ind["ID_Func"] = pd.to_numeric(df_ind.get("ID_Func"), errors="coerce").astype("Int64")
        for c in ["Data_Inicio_Indisp","Data_Fim_Indisp"]:
            if c in df_ind.columns: df_ind[c] = _parse_date_series(df_ind[c])

    if not df_tf.empty:
        for c in ["ID_Func","ID_Treino"]:
            if c in df_tf.columns:
                df_tf[c] = pd.to_numeric(df_tf[c], errors="coerce").astype("Int64")
        for c in ["Data_Conclusao","Valido_Ate"]:
            if c in df_tf.columns:
                df_tf[c] = _parse_date_series(df_tf[c])
    if not df_tc.empty and "ID_Treino" in df_tc.columns:
        df_tc["ID_Treino"] = pd.to_numeric(df_tc["ID_Treino"], errors="coerce").astype("Int64")

    for df in [df_auto, df_desc]:
        if not df.empty:
            for c in ["ID_Func","ID_Proj"]:
                if c in df: df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    if not df_indep.empty:
        for c in ["ID_Func","ID_Proj"]:
            if c in df_indep: df_indep[c] = pd.to_numeric(df_indep[c], errors="coerce").astype("Int64")

    return df_func, df_proj, df_categ, df_cli, df_aloc, df_sk, df_comp, df_ind, df_tf, df_tc, df_auto, df_desc, df_indep




# 5
# ============================================================================
# CASE BUILDER COM BOUNDS DE COMPOSIÇÃO
# Constrói o case, ou seja, a instância do problema em formato NumPy para execução rápida:
# lê e padroniza as tabelas do .zip, gera mapas/índices (funcionários, projetos, categorias),
# calcula custo por par (func,proj), cria máscaras de restrições (indisp/indep/dist/auto/treino),
# monta a composição ideal com limites (bounds) e prepara a estrutura seat-based para o GA.
# ============================================================================


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2.0)**2 + np.cos(np.radians(lat1))*np.cos(np.radians(lat2))*np.sin(dlon/2.0)**2
    return 2*R*np.arcsin(np.sqrt(a))

def build_case_np(zip_path, ativar_bem_estar=True):
    print(f"\nConstruindo case...")

    (df_func, df_proj, df_categ, df_cli, df_aloc, df_skills, df_comp,
     df_indisp, df_tfunc, df_tcat, df_auto, df_desc, df_indep) = preparar_bases(
         carregar_tabelas_zip(zip_path), PAR["COL_TAM"])

    # IDs
    func_ids = df_func["ID_Func"].dropna().astype(int).tolist()
    proj_ids = df_proj["ID_Proj"].dropna().astype(int).tolist()
    f2i = {fid:i for i,fid in enumerate(func_ids)}
    p2j = {pid:j for j,pid in enumerate(proj_ids)}
    Nf, Np = len(func_ids), len(proj_ids)

    print(f"Funcionários: {Nf:,}")
    print(f"Projetos: {Np:,}")

    # Categorias e upgrades
    cat_orig_series = df_func.set_index("ID_Func")["ID_Categ"].astype(int)
    base_cats = [1,2,3,4,5,6]
    cats_present = sorted(set(int(c) for c in cat_orig_series.dropna().unique().tolist()) | set(base_cats))
    cat2idx = {c:i for i,c in enumerate(cats_present)}
    C = len(cats_present)

    skills_count = df_skills.groupby("ID_Func")["ID_Skill"].nunique().to_dict() if not df_skills.empty else {}
    upgrade_cat = {}
    for fid in func_ids:
        c = int(cat_orig_series.loc[fid])
        upgrade_cat[fid] = c-1 if (c in [4,5,6] and skills_count.get(fid,0) >= 3) else c

    upcat_arr   = np.array([upgrade_cat[fid] for fid in func_ids], dtype=np.int16)
    orig_cat_arr= np.array([cat_orig_series.loc[fid] for fid in func_ids], dtype=np.int16)
    upcat_idx   = np.array([cat2idx.get(int(c),0) for c in upcat_arr], dtype=np.int16)

    # Parâmetros por categoria
    perc_tempo = df_categ.set_index("ID_Categ")["Perc_Tempo_Proj"].astype(float).to_dict()
    lim_proj   = df_categ.set_index("ID_Categ")["Lim_Proj"].astype(float).to_dict()
    lim_by_cat = np.array([lim_proj.get(c,5.0) for c in cats_present], dtype=np.float32)

    # Alocação atual
    cont_aloc_atual = df_aloc.groupby("ID_Func")["ID_Proj"].nunique().to_dict() if not df_aloc.empty else {}
    aloc_atual = np.array([float(cont_aloc_atual.get(fid,0.0)) for fid in func_ids], dtype=np.float32)

    # Projetos
    horas_proj = df_proj.set_index("ID_Proj")["Qt_horas_Previstas"].astype(float).to_dict()
    max_p      = df_proj.set_index("ID_Proj")["Max_Pessoas"].astype(float).to_dict()
    idcli_proj = df_proj.set_index("ID_Proj")["ID_Cli"].astype("Int64").fillna(0).astype(int).to_dict()
    tam_map    = df_proj.set_index("ID_Proj")[PAR["COL_TAM"]].astype(str).to_dict()
    tam2idx = {"P":0, "M":1, "G":2}
    tam_idx = np.array([tam2idx.get(tam_map[pid],0) for pid in proj_ids], dtype=np.int16)

    ideal_map = {}
    if not df_comp.empty:
        tmp = (df_comp.groupby([PAR["COL_TAM"],"Categoria"], as_index=False)["Qt_Ideal"].sum())
        for _,r in tmp.iterrows():
            t = tam2idx.get(str(r[PAR["COL_TAM"]]), 0)
            c = int(r["Categoria"])
            ideal_map[(t,c)] = int(r["Qt_Ideal"])

    ideal = np.zeros((3, C), dtype=np.int16)
    comp_low = np.zeros((3, C), dtype=np.int16)
    comp_high = np.zeros((3, C), dtype=np.int16)

    for (t,c),q in ideal_map.items():
        if c in cat2idx:
            idx = cat2idx[c]
            ideal[t, idx] = int(q)
            # Bounds com tolerância ±1%
            if q > 0:
                comp_low[t, idx] = int(math.floor((1 - PAR["TOL_COMPOSICAO"]) * q))
                comp_high[t, idx] = int(math.ceil((1 + PAR["TOL_COMPOSICAO"]) * q))

    print(f"Composição ideal + bounds (tol={PAR['TOL_COMPOSICAO']})")

    # Coordenadas
    cli_lat = df_cli.set_index("ID_Cli")["Latitude_Cli"].astype(float).to_dict() if "Latitude_Cli" in df_cli else {}
    cli_lon = df_cli.set_index("ID_Cli")["Longitude_Cli"].astype(float).to_dict() if "Longitude_Cli" in df_cli else {}
    f_lat = df_func.set_index("ID_Func")["Latitude_Func"].astype(float).to_dict() if "Latitude_Func" in df_func else {}
    f_lon = df_func.set_index("ID_Func")["Longitude_Func"].astype(float).to_dict() if "Longitude_Func" in df_func else {}

    # Matrizes base
    cost = np.zeros((Nf, Np), dtype=np.float32)
    indisp = np.zeros((Nf, Np), dtype=bool)
    dist_mask = np.zeros((Nf, Np), dtype=bool)
    auto_mask = np.zeros((Nf, Np), dtype=bool)
    indep_mask = np.zeros((Nf, Np), dtype=bool)
    treino_mask = np.zeros((Nf, Np), dtype=bool)

    # Custo com categoria efetiva
    for i,fid in enumerate(func_ids):
        sal = float(df_func.loc[df_func["ID_Func"]==fid, "Salario_Hora"].values[0])
        c_eff = int(upcat_arr[i])
        perc  = float(perc_tempo.get(c_eff, 100.0))/100.0
        for j,pid in enumerate(proj_ids):
            h = float(horas_proj.get(pid, 0.0))
            cost[i,j] = sal*h*perc

    # Indisponibilidade
    if not df_indisp.empty:
        for _,r in df_indisp.iterrows():
            fid = int(r["ID_Func"])
            if pd.isna(r.get("Data_Inicio_Indisp")) or pd.isna(r.get("Data_Fim_Indisp")):
                continue
            ini = r["Data_Inicio_Indisp"]; fim = r["Data_Fim_Indisp"]
            if fid in f2i:
                i = f2i[fid]
                for pid in proj_ids:
                    j = p2j[pid]
                    ini_j = df_proj.loc[df_proj["ID_Proj"]==pid, "Data_Inicio_Proj"].values[0]
                    fim_j = df_proj.loc[df_proj["ID_Proj"]==pid, "Data_Fim_Proj"].values[0]
                    if not ((ini_j > fim) or (fim_j < ini)):
                        indisp[i,j] = True

    # Independência
    if not df_indep.empty:
        for _,r in df_indep.iterrows():
            fid = int(r["ID_Func"]); pid = int(r["ID_Proj"])
            if fid in f2i and pid in p2j:
                indep_mask[f2i[fid], p2j[pid]] = True
    indisp = indisp | indep_mask

    # Distância
    if ativar_bem_estar:
        latf_arr = np.array([f_lat.get(fid, np.nan) for fid in func_ids])
        lonf_arr = np.array([f_lon.get(fid, np.nan) for fid in func_ids])
        mask_f = np.isfinite(latf_arr) & np.isfinite(lonf_arr)
        for j,pid in enumerate(proj_ids):
            cli = int(idcli_proj.get(pid, -1))
            if cli in cli_lat and cli in cli_lon:
                latc, lonc = cli_lat[cli], cli_lon[cli]
                if np.isfinite(latc) and np.isfinite(lonc) and mask_f.any():
                    d = _haversine_km(latf_arr[mask_f], lonf_arr[mask_f], latc, lonc)
                    dist_mask[mask_f, j] = d > PAR["KM_MAX"]

    # Autoexclusão
    if ativar_bem_estar and not df_auto.empty:
        for _,r in df_auto.iterrows():
            fid = int(r["ID_Func"]); pid = int(r["ID_Proj"])
            if fid in f2i and pid in p2j:
                auto_mask[f2i[fid], p2j[pid]] = True

    # Descompressão
    conflitos = []
    if ativar_bem_estar:
        proj_info = {int(r.ID_Proj): {"ini": pd.to_datetime(r.Data_Inicio_Proj),
                                      "fim": pd.to_datetime(r.Data_Fim_Proj),
                                      "tam": str(r[PAR["COL_TAM"]])}
                     for _,r in df_proj.iterrows()}
        for pid_j in proj_ids:
            fim_j = proj_info[pid_j]["fim"]; tam_j = proj_info[pid_j]["tam"]
            janela = fim_j + timedelta(days=int(PAR["DESC_DIAS"].get(tam_j,0)))
            for pid_k in proj_ids:
                if pid_j==pid_k: continue
                ini_k = proj_info[pid_k]["ini"]
                if (ini_k > fim_j) and (ini_k < janela):
                    conflitos.append((p2j[pid_j], p2j[pid_k]))
    desc_pairs = np.unique(np.array(conflitos, dtype=np.int32), axis=0) if conflitos else np.zeros((0,2), dtype=np.int32)

    # Treinamentos obrigatórios
    treinos_obrig = set(df_tcat["ID_Treino"].dropna().astype(int).unique().tolist()) if not df_tcat.empty else set()
    if len(treinos_obrig) > 0:
        fim_by_j = df_proj.set_index("ID_Proj")["Data_Fim_Proj"].to_dict()
        if not df_tfunc.empty:
            tfunc_grp = df_tfunc.groupby("ID_Func")
        else:
            tfunc_grp = {}
        for i,fid in enumerate(func_ids):
            concl_ids = []
            if not isinstance(tfunc_grp, dict) and fid in tfunc_grp.groups:
                concl_ids = tfunc_grp.get_group(fid)[["ID_Treino","Valido_Ate"]].copy()
            for j,pid in enumerate(proj_ids):
                if len(concl_ids)==0:
                    treino_mask[i,j] = True
                else:
                    fim_j = fim_by_j.get(pid, pd.NaT)
                    if pd.isna(fim_j):
                        treino_mask[i,j] = True
                    else:
                        validos = concl_ids[concl_ids["Valido_Ate"] >= fim_j]["ID_Treino"].dropna().astype(int).unique().tolist()
                        if not (set(validos) >= treinos_obrig):
                            treino_mask[i,j] = True

    # Necessidades de papéis
    need_soc  = np.zeros(Np, dtype=np.uint8)
    need_dir  = np.zeros(Np, dtype=np.uint8)
    need_comp = np.zeros(Np, dtype=np.uint8)
    idx_soc = cat2idx.get(1, None)
    idx_dir2 = cat2idx.get(2, None)
    idx_dir3 = cat2idx.get(3, None)
    idx_comp4 = cat2idx.get(4, None)
    idx_comp5 = cat2idx.get(5, None)
    idx_comp6 = cat2idx.get(6, None)

    for j,pid in enumerate(proj_ids):
        t = tam_idx[j]
        need_soc[j]  = 1 if (idx_soc is not None and ideal[t, idx_soc] > 0) else 0
        sum_dir = (ideal[t, idx_dir2] if idx_dir2 is not None else 0) + (ideal[t, idx_dir3] if idx_dir3 is not None else 0)
        need_dir[j]  = 1 if sum_dir > 0 else 0
        sum_comp = 0
        for idxc in [idx_comp4, idx_comp5, idx_comp6]:
            if idxc is not None: sum_comp += ideal[t, idxc]
        need_comp[j] = 1 if sum_comp > 0 else 0

    # Assentos
    seats_len = np.array([max(1, int(round(max_p.get(pid,1)))) for pid in proj_ids], dtype=np.int32)
    seats_start = np.zeros(Np, dtype=np.int32)
    for j in range(1, Np):
        seats_start[j] = seats_start[j-1] + seats_len[j-1]
    TOT_SEATS = int(seats_start[-1] + seats_len[-1]) if Np>0 else 0
    proj_of_seat = np.zeros(TOT_SEATS, dtype=np.int32)
    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        proj_of_seat[s0:s0+sl] = j

    print(f"Assentos: {TOT_SEATS:,} (seat-based)")
    print(f"Bem-estar: {'ATIVADO' if ativar_bem_estar else 'DESATIVADO'}")
    print(f"Case construído!")

    case_np = {
        "func_ids": np.array(func_ids, dtype=np.int32),
        "proj_ids": np.array(proj_ids, dtype=np.int32),
        "Nf": Nf, "Np": Np, "C": C,
        "cat2idx": cat2idx,
        "orig_cat": orig_cat_arr.astype(np.int16),
        "upcat": upcat_arr.astype(np.int16),
        "upcat_idx": upcat_idx.astype(np.int16),
        "perc_tempo": perc_tempo,
        "lim_by_cat": lim_by_cat,
        "aloc_atual": aloc_atual,
        "horas_proj": horas_proj,
        "tam_idx": tam_idx,
        "ideal": ideal,
        "comp_low": comp_low,
        "comp_high": comp_high,
        "cost": cost,
        "indisp": indisp,
        "indep": indep_mask,
        "dist": dist_mask,
        "auto": auto_mask,
        "treino": treino_mask,
        "desc_pairs": desc_pairs,
        "seats_start": seats_start,
        "seats_len": seats_len,
        "proj_of_seat": proj_of_seat,
        "assentos_totais": float(seats_len.sum()),
        "ativar_bem_estar": bool(ativar_bem_estar),
        "idx_soc": idx_soc, "idx_dir2": idx_dir2, "idx_dir3": idx_dir3,
        "idx_comp4": idx_comp4, "idx_comp5": idx_comp5, "idx_comp6": idx_comp6,
        "need_soc": need_soc,
        "need_dir": need_dir,
        "need_comp": need_comp,
    }
    return case_np



# 6
# ============================================================================
# FITNESS NUMBA JIT
# Esta seção implementa a função de fitness (aptidão) do GA com Numba (JIT) para ficar rápida.
# Ela calcula o custo total da alocação e soma penalidades por violações:
# upgrades, falta de pessoas (slack), composição fora dos limites, regras de liderança (hard),
# bem-estar (distância/autoexclusão/descompressão) e treinamentos obrigatórios.
# Ao final, há um wrapper para o DEAP chamar a função Numba e um helper simples de diagnóstico.
# ============================================================================

@njit(cache=False, fastmath=True)
def fitness_milp_numba(
    genes,
    proj_of_seat,
    seats_start,
    seats_len,
    cost,
    indisp,
    dist,
    auto,
    treino,
    desc_pairs,
    upcat,
    upcat_idx,
    orig_cat,
    tam_idx,
    ideal,
    comp_low,
    comp_high,
    need_soc,
    need_dir,
    need_comp,
    idx_soc,
    idx_dir2,
    idx_dir3,
    peso_upgrade,
    peso_desvio_comp,
    peso_falta_papel,
    peso_treino,
    peso_desc,
    peso_dist,
    peso_auto,
    peso_hard,
    peso_sdem,
):

    Nf, Np = cost.shape
    C = ideal.shape[1]
    fitness = 0.0

    # 1. CUSTO DE FOLHA REAL (categoria efetiva)
    custo_folha = 0.0
    valid = genes > 0
    i_arr = genes[valid] - 1
    j_arr = proj_of_seat[valid]

    for k in range(len(i_arr)):
        i = i_arr[k]
        j = j_arr[k]
        custo_folha += cost[i, j]

    fitness += custo_folha

    # 2. UPGRADES FUNCIONAIS
    func_usados = np.zeros(Nf, dtype=np.int32)
    for i in i_arr:
        func_usados[i] = 1

    n_upgrades = 0
    for i in range(Nf):
        if func_usados[i] > 0 and upcat[i] < orig_cat[i]:
            n_upgrades += 1

    fitness += peso_upgrade * n_upgrades

    # 3. SLACKS DE DEMANDA
    s_dem_total = 0.0
    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]
        ocupados = (seg > 0).sum()
        s_dem = float(sl - ocupados)
        s_dem_total += s_dem

    fitness += peso_sdem * s_dem_total

    # 4. VIOLAÇÕES HARD
    hard_viol = 0.0

    # 4.1 Indisponibilidade
    for k in range(len(i_arr)):
        if indisp[i_arr[k], j_arr[k]]:
            hard_viol += 1.0

    # 4.2 Capacidade de projetos
    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]
        ocupados = (seg > 0).sum()
        if ocupados > sl:
            hard_viol += float(ocupados - sl)

    # 5. DESVIOS DE COMPOSIÇÃO COM BOUNDS
    viol_comp = 0.0

    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]

        if (seg > 0).sum() == 0:
            continue

        t = tam_idx[j]

        for c_idx in range(C):

            count = 0
            for s in range(sl):
                if seg[s] > 0:
                    if upcat_idx[seg[s] - 1] == c_idx:
                        count += 1

            ideal_q = ideal[t, c_idx]

            if ideal_q == 0:
                if count > 0:
                    viol_comp += float(count)
            else:
                low = comp_low[t, c_idx]
                high = comp_high[t, c_idx]

                if count < low:
                    viol_comp += float(low - count)
                elif count > high:
                    viol_comp += float(count - high)

    fitness += peso_desvio_comp * viol_comp


    # 6. SLACKS DE PAPÉIS
    falta_papel = 0.0

    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]

        if (seg > 0).sum() == 0:
            continue

        has_soc = 0
        has_dirger = 0
        has_compl = 0

        for s in range(sl):
            if seg[s] > 0:
                cat = upcat[seg[s] - 1]
                if cat == 1:
                    has_soc = 1
                elif cat in (2, 3):
                    has_dirger = 1
                elif cat in (4, 5, 6):
                    has_compl = 1

        if need_soc[j] > 0 and has_soc == 0:
            falta_papel += 1.0
        if need_dir[j] > 0 and has_dirger == 0:
            falta_papel += 1.0
        if need_comp[j] > 0 and has_compl == 0:
            falta_papel += 1.0

    fitness += peso_falta_papel * falta_papel

    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]

        if (seg > 0).sum() == 0:
            continue

        n_soc = 0
        n_dir = 0
        n_sm = 0

        for s in range(sl):
            if seg[s] > 0:
                cat = upcat[seg[s] - 1]
                if cat == 1:
                    n_soc += 1
                elif cat == 2:
                    n_dir += 1
                elif cat == 3:
                    n_sm += 1

        # Regra 1: Max 1 sócio
        if n_soc > 1:
            hard_viol += float(n_soc - 1)

        # Regra 2: Max 1 diretor
        if n_dir > 1:
            hard_viol += float(n_dir - 1)

        if n_soc > 0 and n_dir > 0:
            hard_viol += 1.0

        total_lid = n_soc + n_dir + n_sm
        if total_lid > 2:
            hard_viol += float(total_lid - 2)

        t = tam_idx[j]
        need_lider = 0
        if ideal[t, 0] > 0:
            need_lider = 1
        if ideal[t, 1] > 0 or ideal[t, 2] > 0:
            need_lider = 1

        if need_lider > 0 and total_lid == 0:
            hard_viol += 1.0

    fitness += peso_hard * hard_viol

    # 7. BEM-ESTAR
    # 7.1 Distância > KM_MAX
    viol_dist = 0.0
    for k in range(len(i_arr)):
        if dist[i_arr[k], j_arr[k]]:
            viol_dist += 1.0
    fitness += peso_dist * viol_dist

    # 7.2 Autoexclusão
    viol_auto = 0.0
    for k in range(len(i_arr)):
        if auto[i_arr[k], j_arr[k]]:
            viol_auto += 1.0
    fitness += peso_auto * viol_auto

    # 7.3 Descompressão
    viol_desc = 0.0
    for pair_idx in range(desc_pairs.shape[0]):
        j1 = desc_pairs[pair_idx, 0]
        j2 = desc_pairs[pair_idx, 1]

        s01, sl1 = seats_start[j1], seats_len[j1]
        s02, sl2 = seats_start[j2], seats_len[j2]

        funcs_j1 = set()
        funcs_j2 = set()

        for s in range(sl1):
            if genes[s01 + s] > 0:
                funcs_j1.add(genes[s01 + s])

        for s in range(sl2):
            if genes[s02 + s] > 0:
                funcs_j2.add(genes[s02 + s])

        # Interseção
        for f in funcs_j1:
            if f in funcs_j2:
                viol_desc += 1.0

    fitness += peso_desc * viol_desc

    # 8. Treinamento Obrigatorio
    viol_treino = 0.0
    for k in range(len(i_arr)):
        if treino[i_arr[k], j_arr[k]]:
            viol_treino += 1.0
    fitness += peso_treino * viol_treino

    return fitness

# Diagnóstico: verificar se penalização de composição está ativa
def diagnosticar_composicao(genes, case):
    Np = int(case["Np"])
    C = case["ideal"].shape[1]
    seats_start = case["seats_start"]
    seats_len = case["seats_len"]
    tam_idx = case["tam_idx"]
    ideal = case["ideal"]
    comp_low = case["comp_low"]
    comp_high = case["comp_high"]
    upcat_idx = case["upcat_idx"]

    viol_total = 0
    projetos_com_viol = 0

    for j in range(min(5, Np)):  # Verificar primeiros 5 projetos
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]

        if (seg > 0).sum() == 0:
            continue

        t = tam_idx[j]
        print(f"\nProjeto {j}: Tamanho={['P','M','G'][t]}")

        for c_idx in range(C):
            low = comp_low[t, c_idx]
            high = comp_high[t, c_idx]

            if low == 0 and high == 0:
                continue

            count = sum(1 for s in range(sl) if seg[s] > 0 and upcat_idx[seg[s]-1] == c_idx)
            ideal_val = ideal[t, c_idx]


# Wrapper Python para DEAP (sem numba)
def fitness_wrapper(genes, case):
    return (fitness_milp_numba(
        genes=genes,
        proj_of_seat=case["proj_of_seat"],
        seats_start=case["seats_start"],
        seats_len=case["seats_len"],
        cost=case["cost"],
        indisp=case["indisp"],
        dist=case["dist"],
        auto=case["auto"],
        treino=case["treino"],
        desc_pairs=case["desc_pairs"],
        upcat=case["upcat"],
        upcat_idx=case["upcat_idx"],
        orig_cat=case["orig_cat"],
        tam_idx=case["tam_idx"],
        ideal=case["ideal"],
        comp_low=case["comp_low"],
        comp_high=case["comp_high"],
        need_soc=case["need_soc"],
        need_dir=case["need_dir"],
        need_comp=case["need_comp"],
        idx_soc=case["idx_soc"] if case["idx_soc"] is not None else -1,
        idx_dir2=case["idx_dir2"] if case["idx_dir2"] is not None else -1,
        idx_dir3=case["idx_dir3"] if case["idx_dir3"] is not None else -1,
        peso_upgrade=PAR["PESO_UPGRADE"],
        peso_desvio_comp=PAR["PESO_DESVIO_COMP"],
        peso_falta_papel=PAR["PESO_FALTA_PAPEL"],
        peso_treino=PAR["PESO_TREINO"],
        peso_desc=PAR["PESO_DESC"],
        peso_dist=PAR["PESO_DIST"],
        peso_auto=PAR["PESO_AUTO"],
        peso_hard=PAR["PESO_HARD"],
        peso_sdem=PAR["PESO_SDEM"],
    ),)



# 7
# ============================================================================
# OPERADORES GENÉTICOS
# Esta seção define os operadores genéticos do GA:
# cria um indivíduo inicial viável preenchendo assentos (genes) com baixo custo;
# aplica reparos para atingir metas (ex.: 95% de funcionários alocados, limite de upgrades e categorias críticas);
# define mutação (troca/remove/realoca genes) respeitando restrições hard;
# e crossover por projeto (troca blocos de assentos entre dois indivíduos).
# ============================================================================


def init_individual(case):
    Nf, Np = int(case["Nf"]), int(case["Np"])
    proj_of_seat = case["proj_of_seat"]
    seats_start = case["seats_start"]
    seats_len = case["seats_len"]
    indisp = case["indisp"]
    cost = case["cost"]

    genes = np.zeros(proj_of_seat.size, dtype=np.int32)
    filled = np.zeros(Np, dtype=np.int32)

    # Fase 1: Um assento por pessoa (projeto mais barato viável)
    funcs_order = np.arange(Nf)
    np.random.shuffle(funcs_order)
    for i in funcs_order:
        viable = [j for j in range(Np) if (not indisp[i, j]) and (filled[j] < seats_len[j])]
        if not viable:
            continue
        costs = [cost[i, j] for j in viable]
        j_best = viable[int(np.argmin(costs))]
        s0, sl = seats_start[j_best], seats_len[j_best]
        seg = genes[s0:s0+sl]
        empties = np.where(seg == 0)[0]
        if empties.size > 0:
            pos = empties[0]
            seg[pos] = i + 1
            genes[s0:s0+sl] = seg
            filled[j_best] += 1

    # Fase 2: Completar todos os assentos
    used = np.zeros(Nf, dtype=np.uint8)
    used[genes[genes>0]-1] = 1
    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]
        empties = np.where(seg == 0)[0]
        if empties.size == 0:
            continue
        vi = np.where(~indisp[:, j])[0]
        if vi.size == 0:
            continue
        vi_new = vi[used[vi] == 0]
        vi_old = vi[used[vi] == 1]
        def fill_from(pool_idx):
            if pool_idx.size == 0: return 0
            k = min(empties.size, pool_idx.size)
            take = pool_idx[np.argpartition(cost[pool_idx, j], k-1)[:k]]
            seg[empties[:k]] = (take + 1)
            used[take] = 1
            return k
        k_new = fill_from(vi_new)
        if k_new < empties.size:
            fill_from(vi_old)
        genes[s0:s0+sl] = seg

    return genes

    # FASE 3: Forçar pelo menos 1 de cada categoria crítica
    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]

        if (seg > 0).sum() == 0:
            continue

        t = tam_idx[j]

        # Garantir pelo menos 1 sócio se ideal > 0
        if ideal[t, cat2idx.get(1, -1)] > 0:
            has_socio = any(upcat[seg[s]-1] == 1 for s in range(sl) if seg[s] > 0)
            if not has_socio:
                # Buscar sócio disponível
                candidatos = [i for i in range(Nf) if upcat[i] == 1 and not indisp[i, j]]
                if candidatos and (seg == 0).any():
                    pos = np.where(seg == 0)[0][0]
                    seg[pos] = candidatos[0] + 1
                    genes[s0:s0+sl] = seg

# REPAIR 1 Limites de Alocação e Upgrade
def repair_solution_95(genes, case, min_frac_func=0.95, max_upgrade_pct=0.10):
    Nf, Np = int(case["Nf"]), int(case["Np"])
    seats_start = case["seats_start"]
    seats_len = case["seats_len"]
    indisp = case["indisp"]
    cost = case["cost"]
    upcat = case["upcat"]
    orig_cat = case["orig_cat"]
    proj_of_seat = case["proj_of_seat"]

    genes = genes.copy()

    # 95% alocação
    usados = np.zeros(Nf, dtype=np.uint8)
    usados[genes[genes > 0] - 1] = 1
    total_usados = usados.sum()

    meta_func = int(min_frac_func * Nf)

    if total_usados < meta_func:
        faltando = meta_func - total_usados
        candidatos = np.where(usados == 0)[0]  # funcionários ainda não alocados
        np.random.shuffle(candidatos)

        for i in candidatos:
            # Encontrar projetos viáveis
            viaveis = []
            for j in range(Np):
                if indisp[i, j]:
                    continue
                s0, sl = seats_start[j], seats_len[j]
                seg = genes[s0:s0+sl]
                if (seg == 0).any():
                    viaveis.append((j, cost[i, j]))

            if not viaveis:
                continue

            # Escolhe projeto de menor custo
            viaveis.sort(key=lambda x: x[1])
            j_escolhido = viaveis[0][0]
            s0, sl = seats_start[j_escolhido], seats_len[j_escolhido]
            empties = np.where(genes[s0:s0+sl] == 0)[0]
            if empties.size > 0:
                genes[s0 + empties[0]] = i + 1
                usados[i] = 1
                total_usados += 1
                if total_usados >= meta_func:
                    break

    # Upgrades máximo 10%
    total_alocacoes = (genes > 0).sum()

    upgrades_atuais = []
    for seat_idx in range(genes.size):
        if genes[seat_idx] > 0:
            i = genes[seat_idx] - 1
            if upcat[i] < orig_cat[i]:
                upgrades_atuais.append((seat_idx, i, cost[i, proj_of_seat[seat_idx]]))

    limite_upgrades = int(max_upgrade_pct * total_alocacoes)

    if len(upgrades_atuais) > limite_upgrades:
        upgrades_atuais.sort(key=lambda x: x[2], reverse=True)
        remover = len(upgrades_atuais) - limite_upgrades

        for idx in range(remover):
            seat_idx, i_old, _ = upgrades_atuais[idx]
            j = proj_of_seat[seat_idx]
            genes[seat_idx] = 0  # remove upgrade

            # Tenta substituir por alguém sem upgrade
            candidatos_sem_up = []
            for i in range(Nf):
                if not indisp[i, j] and upcat[i] == orig_cat[i]:
                    candidatos_sem_up.append((i, cost[i, j]))

            if candidatos_sem_up:
                candidatos_sem_up.sort(key=lambda x: x[1])
                i_new = candidatos_sem_up[0][0]
                genes[seat_idx] = i_new + 1

    return genes

# REPAIR 2 - Composição
def repair_composition_critical(genes, case):
    Nf, Np = int(case["Nf"]), int(case["Np"])
    seats_start = case["seats_start"]
    seats_len = case["seats_len"]
    tam_idx = case["tam_idx"]
    ideal = case["ideal"]
    cat2idx = case["cat2idx"]
    upcat = case["upcat"]
    indisp = case["indisp"]
    cost = case["cost"]

    genes = genes.copy()

    for j in range(Np):
        s0, sl = seats_start[j], seats_len[j]
        seg = genes[s0:s0+sl]

        if (seg > 0).sum() == 0:
            continue

        t = tam_idx[j]

        # Categorias críticas: 1 (Sócio), 2 (Diretor), 3 (SM)
        for cat_num in [1, 2, 3]:
            if cat_num not in cat2idx:
                continue

            idx_cat = cat2idx[cat_num]
            qtd_ideal = ideal[t, idx_cat]

            # Se ideal > 0, deve ter pelo menos 1
            if qtd_ideal > 0:
                count = 0
                for s in range(sl):
                    if seg[s] > 0 and upcat[seg[s]-1] == cat_num:
                        count += 1

                # Se não tem nenhum, forçar alocação
                if count == 0:
                    candidatos = []
                    for i in range(Nf):
                        if upcat[i] == cat_num and not indisp[i, j]:
                            candidatos.append((i, cost[i, j]))

                    if candidatos:
                        # Ordenar por custo e pegar o mais barato
                        candidatos.sort(key=lambda x: x[1])
                        i_novo = candidatos[0][0]

                        # Substituir primeira pessoa ou adicionar em vazio
                        empties = np.where(seg == 0)[0]
                        if empties.size > 0:
                            seg[empties[0]] = i_novo + 1
                        else:
                            # Se não tem vazio, substituir categoria 6 (consultor)
                            for s in range(sl):
                                if seg[s] > 0 and upcat[seg[s]-1] == 6:
                                    seg[s] = i_novo + 1
                                    break

                        genes[s0:s0+sl] = seg

    return genes

# MUTACAO
def mutate_individual(genes, case, indpb=0.03):
    proj_of_seat = case["proj_of_seat"]
    indisp = case["indisp"]
    Nf = int(case["Nf"])
    cost = case["cost"]
    used = np.zeros(Nf, dtype=np.uint8)
    used[genes[genes>0]-1] = 1

    for g in range(genes.size):
        if np.random.random() < indpb:
            j = proj_of_seat[g]
            r = np.random.random()
            if r < 0.33:
                genes[g] = 0
            else:
                vi = np.where(~indisp[:, j])[0]
                if vi.size > 0:
                    vi_new = vi[used[vi] == 0]
                    pool = vi_new if vi_new.size > 0 else vi
                    if pool.size > 0:
                        costs_pool = cost[pool, j]
                        i_new = pool[int(np.argmin(costs_pool))]
                        genes[g] = i_new + 1
                        used[i_new] = 1
    return (genes,)

# CROSSOVER
def crossover_uniform_seat(genes1, genes2, case, indpb=0.5):
    Np = int(case["Np"])
    seats_start = case["seats_start"]
    seats_len = case["seats_len"]
    child1 = genes1.copy()
    child2 = genes2.copy()
    for j in range(Np):
        if np.random.random() < indpb:
            s0, sl = seats_start[j], seats_len[j]
            child1[s0:s0+sl], child2[s0:s0+sl] = genes2[s0:s0+sl].copy(), genes1[s0:s0+sl].copy()
    return child1, child2




# 8
# ============================================================================
# SETUP DEAP + GA ENGINE MULTI-ISLAND
# Esta seção configura o DEAP e executa o GA no modo “multi-island”.
# setup_deap(): registra como criar indivíduos, avaliar fitness, cruzar, mutar e selecionar.
# run_genetic_algorithm(): roda várias populações (ilhas) em paralelo, com:
# -repair inicial (95% cobertura + limite de upgrades),
# -evolução por gerações (seleção → crossover → mutação → repair periódico),
# -migração entre ilhas para diversificar a busca,
# -early stopping quando não há melhora.
# No final, retorna o melhor indivíduo e converte a solução para o formato x[(func,proj)]=1.
# ============================================================================

def setup_deap(case):
    if hasattr(creator, "FitnessMin"):
        del creator.FitnessMin
    if hasattr(creator, "Individual"):
        del creator.Individual

    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", np.ndarray, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()
    toolbox.register("individual", lambda: creator.Individual(init_individual(case)))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", fitness_wrapper, case=case)
    toolbox.register("mate", crossover_uniform_seat, case=case, indpb=0.5)
    toolbox.register("mutate", mutate_individual, case=case, indpb=PAR["MUT_INDPB"])
    toolbox.register("select", tools.selTournament, tournsize=PAR["GA_TOURN"])

    return toolbox

def run_genetic_algorithm(case, toolbox):
    print(f"\nIniciando GA Multi-Island ")
    print(f"Ilhas: {PAR['ILHAS_NUM']}")
    print(f"População/ilha: {PAR['ILHA_POP']}")
    print(f"Gerações: {PAR['GA_GER']}")
    print(f"Early stopping: {PAR['EARLY_PATIENCE']} gerações")
    print(f"Pesos: peso_hard={PAR['PESO_HARD']:,.0f}, peso_sdem={PAR['PESO_SDEM']:,.0f}")

    random.seed(PAR["GA_SEED"])
    np.random.seed(PAR["GA_SEED"])

    # Inicializar ilhas
    islands = [toolbox.population(n=PAR["ILHA_POP"]) for _ in range(PAR["ILHAS_NUM"])]

    # REPAIR INICIAL (95% + 10% upgrades)
    print("\nAplicando repair inicial (95% cobertura + 10% max upgrades)...")
    for island in islands:
        for idx, ind in enumerate(island):
            ind_repaired = repair_solution_95(ind, case, min_frac_func=0.95, max_upgrade_pct=0.10)
            island[idx] = creator.Individual(ind_repaired)
            del island[idx].fitness.values

    # Avaliar população inicial
    for island in islands:
        fitnesses = list(map(toolbox.evaluate, island))
        for ind, fit in zip(island, fitnesses):
            ind.fitness.values = fit

    # Definir stats APÓS avaliar população
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("min", np.min)
    stats.register("avg", np.mean)
    stats.register("std", np.std)

    # Tracking
    best_ever = None
    best_fitness = float('inf')
    no_improve = 0
    history_min = []
    history_avg = []

    inicio = time.time()

    # Loop de gerações
    for gen in range(PAR["GA_GER"]):
        # Evoluir cada ilha
        for island in islands:
            offspring = toolbox.select(island, len(island))
            offspring = [toolbox.clone(ind) for ind in offspring]

            # Crossover
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < PAR["GA_CXPB"]:
                    child1_new, child2_new = toolbox.mate(child1, child2)
                    child1[:] = child1_new
                    child2[:] = child2_new
                    del child1.fitness.values
                    del child2.fitness.values

            # Mutação
            for mutant in offspring:
                if random.random() < PAR["GA_MUTPB"]:
                    mutant_new, = toolbox.mutate(mutant)
                    mutant[:] = mutant_new
                    del mutant.fitness.values

            if (gen + 1) % 3 == 0:
                for idx, ind in enumerate(offspring):
                    ind_repaired = repair_solution_95(ind, case, min_frac_func=0.95, max_upgrade_pct=0.10)
                    ind[:] = ind_repaired
                    del ind.fitness.values

            # Avaliar inválidos
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = list(map(toolbox.evaluate, invalid_ind))
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            island[:] = offspring

        # Migração entre ilhas
        if (gen + 1) % PAR["ILHA_MIG_INTERVAL"] == 0 and PAR["ILHAS_NUM"] > 1:
            for i in range(PAR["ILHAS_NUM"]):
                emigrants = tools.selBest(islands[i], PAR["ILHA_MIG_TAMANHO"])
                next_island = (i + 1) % PAR["ILHAS_NUM"]
                islands[next_island].sort(key=lambda x: x.fitness.values[0], reverse=True)
                for k, emigrant in enumerate(emigrants):
                    islands[next_island][k] = toolbox.clone(emigrant)

        # Estatísticas
        all_inds = [ind for island in islands for ind in island]
        record = stats.compile(all_inds)
        history_min.append(record["min"])
        history_avg.append(record["avg"])

        best_gen = tools.selBest(all_inds, 1)[0]
        if best_gen.fitness.values[0] < best_fitness:
            best_fitness = best_gen.fitness.values[0]
            best_ever = toolbox.clone(best_gen)
            no_improve = 0
        else:
            no_improve += 1

        # Log
        if (gen + 1) % 20 == 0 or gen == 0:
            elapsed = time.time() - inicio
            print(f"Gen {gen+1:3d} | Min: {record['min']:,.0f} | Avg: {record['avg']:,.0f} | Tempo: {elapsed:.1f}s | Sem melhora: {no_improve}")

        # Early stopping
        if no_improve >= PAR["EARLY_PATIENCE"]:
            print(f"\n  Early stopping: {no_improve} gerações sem melhora")
            break

    tempo_total = time.time() - inicio

    print(f"\n GA concluído!")
    print(f"Tempo total: {tempo_total:.1f}s")
    print(f"Melhor fitness: {best_fitness:,.0f}")
    print(f"Gerações executadas: {gen+1}")

    # Converter genes para dicionário x[i,j]=1
    x_dict = {}
    valid = (best_ever > 0)
    i_arr = best_ever[valid] - 1
    j_arr = case["proj_of_seat"][valid]

    for k in range(len(i_arr)):
        i = int(i_arr[k])
        j = int(j_arr[k])
        fid = int(case["func_ids"][i])
        pid = int(case["proj_ids"][j])
        x_dict[(fid, pid)] = 1.0

    # Funcionários promovidos
    promovidos = []
    funcionarios_usados = set(i_arr)
    for i in funcionarios_usados:
        if case["upcat"][i] < case["orig_cat"][i]:
            promovidos.append(int(case["func_ids"][i]))

    resultado = {
        "x": x_dict,
        "genes": best_ever,
        "fitness": (best_fitness,),
        "funcionarios_promovidos": promovidos,
        "upgrade_cat": {int(case["func_ids"][i]): int(case["upcat"][i]) for i in range(case["Nf"])},
        "history_min": history_min,
        "history_avg": history_avg,
        "tempo_execucao": tempo_total,
        "geracoes": gen + 1,
    }

    return resultado

# 9
# ============================================================================
# RELATORIOS E GRAFOS
# Esta seção gera os artefatos de saída do modelo (MILP ou GA):
# Exporta um Excel Alocados_detalhado com cada alocação ativa (x[i,j]), custos, categorias (orig/upgrade),
# flags de restrições (indisponibilidade, independência, treino) e bem-estar (distância, autoexclusão, descompressão),
# além de um Dicionário explicando cada coluna.
# - Inclui um diagnóstico simples para entender por que alguns funcionários não foram alocados.
# - Cria grafos (NetworkX) das alocações, destacando funcionários promovidos e permitindo visualizar o grafo completo
# ou separado por tamanho do projeto, salvando as figuras em arquivo (SVG).
# ============================================================================


def exportar_alocados_detalhado(
    resultado,
    out_xlsx=os.path.join(OUTPUT_DIR, "Alocados_detalhado_LARGE_V31.xlsx"),
    thr_sel=0.9,
    incluir_dist_km=True
):

    # insumos do resultado
    x            = resultado["x"]
    y            = resultado["y"]
    funcionarios = resultado["funcionarios"]
    projetos     = resultado["projetos"]
    upgrade_cat  = resultado["upgrade_cat"]
    df_func, df_proj, df_cli = resultado["dfs"]

    pares_dist       = resultado.get("pares_dist", set())
    pares_auto       = resultado.get("pares_auto", set())
    conflitos        = resultado.get("conflitos", [])
    w_desc           = resultado.get("w_desc", {})
    sp               = resultado.get("sp", {})
    sn               = resultado.get("sn", {})
    s_papel          = resultado.get("s_papel", {})
    s_dem            = resultado.get("s_dem", {})
    indep_pairs      = resultado.get("indep_pairs", set())
    indisp_pairs     = resultado.get("indisp_pairs", set())
    pares_sem_treino = resultado.get("pares_sem_treino", set())

    perc_tempo = resultado.get("perc_tempo", None)
    if perc_tempo is None or not isinstance(perc_tempo, dict) or len(perc_tempo) == 0:
        raise ValueError(
            "resultado['perc_tempo'] está vazio ou ausente. "
            "Certifique-se de que executar_modelo retorne 'perc_tempo'."
        )

    df_func = df_func.copy()
    df_proj = df_proj.copy()
    df_cli  = df_cli.copy()

    if "ID_Func" in df_func:
        df_func["ID_Func"] = pd.to_numeric(df_func["ID_Func"], errors="coerce").astype("Int64")
    if "ID_Categ" in df_func:
        df_func["ID_Categ"] = pd.to_numeric(df_func["ID_Categ"], errors="coerce").astype("Int64")
    if "Salario_Hora" in df_func:
        df_func["Salario_Hora"] = pd.to_numeric(df_func["Salario_Hora"], errors="coerce")

    if "ID_Proj" in df_proj:
        df_proj["ID_Proj"] = pd.to_numeric(df_proj["ID_Proj"], errors="coerce").astype("Int64")
    if "Qt_horas_Previstas" in df_proj.columns:
        df_proj["Qt_horas_Previstas"] = pd.to_numeric(df_proj["Qt_horas_Previstas"], errors="coerce")

    if "ID_Cli" in df_proj:
        df_proj["ID_Cli"] = pd.to_numeric(df_proj["ID_Cli"], errors="coerce").astype("Int64")
    if "ID_Cli" in df_cli:
        df_cli["ID_Cli"] = pd.to_numeric(df_cli["ID_Cli"], errors="coerce").astype("Int64")

    orig_cat = dict(zip(
        df_func["ID_Func"].dropna().astype(int),
        df_func.get("ID_Categ", pd.Series([pd.NA]*len(df_func))).fillna(pd.NA).astype("Int64")
    ))

    sal_map = dict(zip(
        df_func["ID_Func"].dropna().astype(int),
        df_func.get("Salario_Hora", pd.Series([0.0]*len(df_func))).fillna(0.0).astype(float)
    ))

    horas_map = dict(zip(
        df_proj["ID_Proj"].dropna().astype(int),
        df_proj.get("Qt_horas_Previstas", pd.Series([0.0]*len(df_proj))).fillna(0.0).astype(float)
    ))

    if "Tam_Proj" in df_proj.columns:
        tam_proj = dict(zip(
            df_proj["ID_Proj"].dropna().astype(int),
            df_proj["Tam_Proj"].astype(str)
        ))
    else:
        tam_proj = dict(zip(
            df_proj["ID_Proj"].dropna().astype(int),
            [""] * df_proj["ID_Proj"].dropna().shape[0]
        ))

    if "ID_Cli" in df_proj.columns:
        idcli_by_proj = dict(zip(
            df_proj["ID_Proj"].dropna().astype(int),
            df_proj["ID_Cli"]
        ))
    else:
        idcli_by_proj = dict(zip(
            df_proj["ID_Proj"].dropna().astype(int),
            [pd.NA] * df_proj["ID_Proj"].dropna().shape[0]
        ))

    if "Industria" in df_proj.columns:
        ind_by_proj = dict(zip(
            df_proj["ID_Proj"].dropna().astype(int),
            df_proj["Industria"].astype(str)
        ))
    else:
        ind_by_proj = dict(zip(
            df_proj["ID_Proj"].dropna().astype(int),
            [""] * df_proj["ID_Proj"].dropna().shape[0]
        ))

    def _safe_float_col(df, col):
        return pd.to_numeric(df[col], errors="coerce").astype(float) if col in df.columns else pd.Series(dtype=float)

    lat_cli_series = _safe_float_col(df_cli, "Latitude_Cli")
    lon_cli_series = _safe_float_col(df_cli, "Longitude_Cli")
    lat_fun_series = _safe_float_col(df_func, "Latitude_Func")
    lon_fun_series = _safe_float_col(df_func, "Longitude_Func")

    lat_cli = dict(zip(df_cli.get("ID_Cli", pd.Series(dtype="Int64")).dropna().astype(int), lat_cli_series))
    lon_cli = dict(zip(df_cli.get("ID_Cli", pd.Series(dtype="Int64")).dropna().astype(int), lon_cli_series))
    lat_fun = dict(zip(df_func.get("ID_Func", pd.Series(dtype="Int64")).dropna().astype(int), lat_fun_series))
    lon_fun = dict(zip(df_func.get("ID_Func", pd.Series(dtype="Int64")).dropna().astype(int), lon_fun_series))

    # coleta de alocados
    alocados = []

    for (i, j), var in x.items():
        v = var.varValue
        if v is None or v < thr_sel:
            continue

        # categorias
        cat_orig = int(orig_cat[i]) if i in orig_cat and pd.notna(orig_cat[i]) else None
        cat_up   = upgrade_cat.get(i, cat_orig)

        # percentuais
        if cat_orig is None or cat_orig not in perc_tempo:
            raise ValueError(
                f"Categoria original {cat_orig} do funcionário {i} "
                f"não encontrada em perc_tempo."
            )

        perc_orig = float(perc_tempo[cat_orig]) / 100.0

        if cat_up is None:
            perc_up = perc_orig
        else:
            if cat_up not in perc_tempo:
                raise ValueError(
                    f"Categoria upgrade {cat_up} do funcionário {i} "
                    f"não encontrada em perc_tempo."
                )
            perc_up = float(perc_tempo[cat_up]) / 100.0

        # custo
        sal   = float(sal_map.get(i, 0.0))
        horas = float(horas_map.get(j, 0.0))

        custo_orig  = sal * horas * perc_orig * float(v)
        custo_up    = sal * horas * perc_up   * float(v)
        custo_delta = custo_up - custo_orig

        # Distância (km)
        dist_km = None
        if incluir_dist_km:
            proj_cli_id = idcli_by_proj.get(j, pd.NA)
            try:
                if (
                    i in lat_fun and i in lon_fun and
                    pd.notna(proj_cli_id) and int(proj_cli_id) in lat_cli and int(proj_cli_id) in lon_cli
                ):
                    f_coord = (float(lat_fun[i]), float(lon_fun[i]))
                    c_coord = (float(lat_cli[int(proj_cli_id)]), float(lon_cli[int(proj_cli_id)]))
                    dist_km = geodesic(f_coord, c_coord).km
            except Exception:
                dist_km = None

        # Slacks de papéis
        s_soc    = float(s_papel[(j, "soc")].varValue or 0.0)    if (j, "soc")    in s_papel else 0.0
        s_dirger = float(s_papel[(j, "dirger")].varValue or 0.0) if (j, "dirger") in s_papel else 0.0
        s_compl  = float(s_papel[(j, "compl")].varValue or 0.0)  if (j, "compl")  in s_papel else 0.0

        # Slacks de composição
        c_up = cat_up
        if c_up is not None and pd.notna(c_up):
            key = (j, int(c_up))
            sp_jc = float(sp[key].varValue or 0.0) if key in sp else 0.0
            sn_jc = float(sn[key].varValue or 0.0) if key in sn else 0.0
        else:
            sp_jc = 0.0
            sn_jc = 0.0

        # Descompressão
        wdesc_flag = 0
        wdesc_sum  = 0.0
        if w_desc:
            for (jj, kk) in conflitos:
                if jj == j and (i, j, kk) in w_desc:
                    val = float(w_desc[(i, j, kk)].varValue or 0.0)
                    if val > 1e-9:
                        wdesc_flag = 1
                        wdesc_sum += val
                if kk == j and (i, kk, j) in w_desc:
                    val = float(w_desc[(i, kk, j)].varValue or 0.0)
                    if val > 1e-9:
                        wdesc_flag = 1
                        wdesc_sum += val

        # Flags
        flag_indep   = int((i, j) in indep_pairs)
        flag_indisp  = int((i, j) in indisp_pairs)
        flag_treino  = int((i, j) in pares_sem_treino)
        flag_auto    = int((i, j) in pares_auto)
        flag_dist    = int((i, j) in pares_dist)

        alocados.append({
            "ID_Func": int(i),
            "ID_Proj": int(j),
            "x_value": float(v),

            # Upgrade/Categorias
            "Upgrade_Funcional": int(
                1
                if (cat_up is not None and cat_orig is not None and cat_up < cat_orig)
                else 0
            ),
            "Categ_Orig": cat_orig,
            "Categ_Up":   cat_up,

            # Projeto / cliente / indústria / tamanho
            "ID_Cli": (
                int(idcli_by_proj[j])
                if j in idcli_by_proj and pd.notna(idcli_by_proj[j])
                else pd.NA
            ),
            "Industria": ind_by_proj.get(j, ""),
            "Tam_Proj":  tam_proj.get(j, ""),

            # Variáveis habilitadoras do projeto
            "y_proj": float(y[j].varValue or 0.0) if j in y else 0.0,
            "s_dem_proj": float(s_dem[j].varValue or 0.0) if j in s_dem else 0.0,

            # Slacks de papéis/composição
            "s_papel_soc":    s_soc,
            "s_papel_dirger": s_dirger,
            "s_papel_compl":  s_compl,
            "comp_sp_jc":     sp_jc,
            "comp_sn_jc":     sn_jc,

            # Distância / BE
            "Dist_km": dist_km,
            "Flag_BE_Dist_NOK": int(flag_dist),
            "Flag_BE_Auto_NOK": int(flag_auto),
            "Flag_BE_Desc_usado": int(wdesc_flag),
            "Sum_BE_Desc": float(wdesc_sum),

            # Flags de exclusão
            "Flag_Indep_NOK":  int(flag_indep),
            "Flag_Indisp_NOK": int(flag_indisp),
            "Flag_Treino_NOK": int(flag_treino),

            # Custo de Folha
            "Salario_Hora":      sal,
            "Horas_Proj":        horas,
            "Perc_Tempo_Orig":   perc_orig,
            "Perc_Tempo_Up":     perc_up,
            "Custo_Folha_Orig":  custo_orig,
            "Custo_Folha_Up":    custo_up,
            "Custo_Folha_Delta": custo_delta,
        })

    df_alocados = pd.DataFrame(alocados).sort_values(
        ["ID_Proj", "ID_Func"]
    ).reset_index(drop=True)

    # Dicionário de Campos
    dicio = pd.DataFrame({
        "Coluna": [
            "x_value","Upgrade_Funcional","Categ_Orig","Categ_Up",
            "y_proj","s_dem_proj",
            "s_papel_soc","s_papel_dirger","s_papel_compl",
            "comp_sp_jc","comp_sn_jc",
            "Dist_km",
            "Flag_BE_Dist_NOK","Flag_BE_Auto_NOK","Flag_BE_Desc_usado","Sum_BE_Desc",
            "Flag_Indep_NOK","Flag_Indisp_NOK","Flag_Treino_NOK",
            "Salario_Hora","Horas_Proj","Perc_Tempo_Orig","Perc_Tempo_Up",
            "Custo_Folha_Orig","Custo_Folha_Up","Custo_Folha_Delta",
            "ID_Func","ID_Proj","ID_Cli","Industria","Tam_Proj"
        ],
        "Descrição": [
            "Valor da variável x[i,j] (alocação).",
            "1 se o funcionário foi promovido por regra de skills.",
            "Categoria original do funcionário.",
            "Categoria após upgrade por skills.",
            "Ativação do projeto y[j].",
            "Slack de assentos do projeto (assentos não preenchidos).",
            "Slack de papel 'sócio' no projeto.",
            "Slack de papel 'diretor/gerente' no projeto.",
            "Slack de papel 'complemento' no projeto.",
            "Slack + de composição (excesso) na categoria do funcionário.",
            "Slack - de composição (déficit) na categoria do funcionário.",
            "Distância estimada (km) funcionário ↔ cliente.",
            "1 se o par (i,j) excede KM_MAX (distância).",
            "1 se o par (i,j) está na lista de autoexclusão.",
            "1 se houve uso de slack de descompressão ligado ao (i,j).",
            "Soma dos w_desc vinculados ao (i,j).",
            "1 se (i,j) consta na tabela de Independência (bloqueio hard).",
            "1 se (i,j) consta na tabela de Indisponibilidade (bloqueio hard).",
            "1 se (i,j) está na lista de treinamento obrigatório NOK.",
            "Salário-hora do funcionário.",
            "Horas previstas do projeto.",
            "Percentual de tempo da categoria original (0..1).",
            "Percentual de tempo da categoria após upgrade (0..1).",
            "Custo de folha da alocação usando a categoria original.",
            "Custo de folha da alocação usando a categoria após upgrade.",
            "Diferença de custo (Up - Orig).",
            "Identificador do funcionário.",
            "Identificador do projeto.",
            "Cliente do projeto.",
            "Indústria do projeto.",
            "Tamanho do projeto (P/M/G)."
        ]
    })

    # Exportação
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df_alocados.to_excel(w, sheet_name="Alocados", index=False)
        dicio.to_excel(w, sheet_name="Dicionario", index=False)

    print(f"Alocados detalhados salvos em: {out_xlsx}")
    print(f"Linhas (alocações ativas): {len(df_alocados):,}")
    return df_alocados

# Não Alocados - why?
def diagnostico_nao_alocados(resultado, df_alocados, thr_sel=0.9):
    import pandas as pd

    df_func, df_proj, df_cli = resultado["dfs"]
    x        = resultado["x"]
    projetos = resultado["projetos"]

    indep_pairs      = resultado.get("indep_pairs")      or set()
    indisp_pairs     = resultado.get("indisp_pairs")     or set()
    pares_sem_treino = resultado.get("pares_sem_treino") or set()
    pares_dist       = resultado.get("pares_dist")       or set()
    pares_auto       = resultado.get("pares_auto")       or set()

    df_aloc_atual = resultado.get("df_aloc_atual")
    if df_aloc_atual is None:
        df_aloc_atual = pd.DataFrame()

    if not df_aloc_atual.empty and "ID_Func" in df_aloc_atual.columns:
        cont_aloc_hist = df_aloc_atual.groupby("ID_Func")["ID_Proj"].nunique().to_dict()
    else:
        cont_aloc_hist = {}

    funcionarios_base = (
        df_func["ID_Func"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )
    funcionarios_base = sorted(funcionarios_base)

    if "x_value" in df_alocados.columns:
        func_alocados = set(
            df_alocados.loc[df_alocados["x_value"] >= thr_sel, "ID_Func"].astype(int)
        )
    else:
        func_alocados = set(df_alocados["ID_Func"].astype(int))

    nao_alocados = [i for i in funcionarios_base if i not in func_alocados]

    print("\nDIAGNÓSTICO — Funcionários NÃO alocados")
    print(f"Total de funcionários na base:         {len(funcionarios_base)}")
    print(f"Total de funcionários não alocados:    {len(nao_alocados)}")

    linhas = []

    for i in nao_alocados:
        bloc_indep   = 0
        bloc_indisp  = 0
        bloc_treino  = 0
        bloc_dist    = 0
        bloc_auto    = 0
        pares_modelo = 0
        livres       = 0

        for j in projetos:
            par = (i, j)

            # 1) Independência / Indisponibilidade tiram o par ANTES do modelo
            if par in indep_pairs:
                bloc_indep += 1
                continue
            if par in indisp_pairs:
                bloc_indisp += 1
                continue

            # Se o par não está em x, ele não foi considerado na modelagem
            if par not in x:
                continue

            pares_modelo += 1

            # 2) Dentro do modelo (ou GA), checamos flags BE / Treino
            bloqueado_por_algum = False

            if par in pares_sem_treino:
                bloc_treino += 1
                bloqueado_por_algum = True

            if par in pares_dist:
                bloc_dist += 1
                bloqueado_por_algum = True

            if par in pares_auto:
                bloc_auto += 1
                bloqueado_por_algum = True

            if not bloqueado_por_algum:
                livres += 1

        # Categoria do funcionário (se existir)
        cat_i_series = df_func.loc[df_func["ID_Func"] == i, "ID_Categ"] if "ID_Categ" in df_func.columns else pd.Series([], dtype="Int64")
        cat_i = int(cat_i_series.values[0]) if not cat_i_series.empty and pd.notna(cat_i_series.values[0]) else None

        # Alocação histórica
        aloc_hist = cont_aloc_hist.get(i, 0)

        # Limite de projetos
        lim_i     = None
        lim_ating = False

        linhas.append({
            "ID_Func": i,
            "Bloq_Indep": bloc_indep,
            "Bloq_Indisp": bloc_indisp,
            "Bloq_Treino_NOK": bloc_treino,
            "Bloq_Dist_KM": bloc_dist,
            "Bloq_Auto": bloc_auto,
            "Pares_no_modelo": pares_modelo,
            "Pares_livres_BE_Treino": livres,
            "Aloc_Historica_Proj": aloc_hist,
            "Lim_Proj_Categoria": lim_i,
            "Lim_Proj_Atingido": lim_ating,
        })

    df_diag = pd.DataFrame(linhas).sort_values("ID_Func").reset_index(drop=True)

    #print("\nResumo (primeiras linhas):")
    #print(df_diag.head(20).to_string(index=False))

    return df_diag

# GRAFOS
def edges_from_ga_solution(x, thr=0.9):

    E = []
    for (fid, pid), v in x.items():
        if v is not None and float(v) >= thr:
            E.append((int(fid), int(pid)))
    return E


def _plot_graph_full_ga_from_edges(E, df_func, df_proj, upgrade_cat,
                                   titulo="Grafo - GA Completo",
                                   save_path=os.path.join(OUTPUT_DIR, "GA_grafo_FULL.svg"),
                                   node_size_func=30, node_size_proj=60):

    if not E:
        print("Sem arestas para plot.");
        return

    G = nx.DiGraph()

    # Categoria original por funcionário
    df_func_local = df_func.copy()
    df_func_local["ID_Func"] = pd.to_numeric(df_func_local["ID_Func"], errors="coerce").astype("Int64")
    df_func_local["ID_Categ"] = pd.to_numeric(df_func_local["ID_Categ"], errors="coerce").astype("Int64")
    orig_cat = dict(zip(df_func_local["ID_Func"].astype(int), df_func_local["ID_Categ"].astype(int)))

    # Nós de funcionários
    prom = []
    for i in {i for (i, _) in E}:
        G.add_node(f"F_{i}", tipo="func")
        cat_orig = orig_cat.get(i, None)
        cat_up = upgrade_cat.get(i, cat_orig)
        if cat_orig is not None and cat_up is not None and cat_up < cat_orig:
            prom.append(f"F_{i}")

    # Nós de projetos
    for j in {j for (_, j) in E}:
        G.add_node(f"P_{j}", tipo="proj")

    # Arestas
    for (i, j) in E:
        G.add_edge(f"F_{i}", f"P_{j}")

    # Layout
    pos = nx.spring_layout(G, k=0.6, iterations=400, seed=42)

    funcs = [n for n, d in G.nodes(data=True) if d.get("tipo") == "func"]
    projs = [n for n, d in G.nodes(data=True) if d.get("tipo") == "proj"]
    funcs_up = set(prom)
    funcs_orig = [n for n in funcs if n not in funcs_up]

    plt.figure(figsize=(16, 11))

    # Arestas
    nx.draw_networkx_edges(
        G, pos,
        alpha=0.25, width=0.7,
        edge_color="#8C8C8C"
    )

    # Funcionários não promovidos
    if funcs_orig:
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=funcs_orig,
            node_color="#0077FF",
            node_size=node_size_func,
            label="Funcionários"
        )

    # Funcionários promovidos
    if funcs_up:
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=list(funcs_up),
            node_color="#00D68F",
            node_size=node_size_func,
            label="Promovidos"
        )

    # Projetos
    if projs:
        nx.draw_networkx_nodes(
            G, pos,
            nodelist=projs,
            node_color="#5F6B73",
            node_size=node_size_proj,
            label="Projetos"
        )

    plt.title(titulo, fontsize=16)
    plt.axis("off")
    plt.legend(loc="lower left")
    plt.tight_layout()
    plt.savefig(save_path, dpi=220)
    plt.close()

    print(f"Grafo salvo em: {save_path}")


def plot_graph_full_ga(resultado, zip_path,
                       titulo="Grafo - GA Completo",
                       thr=0.9,
                       save_path=os.path.join(OUTPUT_DIR, "GA_grafo_FULL_GA.svg"),
                       node_size_func=30, node_size_proj=60):

    x = resultado["x"]
    E = edges_from_ga_solution(x, thr=thr)

    with zipfile.ZipFile(zip_path, 'r') as z:
        df_func = read_csv_from_zip(z, "TbFuncionarios.csv")
        df_proj = read_csv_from_zip(z, "TbProjetos.csv")

    upgrade_cat = resultado.get("upgrade_cat", {})

    _plot_graph_full_ga_from_edges(
        E,
        df_func=df_func,
        df_proj=df_proj,
        upgrade_cat=upgrade_cat,
        titulo=titulo,
        save_path=save_path,
        node_size_func=node_size_func,
        node_size_proj=node_size_proj
    )


def plot_graph_full_ga_por_tamanho(resultado, zip_path,
                                   thr=0.9,
                                   prefix=os.path.join(OUTPUT_DIR, "GA_grafo_FULL_por_tam"),
                                   node_size_func=30, node_size_proj=60):

    x = resultado["x"]
    E = edges_from_ga_solution(x, thr=thr)

    if not E:
        print("Sem arestas para plot nos grafos por tamanho.");
        return

    with zipfile.ZipFile(zip_path, 'r') as z:
        df_func = read_csv_from_zip(z, "TbFuncionarios.csv")
        df_proj = read_csv_from_zip(z, "TbProjetos.csv")

    df_proj_local = df_proj.copy()
    df_proj_local["ID_Proj"] = pd.to_numeric(df_proj_local["ID_Proj"], errors="coerce").astype("Int64")
    if PAR["COL_TAM"] not in df_proj_local.columns:
        print(f"Coluna de tamanho de projeto '{PAR['COL_TAM']}' não encontrada em TbProjetos.")
        return

    tam_map = dict(zip(
        df_proj_local["ID_Proj"].astype(int),
        df_proj_local[PAR["COL_TAM"]].astype(str)
    ))

    upgrade_cat = resultado.get("upgrade_cat", {})

    tamanhos = sorted({tam_map.get(j, "NA") for (_, j) in E})

    for tam in tamanhos:
        if tam == "NA":
            continue

        E_tam = [(i, j) for (i, j) in E if tam_map.get(j, None) == tam]

        if not E_tam:
            continue

        titulo = f"Grafo - GA Completo - Projetos tamanho {tam}"
        save_path = f"{prefix}_{tam}.svg"

        _plot_graph_full_ga_from_edges(
            E_tam,
            df_func=df_func,
            df_proj=df_proj,
            upgrade_cat=upgrade_cat,
            titulo=titulo,
            save_path=save_path,
            node_size_func=node_size_func,
            node_size_proj=node_size_proj
        )



# 10
# ============================================================================
# VISUALIZA EVOLUÇÃO
# Esta seção plota a evolução do GA ao longo das gerações:
# usa o histórico do melhor fitness (min) e do fitness médio (avg) para visualizar convergência,
# salva o gráfico em PNG e imprime a melhoria total (absoluta e percentual) do início ao fim.
# ============================================================================


def plotar_evolucao(resultado):
    history_min = resultado["history_min"]
    history_avg = resultado["history_avg"]

    plt.figure(figsize=(12, 6))
    plt.plot(history_min, label='Melhor Fitness', linewidth=2, color='green')
    plt.plot(history_avg, label='Fitness Médio', linewidth=2, color='blue', alpha=0.7)
    plt.xlabel('Geração', fontsize=12)
    plt.ylabel('Fitness', fontsize=12)
    plt.title('Evolução do GA Multi-Island', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'GA_Evolucao.png'), dpi=150, bbox_inches='tight')
    plt.show()

    melhoria = history_min[0] - history_min[-1]
    melhoria_pct = (1 - history_min[-1]/history_min[0])*100
    print(f"\n Melhoria total: {melhoria:,.0f} ({melhoria_pct:.1f}%)")



# 11
# ============================================================================
# DIAGNÓSTICO: % de funcionários alocados
# Esta função é um diagnóstico simples de cobertura:
# conta quantos funcionários aparecem pelo menos uma vez no vetor de genes (ou seja, foram alocados em algum projeto)
# e imprime/retorna o total e o percentual de funcionários alocados na solução.
# ============================================================================

def avaliar_alocacao_funcionarios(genes, case):
    """Avalia % de funcionários alocados em ao menos um projeto"""
    Nf = int(case["Nf"])
    func_ids = case["func_ids"]
    usados = np.zeros(Nf, dtype=np.uint8)
    usados[genes[genes > 0] - 1] = 1
    total_usados = usados.sum()
    perc = total_usados / Nf * 100
    print(f"\n Funcionários alocados: {total_usados}/{Nf} ({perc:.2f}%)")
    return total_usados, perc

# 12
# ============================================================================
# FINALIZAÇÃO
# Esta seção finaliza a execução do GA gerando um relatório consolidado.
# Ela imprime um resumo no console (projetos atendidos, total de alocações, % de funcionários alocados,
# média de pessoas por projeto, upgrades e tempo) e recalcula o custo total “real” da folha
# a partir dos dados do .zip usando a categoria efetiva (pós-upgrade).
# Ao final, retorna um dicionário com todas as métricas principais para uso em análises/exports.
# ============================================================================

def gerar_relatorio_final(resultado, case, zip_path):

    print("\n" + "="*75)
    titulo = "RELATÓRIO GA — BASE LARGE (Bem-Estar: ATIVO)" if case["ativar_bem_estar"] else "RELATÓRIO GA — BASE LARGE (Bem-Estar: INATIVO)"
    print(titulo)
    print("="*75)

    # Status
    print(f"Status do Solver:                Optimal")

    # Projetos ativos
    x = resultado["x"]
    projetos_com_aloc = len(set(pid for _, pid in x.keys()))
    total_projetos = case["Np"]
    print(f"Projetos ativos (y):             {projetos_com_aloc} / {total_projetos}")

    # Alocações
    total_alocacoes = len(x)
    print(f"Total de alocações (∑x):         {total_alocacoes}")

    # Profissionais alocados
    func_alocados = len(set(fid for fid, _ in x.keys()))
    total_funcionarios = case["Nf"]
    perc_func_alocados = func_alocados / total_funcionarios * 100
    print(f"Profissionais alocados (únicos): {func_alocados} / {total_funcionarios}  ({perc_func_alocados:.1f}%)")

    # Média pessoas por projeto
    media_pessoas = total_alocacoes / projetos_com_aloc if projetos_com_aloc > 0 else 0
    print(f"Média pessoas por projeto:       {media_pessoas:.2f}")

    # Upgrades
    n_upgrades = len(resultado["funcionarios_promovidos"])
    perc_upgrades = n_upgrades / total_funcionarios * 100
    print(f"Upgrades realizados:             {n_upgrades}  ({perc_upgrades:.1f}%)")

    print("-" * 75)

    # Custo total (calculado com categoria efetiva)
    custo_total = 0.0

    # Carregar dados para calcular custo real
    with zipfile.ZipFile(zip_path, 'r') as z:
        df_func = read_csv_from_zip(z, "TbFuncionarios.csv")
        df_proj = read_csv_from_zip(z, "TbProjetos.csv")
        df_categ = read_csv_from_zip(z, "TbCategorias.csv")

    def _to_float_local(sr):
        return pd.to_numeric(sr.astype(str).str.replace(",", ".", regex=False), errors="coerce")

    df_func["ID_Func"] = pd.to_numeric(df_func["ID_Func"], errors="coerce").astype("Int64")
    df_func["ID_Categ"] = pd.to_numeric(df_func["ID_Categ"], errors="coerce").astype("Int64")
    df_func["Salario_Hora"] = _to_float_local(df_func.get("Salario_Hora", pd.Series([0]*len(df_func))))
    df_proj["ID_Proj"] = pd.to_numeric(df_proj["ID_Proj"], errors="coerce").astype("Int64")
    df_proj["Qt_horas_Previstas"] = _to_float_local(df_proj.get("Qt_horas_Previstas", pd.Series([0]*len(df_proj))))
    df_categ["ID_Categ"] = pd.to_numeric(df_categ["ID_Categ"], errors="coerce").astype("Int64")
    df_categ["Perc_Tempo_Proj"] = _to_float_local(df_categ.get("Perc_Tempo_Proj", pd.Series([100]*len(df_categ))))

    sal_map = dict(zip(df_func["ID_Func"].astype(int), df_func["Salario_Hora"].fillna(0.0).astype(float)))
    horas_map = dict(zip(df_proj["ID_Proj"].astype(int), df_proj["Qt_horas_Previstas"].fillna(0.0).astype(float)))
    perc_tempo = df_categ.set_index("ID_Categ")["Perc_Tempo_Proj"].astype(float).to_dict()

    for (fid, pid), _ in x.items():
        cat_up = int(resultado["upgrade_cat"].get(fid, 1))
        sal = float(sal_map.get(fid, 0.0))
        horas = float(horas_map.get(pid, 0.0))
        perc = float(perc_tempo.get(cat_up, 100.0)) / 100.0
        custo_total += sal * horas * perc

    print(f"Custo total (folha):             R$ {custo_total:,.2f}")

    print("="*75)

    # Tempo
    tempo_exec = resultado["tempo_execucao"]
    print(f"Tempo: {tempo_exec:.2f}s")
    print()

    return {
        "status": "Optimal",
        "projetos_ativos": projetos_com_aloc,
        "total_projetos": total_projetos,
        "total_alocacoes": total_alocacoes,
        "funcionarios_alocados": func_alocados,
        "total_funcionarios": total_funcionarios,
        "perc_funcionarios_alocados": perc_func_alocados,
        "media_pessoas_projeto": media_pessoas,
        "upgrades": n_upgrades,
        "perc_upgrades": perc_upgrades,
        "custo_total": custo_total,
        "tempo_execucao": tempo_exec,
    }


# 13
# ============================================================================
# EXECUÇÃO
# Esta função é o “pipeline” completo do GA, do início ao fim:
# constrói o case em NumPy a partir do .zip; configura o DEAP;  executa o GA multi-island;
# converte a solução do GA para um formato compatível com o relatório do MILP (DummyVar com varValue);
# exporta o Excel de alocados e o diagnóstico de não alocados; plota a curva de evolução;
# gera o relatório final com métricas e cria os grafos (completo e por tamanho).
# Retorna: (resultado_ga, case, metricas).
# ============================================================================

def executar_ga_completo(zip_path=None, ativar_bem_estar=False, thr_sel=0.9, skip_reports=True):
    from collections import Counter
    import pandas as pd
    _status(f"[GA] Iniciando processamento: base={os.path.basename(zip_path)} | bem_estar={'ON' if ativar_bem_estar else 'OFF'}")

    # 1. Construir case
    case = build_case_np(zip_path, ativar_bem_estar)
    func_ids = case["func_ids"]
    proj_ids = case["proj_ids"]
    Nf = int(case["Nf"])
    Np = int(case["Np"])

    # 2. Setup DEAP
    toolbox = setup_deap(case)

    # 3. Executar GA
    resultado_ga = run_genetic_algorithm(case, toolbox)

    # 3.1 Diagnóstico de % de funcionários alocados
    avaliar_alocacao_funcionarios(resultado_ga["genes"], case)

    # 4. Montar resultado

    # 4.1 Carregar bases para df_func, df_proj, df_cli, df_aloc_atual
    tabs = carregar_tabelas_zip(zip_path)
    (df_func, df_proj, df_categ, df_cli,
     df_aloc_atual, df_sk, df_comp,
     df_ind, df_tf, df_tc, df_auto, df_desc, df_indep) = preparar_bases(
        tabs, PAR["COL_TAM"]
    )

    # 4.2 Classe dummy para imitar var.varValue do PuLP
    class DummyVar:
        def __init__(self, value):
            self.varValue = float(value)

    # 4.3 Converter x do GA
    x_ga = resultado_ga["x"]
    x_milp = {(int(fid), int(pid)): DummyVar(v) for (fid, pid), v in x_ga.items()}

    # 4.4 y[j]: projeto ativo se aparece em algum par de x
    cont_proj = Counter(pid for (_, pid) in x_ga.keys())
    y_milp = {
        int(pid): DummyVar(1.0 if cont_proj.get(pid, 0) > 0 else 0.0)
        for pid in proj_ids
    }

    # 4.5 pares de bloqueio / bem-estar a partir das matrizes booleanas do case
    indep_pairs = set()
    indisp_pairs = set()
    pares_dist = set()
    pares_auto = set()
    pares_sem_treino = set()

    indep_mat = case["indep"]
    indisp_mat = case["indisp"]
    dist_mat = case["dist"]
    auto_mat = case["auto"]
    treino_mat = case["treino"]

    for i in range(Nf):
        fid = int(func_ids[i])
        for j in range(Np):
            pid = int(proj_ids[j])

            if indep_mat[i, j]:
                indep_pairs.add((fid, pid))
            if indisp_mat[i, j] and not indep_mat[i, j]:
                indisp_pairs.add((fid, pid))
            if dist_mat[i, j]:
                pares_dist.add((fid, pid))
            if auto_mat[i, j]:
                pares_auto.add((fid, pid))
            if treino_mat[i, j]:
                pares_sem_treino.add((fid, pid))

    # 4.6 perc_tempo vem direto do case
    perc_tempo = case["perc_tempo"]

    # 4.7 Lista de funcionários / projetos
    funcionarios_ids = [int(fid) for fid in func_ids.tolist()]
    projetos_ids = [int(pid) for pid in proj_ids.tolist()]

    # 4.8 Montar dicionário resultado
    resultado_relatorio = {
        "x": x_milp,
        "y": y_milp,
        "funcionarios": funcionarios_ids,
        "projetos": projetos_ids,
        "upgrade_cat": resultado_ga["upgrade_cat"],
        "dfs": (df_func, df_proj, df_cli),
        "perc_tempo": perc_tempo,

        # pares / flags de bloqueio e BE
        "pares_dist": pares_dist,
        "pares_auto": pares_auto,
        "indep_pairs": indep_pairs,
        "indisp_pairs": indisp_pairs,
        "pares_sem_treino": pares_sem_treino,

        # slacks / variáveis que não existem no GA → deixamos vazias
        "conflitos": [],
        "w_desc": {},
        "sp": {},
        "sn": {},
        "s_papel": {},
        "s_dem": {},

        # alocação histórica (se existir)
        "df_aloc_atual": df_aloc_atual if not df_aloc_atual.empty else pd.DataFrame(),
    }

    # 5. Exportar EXCEL de alocados
    sufixo_be = "BE" if ativar_bem_estar else "NBE"
    excel_path = os.path.join(OUTPUT_DIR, f"Alocados_detalhado_GA_{sufixo_be}.xlsx")

    if not skip_reports:
        df_alocados = exportar_alocados_detalhado(
            resultado_relatorio,
            out_xlsx=excel_path,
            thr_sel=thr_sel
        )

        # 6. Diagnóstico de NÃO alocados + Excel
        df_diag = diagnostico_nao_alocados(
            resultado_relatorio,
            df_alocados,
            thr_sel=thr_sel
        )

        diag_path = os.path.join(OUTPUT_DIR, f"Diagnostico_Nao_Alocados_GA_{sufixo_be}.xlsx")
        df_diag.to_excel(diag_path, index=False)
        print(f"\nDiagnóstico de não alocados salvo em: {diag_path}")

        # 7. Curva de evolução do GA
        plotar_evolucao(resultado_ga)
    else:
        print("\n  [skip_reports] Pulando Excel, diagnóstico e curva de evolução.")

    # 8. Relatório final
    metricas = gerar_relatorio_final(resultado_ga, case, zip_path)

    if not skip_reports:
        # 9. Grafos
        print("Gerando Grafos...")

        # 9.1 Grafo completo
        plot_graph_full_ga(
            resultado=resultado_ga,
            zip_path=zip_path,
            titulo="Grafo - GA Completo (todos os projetos)",
            thr=0.9,
            save_path=os.path.join(OUTPUT_DIR, "GA_grafo_FULL_GA.svg")
        )

        # 9.2 Grafos por tamanho de projeto (P, M, G)
        plot_graph_full_ga_por_tamanho(
            resultado=resultado_ga,
            zip_path=zip_path,
            thr=0.9,
            prefix=os.path.join(OUTPUT_DIR, "GA_grafo_FULL_GA_por_tam")
        )
    else:
        print("  [skip_reports] Pulando grafos SVG.")

    # 10. Resumo final
    _status(
        f"[GA] Concluído: base={os.path.basename(zip_path)} | bem_estar={'ON' if ativar_bem_estar else 'OFF'} | "
        f"fitness={resultado_ga['fitness'][0]:,.0f} | alocacoes={len(resultado_ga['x'])} | "
        f"upgrades={len(resultado_ga['funcionarios_promovidos'])} | tempo={resultado_ga['tempo_execucao']:.1f}s"
    )

    return resultado_ga, case, metricas




# 14
# ============================================================================
# EXECUTA O MODELO GENÉTICO
# Dispara a execução completa do GA na base LARGE.
# Observação: por ser estocástico (aleatório), os resultados podem variar a cada rodada.
# Aqui o bem-estar está ativado; mude para False para rodar sem as variáveis de bem-estar.
# Ao final, a função retorna: resultado (solução do GA), case (dados/estruturas NumPy) e metricas (resumo final).
# ============================================================================




if __name__ == "__main__":
    import sys
    import os
    zip_path = sys.argv[1] if len(sys.argv) > 1 else PAR["ARQUIVO_ZIP"]
    be = '--no-be' not in sys.argv
    skip_reports = os.environ.get("GA_SKIP_REPORTS", "1") != "0"
    resultado, case, metricas = executar_ga_completo(zip_path, ativar_bem_estar=be, skip_reports=skip_reports)

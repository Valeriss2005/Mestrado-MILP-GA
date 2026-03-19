# ============================================================================
# MILP MODEL - Converted from MM-GitH for local execution
# Usage:
#   from models.milp_model import executar_modelo, PAR
#   PAR["ARQUIVO_ZIP"] = "data/instances/XSMALL_V01.zip"
#   resultado = executar_modelo(PAR["ARQUIVO_ZIP"], ativar_bem_estar=True)
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
# (deps already installed locally)

# 2
# =========================
# PARÂMETROS
# =========================
PAR = {
    "ARQUIVO_ZIP": "data/instances/LARGE_V31.zip",

    # Coluna de tamanho do projeto
    "COL_TAM": "Tam_Proj",

    # Janela de descompressão por tamanho (dias)
    "DESC_DIAS": {"P": 1, "M": 2, "G": 3},

    # Parâmetro de KM para Bem-estar
     "KM_MAX"                  : 20.00,
     "MAX_PCT_UPGRADE"         : 0.10,

    # Tolerâncias míninas necessárias para tornar viável
    "TOL_PESSOAS_ALOCADAS"    : 0.05,
    "TOL_TREINO"              : 0.02,
    "TOL_COMPOSICAO"          : 0.01,

    # Tolerâncias não serão ativadas
    "TOL_COBERTURA_PROJETOS"  : 0,
    "TOL_PAPEIS"              : 0,
    "TOL_LIM_FUNC_SOC_DIR_GS" : 0,
    "TOL_LIM_FUNC_OUTROS"     : 0,
    "TOL_DIST"                : 0,
    "TOL_AUTO"                : 0,
    "TOL_DESC"                : 0,
    "TOL_SDEM_GLOBAL"         : 0,
    "TOL_SDEM_LOCAL"          : 0,

    # Pesos não serão ativados
    "PESO_UPGRADE"            : 0,
    "PESO_DESVIO_COMP"        : 0,
    "PESO_FALTA_PAPEL"        : 0,
    "PESO_TREINO"             : 0,
    "PESO_DESC"               : 0,
    "PESO_DIST"               : 0,
    "PESO_AUTO"               : 0,

    # Solver
    "TIMEOUT"                 : 900,
    "GAPREL"                  : 0.01
}


# 3
# =========================
# BIBLIOTECAS
# =========================
import pandas as pd, numpy as np, math, os, io, zipfile, random
import time as _time
from datetime import datetime, timedelta
from geopy.distance import geodesic
import networkx as nx
import matplotlib.pyplot as plt
from pulp import *

t0 = _time.time()

# 4
# =========================
# Funções utilitárias usadas para padronizar a leitura e o pré-processamento dos dados do estudo antes da otimização.
# 1) carrega os CSVs a partir de um arquivo .zip (bases SMALL/LARGE),
# 2) normaliza nomes de arquivos removendo prefixos,
# 3) converte tipos (IDs para inteiro, valores numéricos com vírgula para float, datas em formatos diferentes para datetime),
# 4) devolve todas as tabelas prontas para uso em dataframes consistentes (df_func, df_proj, df_comp, etc.),
# 5) cálculo de distância geográfica (Haversine) e
# 6) warm-start do solver, permitindo inicializar variáveis de decisão (x e y) para o otimizador não começar do zero.
# =========================

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

    # Funcionários
    df_func["ID_Func"] = pd.to_numeric(df_func.get("ID_Func"), errors="coerce").astype("Int64")
    df_func["ID_Categ"] = pd.to_numeric(df_func.get("ID_Categ"), errors="coerce").astype("Int64")
    df_func["Salario_Hora"] = _to_float(df_func.get("Salario_Hora", pd.Series([0]*len(df_func))))
    for col in ["Latitude_Func","Longitude_Func"]:
        if col in df_func.columns: df_func[col] = _to_float(df_func[col])

    # Projetos
    df_proj["ID_Proj"] = pd.to_numeric(df_proj.get("ID_Proj"), errors="coerce").astype("Int64")
    df_proj["ID_Cli"] = pd.to_numeric(df_proj.get("ID_Cli"), errors="coerce").astype("Int64")
    df_proj[col_tam] = df_proj[col_tam].astype(str)
    for c in ["Qt_horas_Previstas","Max_Pessoas"]:
        if c in df_proj.columns: df_proj[c] = _to_float(df_proj[c])
    for c in ["Data_Inicio_Proj","Data_Fim_Proj"]:
        if c in df_proj.columns: df_proj[c] = _parse_date_series(df_proj[c])

    # Categorias
    df_categ["ID_Categ"] = pd.to_numeric(df_categ.get("ID_Categ"), errors="coerce").astype("Int64")
    df_categ["Perc_Tempo_Proj"] = _to_float(df_categ.get("Perc_Tempo_Proj", pd.Series([100]*len(df_categ))))
    df_categ["Lim_Proj"] = _to_float(df_categ.get("Lim_Proj", pd.Series([5]*len(df_categ))))

    # Clientes
    for col in ["Latitude_Cli","Longitude_Cli"]:
        if col in df_cli.columns: df_cli[col] = _to_float(df_cli[col])

    # Alocação atual
    if not df_aloc.empty:
        for c in ["ID_Func","ID_Proj"]:
            df_aloc[c] = pd.to_numeric(df_aloc[c], errors="coerce").astype("Int64")

    # Composição ideal
    if not df_comp.empty:
        df_comp["Categoria"] = pd.to_numeric(df_comp.get("Categoria"), errors="coerce").astype("Int64")
        df_comp[col_tam] = df_comp[col_tam].astype(str)
        df_comp["Qt_Ideal"] = pd.to_numeric(df_comp.get("Qt_Ideal"), errors="coerce").fillna(0).astype(int)

    # Indisponibilidade
    if not df_ind.empty:
        df_ind["ID_Func"] = pd.to_numeric(df_ind.get("ID_Func"), errors="coerce").astype("Int64")
        for c in ["Data_Inicio_Indisp","Data_Fim_Indisp"]:
            if c in df_ind.columns: df_ind[c] = _parse_date_series(df_ind[c])

    # Treinamentos
    if not df_tf.empty:
        for c in ["ID_Func","ID_Treino"]:
            if c in df_tf: df_tf[c] = pd.to_numeric(df_tf[c], errors="coerce").astype("Int64")
        for c in ["Data_Conclusao","Valido_Ate"]:
            if c in df_tf: df_tf[c] = _parse_date_series(df_tf[c])
    if not df_tc.empty and "ID_Treino" in df_tc:
        df_tc["ID_Treino"] = pd.to_numeric(df_tc["ID_Treino"], errors="coerce").astype("Int64")

    # Skills / autoexclusão / descompressão
    if not df_sk.empty:
        for c in ["ID_Func","ID_Skill"]:
            if c in df_sk: df_sk[c] = pd.to_numeric(df_sk[c], errors="coerce").astype("Int64")
        if "Data_Atualizacao" in df_sk:
            df_sk["Data_Atualizacao"] = _parse_date_series(df_sk["Data_Atualizacao"])
    for df in [df_auto, df_desc]:
        if not df.empty:
            for c in ["ID_Func","ID_Proj"]:
                if c in df: df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # Independência
    if not df_indep.empty:
        for c in ["ID_Func","ID_Proj"]:
            if c in df_indep.columns:
                df_indep[c] = pd.to_numeric(df_indep[c], errors="coerce").astype("Int64")


    return df_func, df_proj, df_categ, df_cli, df_aloc, df_sk, df_comp, df_ind, df_tf, df_tc, df_auto, df_desc, df_indep

# Haversine vetorizado (para distância)
def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0088
    dlat = np.radians(lat2-lat1)
    dlon = np.radians(lon2-lon1)
    a = np.sin(dlat/2.0)**2 + np.cos(np.radians(lat1))*np.cos(np.radians(lat2))*np.sin(dlon/2.0)**2
    return 2*R*np.arcsin(np.sqrt(a))

# Warm-start helper
def aplicar_warm_start(x_vars, y_vars, warm_start_edges=None, warm_start_y=None):
    if warm_start_edges:
        for (i,j) in warm_start_edges:
            if (i,j) in x_vars:
                x_vars[(i,j)].setInitialValue(1.0)
    if warm_start_y:
        for j, val in warm_start_y.items():
            if j in y_vars:
                y_vars[j].setInitialValue(float(val))

# 5
# =========================
# EXECUÇÃO DO MODELO
# =========================

# Lê os CSVs dentro do .zip e padroniza tipos (IDs, datas, números) para usar no modelo.
def executar_modelo(zip_path, ativar_bem_estar=True, saida_prefix="LARGE_V31.zip", warm_start=None):
    _status(f"[MILP] Iniciando processamento: base={os.path.basename(zip_path)} | bem_estar={'ON' if ativar_bem_estar else 'OFF'}")
    tabs = carregar_tabelas_zip(zip_path)
    (df_func, df_proj, df_categ, df_cli, df_aloc, df_skills, df_comp,
     df_indisp, df_tfunc, df_tcat, df_auto, df_desc, df_indep) = preparar_bases(tabs, PAR["COL_TAM"])

    # Define colunas e regras (tamanho do projeto, dias de descompressão), cria as listas de funcionarios e projetos e calcula Nf e Np.
    COL_TAM = PAR["COL_TAM"]; DESC_DIAS = PAR["DESC_DIAS"]
    funcionarios = df_func["ID_Func"].dropna().astype(int).unique().tolist()
    projetos     = df_proj["ID_Proj"].dropna().astype(int).unique().tolist()
    Nf, Np = len(funcionarios), len(projetos)

    # Monta mapas rápidos para consultas no modelo: limite de projetos por categoria, % de tempo,
    # tamanho do projeto, máximo de pessoas, alocação atual etc.
    limite_proj = df_categ.set_index("ID_Categ")["Lim_Proj"].to_dict()
    perc_tempo  = df_categ.set_index("ID_Categ")["Perc_Tempo_Proj"].to_dict()
    cont_aloc_atual = df_aloc.groupby("ID_Func")["ID_Proj"].nunique().to_dict() if not df_aloc.empty else {}
    tam = df_proj.set_index("ID_Proj")[COL_TAM].to_dict()
    max_p = df_proj.set_index("ID_Proj")["Max_Pessoas"].astype(float).to_dict()

    # Lê a TbComposicao e cria um mapa ideal_map com a quantidade ideal por (tamanho do projeto, categoria).
    ideal_map = {}
    if not df_comp.empty:
        ideal_map = (df_comp.groupby([COL_TAM,"Categoria"], as_index=False)["Qt_Ideal"]
                          .sum().set_index([COL_TAM,"Categoria"])["Qt_Ideal"].to_dict())

    # =========================
    # Upgrade por skills: calcula uma categoria efetiva (upgrade_cat) para cada funcionário.
    # Se ele está em categorias 4,5,6 e tem ≥3 skills válidos, ele sobe para categoria melhor (c-1).
    # (Otimizado: lookup dicts pré-computados)
    # =========================
    upgrade_cat = {}

    # Lookup dicts reutilizáveis (evitam .loc O(N) dentro de loops)
    _func_categ_map = dict(zip(df_func["ID_Func"], df_func["ID_Categ"].astype(int)))
    _proj_fim_map   = dict(zip(df_proj["ID_Proj"], df_proj["Data_Fim_Proj"]))
    _proj_ini_map   = dict(zip(df_proj["ID_Proj"], df_proj["Data_Inicio_Proj"]))

    skills_valid = (
        df_skills[["ID_Func", "ID_Skill", "Data_Atualizacao"]]
        .dropna(subset=["ID_Func"])
    )

    for i in funcionarios:
        c = _func_categ_map[i]

        sk_df = skills_valid[skills_valid["ID_Func"] == i]

        if sk_df.empty:
            upgrade_cat[i] = c
            continue

        valid_count = 0
        for _, row in sk_df.iterrows():

            for j in projetos:
                fim_j = _proj_fim_map[j]
                if row["Data_Atualizacao"] >= fim_j:
                    valid_count += 1
                    break

        if c in [4, 5, 6] and valid_count >= 3:
            upgrade_cat[i] = c - 1
        else:
            upgrade_cat[i] = c

    # =========================
    # Treinamentos obrigatórios: identifica pares (funcionário, projeto) que não possuem todos os treinamentos
    # obrigatórios válidos até o fim do projeto (pares_sem_treino).
    # =========================
    treinos_obrig = set(df_tcat["ID_Treino"].dropna().astype(int).unique().tolist()) if not df_tcat.empty else set()
    pares_sem_treino = set()
    if len(treinos_obrig) > 0:
        # Pré-agrupar treinamentos por funcionário para lookup O(1)
        _tfunc_groups = {}
        for _, r in df_tfunc.iterrows():
            fid = r["ID_Func"]
            if fid not in _tfunc_groups:
                _tfunc_groups[fid] = []
            _tfunc_groups[fid].append(r)

        for j in projetos:
            fim_j = _proj_fim_map[j]
            for i in funcionarios:
                rows = _tfunc_groups.get(i, [])
                concl = set()
                for r in rows:
                    if r["Valido_Ate"] >= fim_j:
                        tid = r["ID_Treino"]
                        if tid == tid:  # not NaN
                            concl.add(int(tid))
                if not (concl >= treinos_obrig):
                    pares_sem_treino.add((i,j))

    # =========================
    # Indisponibilidade (hard): marca pares (funcionário, projeto) proibidos por conflito de datas com períodos de indisponibilidade (indisp_pairs).
    # =========================
    indisp_pairs = set()
    if not df_indisp.empty:
        # Pré-agrupar indisponibilidades por funcionário
        _indisp_groups = {}
        for _, r in df_indisp.iterrows():
            fid = r["ID_Func"]
            if fid not in _indisp_groups:
                _indisp_groups[fid] = []
            _indisp_groups[fid].append((r["Data_Inicio_Indisp"], r["Data_Fim_Indisp"]))

        for i in funcionarios:
            segs = _indisp_groups.get(i, [])
            if not segs:
                continue
            for j in projetos:
                ini_j = _proj_ini_map[j]
                fim_j = _proj_fim_map[j]
                for (ini_ind, fim_ind) in segs:
                    if not (ini_j > fim_ind or fim_j < ini_ind):
                        indisp_pairs.add((i,j))
                        break

    # =========================
    # Independência (hard): marca pares (funcionário, projeto) proibidos por conflito de independência (indep_pairs).
    # =========================
    indep_pairs = set()
    if not df_indep.empty:
        for _, r in df_indep.iterrows():
            i = int(r["ID_Func"]); j = int(r["ID_Proj"])
            if i in funcionarios and j in projetos:
                indep_pairs.add((i,j))

    # =========================
    # Distância > KM_MAX (BE): se bem-estar está ativo, calcula distância funcionário–cliente e marca pares acima de KM_MAX (pares_dist).
    # =========================
    pares_dist = set()
    if ativar_bem_estar:
        cli_pos = df_cli.dropna(subset=["ID_Cli","Latitude_Cli","Longitude_Cli"])[["ID_Cli","Latitude_Cli","Longitude_Cli"]].astype(float)
        fun_pos = df_func.dropna(subset=["ID_Func","Latitude_Func","Longitude_Func"])[["ID_Func","Latitude_Func","Longitude_Func"]].astype(float)
        idcli = df_proj.set_index("ID_Proj")["ID_Cli"].astype(int).to_dict()
        latc = {int(r.ID_Cli): float(r.Latitude_Cli) for _,r in cli_pos.iterrows()}
        lonc = {int(r.ID_Cli): float(r.Longitude_Cli) for _,r in cli_pos.iterrows()}
        latf = {int(r.ID_Func): float(r.Latitude_Func) for _,r in fun_pos.iterrows()}
        lonf = {int(r.ID_Func): float(r.Longitude_Func) for _,r in fun_pos.iterrows()}
        for j in projetos:
            c = idcli.get(j)
            if c not in latc:
                continue
            lat_c, lon_c = latc[c], lonc[c]
            for i in funcionarios:
                if i not in latf:
                    continue
                d = _haversine_km(latf[i], lonf[i], lat_c, lonc[c])
                if d > PAR["KM_MAX"]:
                    pares_dist.add((i,j))

    # =========================
    # Autoexclusão (BE): se bem-estar está ativo, marca pares proibidos por autoexclusão (pares_auto).
    # =========================
    pares_auto = set()
    if ativar_bem_estar and not df_auto.empty:
        for _,r in df_auto.iterrows():
            i = int(r["ID_Func"]); j = int(r["ID_Proj"])
            if i in funcionarios and j in projetos:
                pares_auto.add((i,j))

    # =========================
    # Descompressão (BE): se bem-estar está ativo, cria conflitos entre projetos muito próximos
    # no tempo (j seguido de k dentro da janela de descanso) (conflitos).
    # =========================
    conflitos = []
    if ativar_bem_estar:
        proj_info = {
            int(r.ID_Proj):{
                "fim": pd.to_datetime(r.Data_Fim_Proj),
                "ini": pd.to_datetime(r.Data_Inicio_Proj),
                "tam": r[COL_TAM]
            } for _,r in df_proj.iterrows()
        }
        for j in projetos:
            fim_j = proj_info[j]["fim"]; tam_j = proj_info[j]["tam"]
            janela = fim_j + timedelta(days=int(PAR["DESC_DIAS"].get(tam_j,0)))
            for k in projetos:
                if j==k: continue
                ini_k = proj_info[k]["ini"]
                if (ini_k > fim_j) and (ini_k < janela):
                    conflitos.append((j,k))

    # =========================
    # Buckets de papéis (pós-upgrade): separa funcionários por grupo de papel usando upgrade_cat: sócios, diretores/gerentes, equipe.
    # =========================
    socios = [i for i in funcionarios if upgrade_cat[i]==1]
    dirger = [i for i in funcionarios if upgrade_cat[i] in [2,3]]
    compl  = [i for i in funcionarios if upgrade_cat[i] in [4,5,6]]

    # =========================
    # Variáveis de decisão: cria o problema MILP e as variáveis: x(i,j) = funcionário i alocado no projeto j (0/1)
    # y(j) = projeto j ativo (0/1) ; a(i) = funcionário i foi alocado em pelo menos 1 projeto (0/1);
    # s_dem(j) = “folga” de demanda (quantas vagas ficaram sem preencher); w_desc(i,j,k) = violação controlada de descompressão (quando aplicável)
    # =========================
    all_pairs = [(i,j) for i in funcionarios for j in projetos
                 if (i,j) not in indisp_pairs and (i,j) not in indep_pairs]

    prob = LpProblem("Alocacao_Big4_V17_clean_opt", LpMinimize)
    x = LpVariable.dicts("x", all_pairs, cat="Binary")
    y = LpVariable.dicts("y", projetos, cat="Binary")
    a = LpVariable.dicts("a", funcionarios, cat="Binary")
    s_dem = LpVariable.dicts("s_dem", projetos, lowBound=0, cat="Continuous")

    sp, sn = {}, {}
    s_papel = {}

    # Descompressão
    w_desc = {}
    if ativar_bem_estar and len(conflitos)>0:
        w_desc = {(i,j,k): LpVariable(f"wdesc_{i}_{j}_{k}", lowBound=0, upBound=1, cat="Continuous")
                  for (j,k) in conflitos for i in funcionarios}

    # =========================
    # Custo unitário: função custo_unit(i,j) calcula custo = salário/hora × horas do projeto × percentual de tempo da categoria.
    # (Otimizado: lookup dicts pré-computados em vez de .loc repetido)
    # =========================
    _cu_categ = dict(zip(df_func["ID_Func"], df_func["ID_Categ"].astype(int)))
    _cu_sal   = dict(zip(df_func["ID_Func"], df_func["Salario_Hora"].astype(float)))
    _cu_horas = dict(zip(df_proj["ID_Proj"], df_proj["Qt_horas_Previstas"].astype(float)))

    def custo_unit(i,j):
        c = _cu_categ[i]
        horas = _cu_horas[j]
        sal = _cu_sal[i]
        perc = float(perc_tempo.get(c, 100.0))/100.0
        return sal*horas*perc

    # =========================
    # Papéis desligados: TbComposicao já controla via composição
    # =========================
    s_papel = {}
    pen_papel = 0.0

    # =========================
    # COMPOSIÇÃO POR TAMANHO (Qt_Ideal ± TOL_COMPOSICAO): garante que cada projeto atenda a quantidade ideal por categoria,
    # dentro da tolerância (TOL_COMPOSICAO), quando y(j)=1.
    # =========================
    cats_sorted = sorted(df_categ["ID_Categ"].dropna().astype(int).unique())

    for j in projetos:
        t = tam[j]
        for c in cats_sorted:
            ideal = int(ideal_map.get((t, int(c)), 0))
            if ideal <= 0:
                continue

            low  = math.floor((1 - PAR["TOL_COMPOSICAO"]) * ideal)
            high = math.ceil((1 + PAR["TOL_COMPOSICAO"]) * ideal)

            qtd = lpSum(
                x[i, j]
                for (i, j2) in x
                if j2 == j and upgrade_cat[i] == int(c)
            )

            prob += qtd <= high * y[j], f"Comp_max_cat{c}_proj{j}"
            prob += qtd >= low  * y[j], f"Comp_min_cat{c}_proj{j}"


    # =========================
    # REGRAS DE LIDERANÇA: impõe limites e presença mínima de liderança (sócio/diretor/SM) conforme as regras e a composição prevista.
    # =========================
    for j in projetos:
        t = tam[j]

        # Contagem de líderes pós-upgrade
        L_socio = lpSum(
            x[i, j] for (i, j2) in x
            if j2 == j and upgrade_cat[i] == 1
        )
        L_dir = lpSum(
            x[i, j] for (i, j2) in x
            if j2 == j and upgrade_cat[i] == 2
        )
        L_sm = lpSum(
            x[i, j] for (i, j2) in x
            if j2 == j and upgrade_cat[i] == 3
        )

        # Regra 1: Max 1 sócio
        prob += L_socio <= 1 * y[j], f"GA_R1_Max1Socio_proj{j}"

        # Regra 2: Max 1 diretor
        prob += L_dir <= 1 * y[j],   f"GA_R2_Max1Dir_proj{j}"

        # Regra 3: Sócio e Diretor não coexistem
        prob += L_socio + L_dir <= 1 * y[j], f"GA_R3_NoSocioDir_proj{j}"

        # Regra 4: Max 2 líderes (Sócio + Diretor + SM)
        prob += L_socio + L_dir + L_sm <= 2 * y[j], f"GA_R4_Max2Lid_proj{j}"

        # Regra 5: Min 1 líder se TbComposição prevê liderança
        ideal_1 = int(ideal_map.get((t, 1), 0))  # sócio
        ideal_2 = int(ideal_map.get((t, 2), 0))  # diretor
        ideal_3 = int(ideal_map.get((t, 3), 0))  # SM

        if (ideal_1 + ideal_2 + ideal_3) > 0:
            prob += L_socio + L_dir + L_sm >= 1 * y[j], f"GA_R5_Min1Lid_proj{j}"


   # =========================
    # Upgrades (penalidade): conta quando um funcionário foi alocado acima da categoria original e aplica custo/peso de penalização.
    # =========================
    penalidade_upgrades = lpSum(
        PAR["PESO_UPGRADE"] * x[i, j]
        for (i, j) in x
        if upgrade_cat[i] < int(df_func.loc[df_func["ID_Func"] == i, "ID_Categ"].values[0])
    )

    upgrades_x = lpSum(
        x[i, j]
        for (i, j) in x
        if upgrade_cat[i] < int(df_func.loc[df_func["ID_Func"] == i, "ID_Categ"].values[0])
    )

    # =========================
    # BE + Treino (contadores): conta violações de treino, distância, autoexclusão e descompressão e transforma
    # em penalidades na função objetivo (pesos).
    # =========================
    viol_treino = lpSum(x[i, j] for (i, j) in x if (i, j) in pares_sem_treino) if len(pares_sem_treino) > 0 else 0
    viol_dist   = lpSum(x[i, j] for (i, j) in x if (i, j) in pares_dist)   if ativar_bem_estar and len(pares_dist)  > 0 else 0
    viol_auto   = lpSum(x[i, j] for (i, j) in x if (i, j) in pares_auto)   if ativar_bem_estar and len(pares_auto)  > 0 else 0
    pen_treino  = PAR["PESO_TREINO"] * viol_treino if len(pares_sem_treino) > 0 else 0
    pen_dist    = PAR["PESO_DIST"]   * viol_dist   if ativar_bem_estar and len(pares_dist)  > 0 else 0
    pen_auto    = PAR["PESO_AUTO"]   * viol_auto   if ativar_bem_estar and len(pares_auto)  > 0 else 0
    pen_desc    = PAR["PESO_DESC"]   * (
        lpSum(w_desc[(i, j, k)] for (j, k) in conflitos for i in funcionarios)
        if ativar_bem_estar and len(conflitos) > 0 else 0
    )

    # =========================
    # Função Objetivo: minimiza custo total + penalidades (upgrades, treino, distância, autoexclusão, descompressão).
    # =========================
    prob += (
        lpSum(x[i, j] * custo_unit(i, j) for (i, j) in x)
        + pen_papel
        + penalidade_upgrades
        #+ pen_sdem
        + pen_treino
        + pen_dist
        + pen_auto
        + pen_desc
    )

    # =========================
    # Restrições globais: Cobertura mínima de projetos (Σy), preenchimento de vagas por projeto (com s_dem),
    # limites globais/locais de slack.
    # =========================
    if Np > 0:
        prob += lpSum(y[j] for j in projetos) >= (1.0 - PAR["TOL_COBERTURA_PROJETOS"]) * Np

    for j in projetos:
        prob += lpSum(x[i, j] for (i, j2) in x if j2 == j) + s_dem[j] == float(max_p[j]) * y[j]

    # Slacks de demanda (limites globais e locais)
    assentos_totais = sum(max_p[j] for j in projetos)
    prob += lpSum(s_dem[j] for j in projetos) <= PAR["TOL_SDEM_GLOBAL"] * assentos_totais + 1e-6
    for j in projetos:
        prob += s_dem[j] <= PAR["TOL_SDEM_LOCAL"] * max_p[j] + 1e-6

    # Total de alocações
    total_x = lpSum(x[i, j] for (i, j) in x)

    # Impõe que upgrades sejam no máximo uma fração do total de alocações (ex.: ≤10% de Σx).
    prob += upgrades_x <= PAR["MAX_PCT_UPGRADE"] * total_x + 1e-6, "Limite_Upgrades_10pct"

    # Treinamento Obrigatório
    if len(pares_sem_treino) > 0:
        prob += viol_treino <= PAR["TOL_TREINO"] * total_x + 1e-6

    # Limita a quantidade de violações permitidas (ex.: distância, autoexclusão, descompressão) usando tolerâncias.
    if ativar_bem_estar and len(pares_dist)>0:
        prob += viol_dist <= PAR["TOL_DIST"] * total_x + 1e-6
    if ativar_bem_estar and len(pares_auto)>0:
        prob += viol_auto <= PAR["TOL_AUTO"] * total_x + 1e-6
    if ativar_bem_estar and len(conflitos)>0:
        for (j,k) in conflitos:
            for i in funcionarios:
                if (i,j) in x and (i,k) in x:
                    prob += x[i,j] + x[i,k] <= 1 + w_desc[(i,j,k)]
        prob += lpSum(w_desc[(i,j,k)] for (j,k) in conflitos for i in funcionarios) <= PAR["TOL_DESC"] * total_x + 1e-6

    # Ligação x → y: Se alguém é alocado no projeto, o projeto precisa estar ativo: x(i,j) ≤ y(j).
    for (i,j) in x:
        prob += x[i,j] <= y[j]

    # Controla quantos projetos cada funcionário pode assumir, considerando categoria, tolerância e alocações já existentes.
    for i in funcionarios:
        cat = int(df_func.loc[df_func["ID_Func"]==i,"ID_Categ"].values[0])
        lim = float(limite_proj.get(cat,5))
        aloc_atual = float(cont_aloc_atual.get(i,0))
        tol = PAR["TOL_LIM_FUNC_SOC_DIR_GS"] if cat in [1,2,3] else PAR["TOL_LIM_FUNC_OUTROS"]
        prob += lpSum(x[i,j] for (i2,j) in x if i2==i) + aloc_atual <= (1+tol) * lim + 1e-6

    # Pessoas alocadas (a[i]): marca funcionário como alocado se tiver pelo menos uma alocação e exige um percentual mínimo de pessoas alocadas.
    for i in funcionarios:
        prob += lpSum(x[i,j] for (i2,j) in x if i2==i) >= a[i]
    if Nf > 0:
        prob += lpSum(a[i] for i in funcionarios) >= (1.0 - PAR["TOL_PESSOAS_ALOCADAS"]) * Nf - 1e-6

    # =========================
    # Warm-start: se existir uma solução inicial, define valores iniciais para x e y para ajudar o solver começar “adiantado”.
    # =========================
    if warm_start:
        aplicar_warm_start(x, y,
                           warm_start_edges=warm_start.get("edges"),
                           warm_start_y=warm_start.get("y"))

    # =========================
    # Solver: configura e executa o solver (tempo limite, gap, threads, etc.) e obtém o status.
    # =========================
    solver = HiGHS(
    msg=True,
    timeLimit=PAR["TIMEOUT"],
    options={
        "threads": 0,
        "mip_rel_gap": PAR["GAPREL"],
        "presolve": "on",
        "random_seed": 42,
        "mip_detect_symmetry": "on",
        "mip_heuristic_effort": "high",
        "allow_unbounded_or_infeasible": "off",
    }
    )

    status = prob.solve(solver)
    status_txt = LpStatus.get(status, str(status))

    # =========================
    # Relatório básico calcula métricas finais: projetos ativos, total de alocações, pessoas únicas alocadas, média por projeto, upgrades e custo total
    # (Otimizado: lookup dicts + single-pass em vez de O(Nf*|x|) aninhado)
    # =========================
    total_y = sum(v.varValue or 0 for v in y.values())
    total_x_val = sum(x[i,j].varValue or 0 for (i,j) in x)

    # unicos: O(|x|) usando set em vez de O(Nf*|x|) com loop aninhado
    unicos = len(set(i for (i,j) in x if (x[i,j].varValue or 0) > 0.5))

    media = (total_x_val/total_y) if total_y>0 else 0.0

    # Lookup dicts para evitar .loc repetido (O(N) cada) dentro do loop
    _categ_map = dict(zip(df_func["ID_Func"], df_func["ID_Categ"].astype(int)))
    _sal_map   = dict(zip(df_func["ID_Func"], df_func["Salario_Hora"].astype(float)))
    _horas_map = dict(zip(df_proj["ID_Proj"], df_proj["Qt_horas_Previstas"].astype(float)))

    upgrades_val = sum(1 for (i,j) in x
                       if (x[i,j].varValue or 0)>=0.9 and upgrade_cat[i] < _categ_map.get(i, 0))

    custo_real = 0.0
    for (i,j) in x:
        v = x[i,j].varValue or 0.0
        if v >= 0.9:
            c = _categ_map.get(i, 0)
            horas = _horas_map.get(j, 0.0)
            sal = _sal_map.get(i, 0.0)
            perc = float(perc_tempo.get(c, 100.0))/100.0
            custo_real += sal*horas*perc

    v_treino = value(viol_treino) if len(pares_sem_treino)>0 else 0.0
    v_dist   = value(viol_dist)   if ativar_bem_estar and len(pares_dist)>0 else 0.0
    v_auto   = value(viol_auto)   if ativar_bem_estar and len(pares_auto)>0 else 0.0
    # Soma direta de varValues em vez de construir lpSum (que aloca árvore gigante em memória)
    v_desc   = sum((w_desc[(i,j,k)].varValue or 0) for (j,k) in conflitos for i in funcionarios) if ativar_bem_estar and len(conflitos)>0 else 0.0

    t1 = _time.time()

    _status(
        f"[MILP] Concluído: base={os.path.basename(zip_path)} | bem_estar={'ON' if ativar_bem_estar else 'OFF'} | "
        f"status={status_txt} | projetos_ativos={int(total_y)}/{Np} | alocacoes={int(total_x_val)} | "
        f"unicos={int(unicos)}/{Nf} | upgrades={upgrades_val} | custo=R$ {custo_real:,.2f} | tempo={(t1-t0):.2f}s"
    )

    resultado = {
        "x": x,
        "y": y,
        "funcionarios": funcionarios,
        "projetos": projetos,
        "upgrade_cat": upgrade_cat,
        "dfs": (df_func, df_proj, df_cli),

        # para exportar detalhado (seu export usa isso)
        "pares_dist": pares_dist,
        "pares_auto": pares_auto,
        "conflitos": conflitos,
        "w_desc": w_desc,
        "sp": sp,
        "sn": sn,
        "s_papel": s_papel,
        "s_dem": s_dem,
        "indep_pairs": indep_pairs,
        "indisp_pairs": indisp_pairs,
        "pares_sem_treino": pares_sem_treino,
        "perc_tempo": perc_tempo,

        # opcional (útil para debug/relatórios)
        "status_txt": status_txt,
    }

    return resultado



# 6
# =========================
# PLOT — GRAFO COMPLETO
# =========================
def edges_from_solution(x, thr=0.9):
    E = []
    for (i,j), var in x.items():
        v = var.varValue
        if v is not None and v >= thr:
            E.append((int(i), int(j)))
    return E

# 7
def plot_graph_full(x, funcionarios, projetos, df_func, df_proj, upgrade_cat,
                    titulo="Grafo - MILP Completo", thr=0.9, save_path=os.path.join(OUTPUT_DIR, "grafo_FULL_LARGE_V31.svg"),
                    node_size_func=30, node_size_proj=60):
    E = edges_from_solution(x, thr)
    if not E:
        print("Sem arestas para plot."); return
    G = nx.DiGraph()
    orig_cat = dict(zip(df_func["ID_Func"].astype(int), df_func["ID_Categ"].astype(int)))
    prom = []
    for i in {i for (i,_) in E}:
        G.add_node(f"F_{i}", tipo="func")
        if upgrade_cat[i] < orig_cat[i]: prom.append(f"F_{i}")
    for j in {j for (_,j) in E}: G.add_node(f"P_{j}", tipo="proj")
    for (i,j) in E: G.add_edge(f"F_{i}", f"P_{j}")
    pos = nx.spring_layout(G, k=0.6, iterations=400, seed=42)
    funcs = [n for n,d in G.nodes(data=True) if d["tipo"]=="func"]
    projs = [n for n,d in G.nodes(data=True) if d["tipo"]=="proj"]
    funcs_up = set(prom)
    funcs_orig = [n for n in funcs if n not in funcs_up]
    plt.figure(figsize=(16,11))
    nx.draw_networkx_edges(G, pos, alpha=0.25, width=0.7, edge_color="#8C8C8C")
    nx.draw_networkx_nodes(G, pos, nodelist=funcs_orig, node_color="#0077FF", node_size=node_size_func, label="Funcionários")
    nx.draw_networkx_nodes(G, pos, nodelist=funcs_up,   node_color="#00D68F", node_size=node_size_func, label="Promovidos")
    nx.draw_networkx_nodes(G, pos, nodelist=projs, node_color="#5F6B73", node_size=node_size_proj, label="Projetos")
    plt.title(titulo, fontsize=16); plt.axis("off"); plt.legend(loc="lower left"); plt.tight_layout()
    plt.savefig(save_path, dpi=220); plt.close()
    print(f"Grafo salvo em: {save_path}")

# 8
# =========================
# EXPORTAÇÃO — ALOCADOS DETALHADO
# =========================
def exportar_alocados_detalhado(
    resultado,
    out_xlsx=os.path.join(OUTPUT_DIR, "Alocados_detalhado_LARGE_V31.xlsx"),
    thr_sel=0.9,
    incluir_dist_km=True
):
    """
    Exporta um Excel com as alocações ativas (x>=thr_sel) e um dicionário de campos.

    Inclui:
      - Flags de bem-estar (distância, auto, descompressão)
      - Flags de exclusão (independência, indisponibilidade, treinamento)
      - Slacks de papéis e composição
      - Custo de folha por alocação com categoria original e categoria upgrade.

    Requer no dict `resultado`:
      - "perc_tempo": dict {ID_Categ -> Perc_Tempo_Proj (em %)}
      - "pares_sem_treino": set de pares (i,j) onde treino está NOK
    """
    import pandas as pd
    from geopy.distance import geodesic

    x            = resultado["x"]
    y            = resultado["y"]
    funcionarios = resultado["funcionarios"]
    projetos     = resultado["projetos"]
    upgrade_cat  = resultado["upgrade_cat"]
    df_func, df_proj, df_cli = resultado["dfs"]

    pares_dist      = resultado.get("pares_dist", set())
    pares_auto      = resultado.get("pares_auto", set())
    conflitos       = resultado.get("conflitos", [])
    w_desc          = resultado.get("w_desc", {})
    sp              = resultado.get("sp", {})
    sn              = resultado.get("sn", {})
    s_papel         = resultado.get("s_papel", {})
    s_dem           = resultado.get("s_dem", {})
    indep_pairs     = resultado.get("indep_pairs", set())
    indisp_pairs    = resultado.get("indisp_pairs", set())
    pares_sem_treino= resultado.get("pares_sem_treino", set())

    perc_tempo = resultado.get("perc_tempo", None)
    if perc_tempo is None or not isinstance(perc_tempo, dict) or len(perc_tempo) == 0:
        raise ValueError("resultado['perc_tempo'] está vazio ou ausente. "
                         "Certifique-se de que executar_modelo retorne 'perc_tempo'.")

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

    alocados = []

    for (i, j), var in x.items():
        v = var.varValue
        if v is None or v < thr_sel:
            continue

        cat_orig = int(orig_cat[i]) if i in orig_cat and pd.notna(orig_cat[i]) else None
        cat_up   = upgrade_cat.get(i, cat_orig)

        if cat_orig is None or cat_orig not in perc_tempo:
            raise ValueError(f"Categoria original {cat_orig} do funcionário {i} "
                             f"não encontrada em perc_tempo.")

        perc_orig = float(perc_tempo[cat_orig]) / 100.0

        if cat_up is None:
            perc_up = perc_orig
        else:
            if cat_up not in perc_tempo:
                raise ValueError(f"Categoria upgrade {cat_up} do funcionário {i} "
                                 f"não encontrada em perc_tempo.")
            perc_up = float(perc_tempo[cat_up]) / 100.0

        sal   = float(sal_map.get(i, 0.0))
        horas = float(horas_map.get(j, 0.0))

        custo_orig  = sal * horas * perc_orig * float(v)
        custo_up    = sal * horas * perc_up   * float(v)
        custo_delta = custo_up - custo_orig

        dist_km = None
        if incluir_dist_km:
            proj_cli_id = idcli_by_proj.get(j, pd.NA)
            try:
                if (i in lat_fun and i in lon_fun and
                    pd.notna(proj_cli_id) and int(proj_cli_id) in lat_cli and int(proj_cli_id) in lon_cli):
                    f = (float(lat_fun[i]), float(lon_fun[i]))
                    c = (float(lat_cli[int(proj_cli_id)]), float(lon_cli[int(proj_cli_id)]))
                    dist_km = geodesic(f, c).km
            except Exception:
                dist_km = None

        s_soc    = float(s_papel[(j,"soc")].varValue or 0.0)    if (j,"soc")    in s_papel else None
        s_dirger = float(s_papel[(j,"dirger")].varValue or 0.0) if (j,"dirger") in s_papel else None
        s_compl  = float(s_papel[(j,"compl")].varValue or 0.0)  if (j,"compl")  in s_papel else None

        c_up = cat_up
        sp_jc = float(sp[(j,int(c_up))].varValue or 0.0) if (j,int(c_up)) in sp and c_up is not None and pd.notna(c_up) else None
        sn_jc = float(sn[(j,int(c_up))].varValue or 0.0) if (j,int(c_up)) in sn and c_up is not None and pd.notna(c_up) else None

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

        flag_indep   = int((i, j) in indep_pairs)
        flag_indisp  = int((i, j) in indisp_pairs)
        flag_treino  = int((i, j) in pares_sem_treino)
        flag_auto    = int((i, j) in pares_auto)
        flag_dist    = int((i, j) in pares_dist)

        alocados.append({
            "ID_Func": int(i),
            "ID_Proj": int(j),
            "x_value": float(v),

            "Upgrade_Funcional": int(1 if (cat_up is not None and cat_orig is not None and cat_up < cat_orig) else 0),
            "Categ_Orig": cat_orig,
            "Categ_Up":   cat_up,

            "ID_Cli": (int(idcli_by_proj[j]) if j in idcli_by_proj and pd.notna(idcli_by_proj[j]) else pd.NA),
            "Industria": ind_by_proj.get(j, ""),
            "Tam_Proj": tam_proj.get(j, ""),

            "y_proj": float(y[j].varValue or 0.0) if j in y else None,
            "s_dem_proj": float(s_dem[j].varValue or 0.0) if j in s_dem else None,
            "s_papel_soc": s_soc,
            "s_papel_dirger": s_dirger,
            "s_papel_compl": s_compl,
            "comp_sp_jc": sp_jc,
            "comp_sn_jc": sn_jc,

            "Dist_km": dist_km,
            "Flag_BE_Dist_NOK": flag_dist,
            "Flag_BE_Auto_NOK": flag_auto,
            "Flag_BE_Desc_usado": int(wdesc_flag),
            "Sum_BE_Desc": float(wdesc_sum),

             "Flag_Indep_NOK": flag_indep,
            "Flag_Indisp_NOK": flag_indisp,
            "Flag_Treino_NOK": flag_treino,

            "Salario_Hora": sal,
            "Horas_Proj": horas,
            "Perc_Tempo_Orig": perc_orig,
            "Perc_Tempo_Up": perc_up,
            "Custo_Folha_Orig": custo_orig,
            "Custo_Folha_Up": custo_up,
            "Custo_Folha_Delta": custo_delta,
        })

    df_alocados = pd.DataFrame(alocados).sort_values(["ID_Proj", "ID_Func"]).reset_index(drop=True)

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
            "Slack de papel 'consultoria' no projeto.",
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

    # ---------- exportação ----------
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as w:
        df_alocados.to_excel(w, sheet_name="Alocados", index=False)
        dicio.to_excel(w, sheet_name="Dicionario", index=False)

    print(f"Alocados detalhados salvos em: {out_xlsx}")
    print(f"Linhas (alocações ativas): {len(df_alocados):,}")

    return df_alocados



# 9
# Gera lista de não alocados para conferência se realmente deveriam estar nesta lista

def diagnostico_nao_alocados(resultado, df_alocados, thr_sel=0.9):
    """
    Gera um diagnóstico por funcionário NÃO alocado, indicando quantos projetos
    estão bloqueados por: Independência, Indisponibilidade, Treino NOK,
    Distância > KM_MAX, Autoexclusão, e se o limite de projetos já estava atingido.

    Retorna um DataFrame com uma linha por funcionário não alocado.
    """
    df_func, df_proj, df_cli = resultado["dfs"]
    x             = resultado["x"]
    projetos      = resultado["projetos"]

    indep_pairs      = resultado.get("indep_pairs", set())
    indisp_pairs     = resultado.get("indisp_pairs", set())
    pares_sem_treino = resultado.get("pares_sem_treino", set())
    pares_dist       = resultado.get("pares_dist", set())
    pares_auto       = resultado.get("pares_auto", set())

    df_aloc_atual = resultado.get("df_aloc_atual", pd.DataFrame())

    if not df_aloc_atual.empty and "ID_Func" in df_aloc_atual.columns:
        cont_aloc_hist = df_aloc_atual.groupby("ID_Func")["ID_Proj"].nunique().to_dict()
    else:
        cont_aloc_hist = {}


    funcionarios_base = sorted(df_func["ID_Func"].dropna().astype(int).unique().tolist())


    if "x_value" in df_alocados.columns:
        func_alocados = set(
            df_alocados.loc[df_alocados["x_value"] >= thr_sel, "ID_Func"].astype(int)
        )
    else:
        func_alocados = set(df_alocados["ID_Func"].astype(int))

    nao_alocados = [i for i in funcionarios_base if i not in func_alocados]

    print("\n=== DIAGNÓSTICO — Funcionários NÃO alocados ===")
    print(f"Total de funcionários na base:        {len(funcionarios_base)}")
    print(f"Total de funcionários não alocados:   {len(nao_alocados)}")

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

            if par in indep_pairs:
                bloc_indep += 1
                continue
            if par in indisp_pairs:
                bloc_indisp += 1
                continue

            if par not in x:
                continue

            pares_modelo += 1

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

        cat_i = df_func.loc[df_func["ID_Func"] == i, "ID_Categ"]
        cat_i = int(cat_i.values[0]) if not cat_i.empty and pd.notna(cat_i.values[0]) else None

        aloc_hist = cont_aloc_hist.get(i, 0)
        lim_i     = None
        lim_ating = False

        if cat_i is not None:
            lim_i = None
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
            "Lim_Proj_Atingido": lim_ating,
        })

    df_diag = (
        pd.DataFrame(linhas)
        .sort_values("ID_Func")
        .reset_index(drop=True)
    )

    print("\nResumo (primeiras linhas):")
    print(df_diag.head(3).to_string(index=False))


    return df_diag



# 10
# =========================
# EXECUÇÃO DO MODELO E COMPLEMENTOS
# =========================
import time as _time
if __name__ == "__main__":
    import sys
    zip_path = sys.argv[1] if len(sys.argv) > 1 else PAR["ARQUIVO_ZIP"]
    be = '--no-be' not in sys.argv
    executar_modelo(zip_path, ativar_bem_estar=be, saida_prefix=os.path.basename(zip_path))

# 11
# Gera grafos por tamanho de projeto
def plot_graph_por_tamanho(resultado, tamanho="P", thr=0.9,
                           titulo=None, save_path=None,
                           node_size_func=30, node_size_proj=30, seed=42):
    import networkx as nx, matplotlib.pyplot as plt
    import numpy as np, math

    x            = resultado["x"]
    upgrade_cat  = resultado["upgrade_cat"]
    df_func, df_proj, _ = resultado["dfs"]

    dfp = df_proj.copy()
    dfp["ID_Proj"] = dfp["ID_Proj"].astype(int)
    proj_ids = set(dfp.loc[dfp["Tam_Proj"].astype(str)==str(tamanho), "ID_Proj"].tolist())
    if not proj_ids:
        print(f"Sem projetos do tamanho {tamanho}."); return

    E = []
    for (i,j), var in x.items():
        v = var.varValue
        if v is not None and v >= thr and j in proj_ids:
            E.append((int(i), int(j)))
    if not E:
        print(f"Sem arestas para {tamanho}."); return

    G = nx.DiGraph()
    orig_cat = dict(zip(df_func["ID_Func"].astype(int), df_func["ID_Categ"].astype(int)))
    funcs = sorted({i for (i,_) in E})
    projs = sorted({j for (_,j) in E})
    for i in funcs:
        G.add_node(f"F_{i}", tipo="func", promovido=(upgrade_cat.get(i,99) < orig_cat.get(i,99)))
    for j in projs:
        G.add_node(f"P_{j}", tipo="proj")
    for (i,j) in E:
        G.add_edge(f"F_{i}", f"P_{j}")

    pos = nx.spring_layout(G, k=0.6, iterations=400, seed=seed)
    funcs_up  = [n for n,d in G.nodes(data=True) if d["tipo"]=="func" and d.get("promovido", False)]
    funcs_ok  = [n for n,d in G.nodes(data=True) if d["tipo"]=="func" and not d.get("promovido", False)]
    projs_nds = [n for n,d in G.nodes(data=True) if d["tipo"]=="proj"]

    plt.figure(figsize=(16,11))
    nx.draw_networkx_edges(G, pos, alpha=0.25, width=0.7, edge_color="#8C8C8C")
    nx.draw_networkx_nodes(G, pos, nodelist=funcs_ok, node_color="#0077FF", node_size=node_size_func, label="Funcionários")
    nx.draw_networkx_nodes(G, pos, nodelist=funcs_up,   node_color="#00D68F", node_size=node_size_func, label="Promovidos")
    nx.draw_networkx_nodes(G, pos, nodelist=projs_nds, node_color="#5F6B73", node_size=node_size_proj, label="Projetos")

    if titulo is None:   titulo = f"Grafo - MILP por Tamanho {tamanho}"
    if save_path is None: save_path = os.path.join(OUTPUT_DIR, f"grafo_Tam_{tamanho}.svg")
    plt.title(titulo, fontsize=16); plt.axis("off"); plt.legend(loc="lower left"); plt.tight_layout()
    plt.savefig(save_path, format="svg", transparent=True, bbox_inches="tight")
    print(f"Grafo {tamanho} salvo em: {save_path} | Projetos: {len(projs)} | Funcionários: {len(funcs)} | Arestas: {len(E)}")






# 12
# Analise por tamanho de projeto (P/M/G) a partir do Excel "Alocados_detalhado.xls"
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def _pct(x):
    """Converte proporção (0..1) para % (0..100)."""
    return 100.0 * float(x)

def _seguro_media(sr):
    """Média com tolerância a séries vazias."""
    return float(sr.mean()) if len(sr) else 0.0

def _seguro_sum(sr):
    return float(sr.sum()) if len(sr) else 0.0

def analisar_por_tamanho(
    path_excel: str,
    sheet_name: str = "Alocados",
    salvar_excel_resumo: bool = True,
    out_excel: str = None,
    salvar_graficos: bool = True,
    out_dir_figs: str = None,
    mostrar_print: bool = True
):
    """
    Lê o Excel exportado por exportar_alocados_detalhado(...), calcula métricas por Tam_Proj (P/M/G)
    e retorna um DataFrame-resumo. Opcionalmente salva gráficos e Excel com o resumo.
    """

    path_excel = Path(path_excel)
    if not path_excel.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path_excel}")

    df = pd.read_excel(path_excel, sheet_name=sheet_name)

    cols_flags = ["Flag_BE_Dist_NOK","Flag_BE_Auto_NOK","Flag_BE_Desc_usado"]
    cols_papel = ["s_papel_soc","s_papel_dirger","s_papel_compl"]
    cols_comp  = ["comp_sp_jc","comp_sn_jc"]
    cols_base  = ["ID_Proj","ID_Func","Tam_Proj","Upgrade_Funcional"]
    cols_exclusao = [
        "Flag_Indep_NOK",
        "Flag_Indisp_NOK",
        "Flag_Treino_NOK",        ]

    for c in cols_flags + cols_papel + cols_comp + cols_exclusao:
        if c not in df.columns:
            df[c] = 0.0

    for c in cols_base:
        if c not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente no Excel: {c}")

    for c in cols_flags + cols_papel + cols_comp + cols_exclusao + ["Upgrade_Funcional"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    df["Tam_Proj"] = df["Tam_Proj"].astype(str).str.upper().str.strip()

    def _tam_medio_equipe(sub):
        por_proj = sub.groupby("ID_Proj", as_index=False)["ID_Func"].count()
        return _seguro_media(por_proj["ID_Func"])

    def _grau_medio_func(sub):
        por_func = sub.groupby("ID_Func", as_index=False)["ID_Proj"].nunique()
        return _seguro_media(por_func["ID_Proj"])

    def _pct_multi(sub):
        por_func = sub.groupby("ID_Func", as_index=False)["ID_Proj"].nunique()
        if len(por_func) == 0:
            return 0.0
        return _pct((por_func["ID_Proj"] > 1).mean())

    def _pct_upgrades(sub):
        if len(sub) == 0:
            return 0.0
        return _pct(sub["Upgrade_Funcional"].mean())

    def _slack_papeis(sub):
        if len(sub) == 0:
            return 0.0, 0.0
        any_papel = ((sub["s_papel_soc"]>1e-9) |
                     (sub["s_papel_dirger"]>1e-9) |
                     (sub["s_papel_compl"]>1e-9)).mean()
        mag_media = (sub["s_papel_soc"] +
                     sub["s_papel_dirger"] +
                     sub["s_papel_compl"]).mean()
        return _pct(any_papel), float(mag_media)

    def _slack_comp(sub):
        if len(sub) == 0:
            return 0.0, 0.0
        any_comp = ((sub["comp_sp_jc"]>1e-9) |
                    (sub["comp_sn_jc"]>1e-9)).mean()
        mag_media = (sub["comp_sp_jc"] + sub["comp_sn_jc"]).mean()
        return _pct(any_comp), float(mag_media)

    def _be_flags(sub):
        if len(sub) == 0:
            return 0.0, 0.0, 0.0
        p_dist = _pct(sub["Flag_BE_Dist_NOK"].mean())
        p_auto = _pct(sub["Flag_BE_Auto_NOK"].mean())
        p_desc = _pct(sub["Flag_BE_Desc_usado"].mean())
        return p_dist, p_auto, p_desc

    def _contagens(sub):
        n_proj = sub["ID_Proj"].nunique()
        n_aloc = len(sub)
        n_func = sub["ID_Func"].nunique()
        return n_proj, n_aloc, n_func

    resumo_rows = []

    for tam, sub in df.groupby("Tam_Proj", as_index=False):

        equipe_med = _tam_medio_equipe(sub)
        grau_med   = _grau_medio_func(sub)
        pct_multi  = _pct_multi(sub)
        pct_upg    = _pct_upgrades(sub)

        pct_sl_papel, mag_sl_papel = _slack_papeis(sub)
        pct_sl_comp,  mag_sl_comp  = _slack_comp(sub)

        be_dist, be_auto, be_desc  = _be_flags(sub)

        n_proj, n_aloc, n_func = _contagens(sub)

        pct_indep   = _pct(sub["Flag_Indep_NOK"].mean())
        pct_indisp  = _pct(sub["Flag_Indisp_NOK"].mean())
        pct_treino  = _pct(sub["Flag_Treino_NOK"].mean())

        resumo_rows.append({
            "Tam_Proj": tam,
            "Equipe_media": round(equipe_med, 2),
            "Pct_Upgrades": round(pct_upg, 2),
            "Grau_medio_func": round(grau_med, 2),
            "Pct_multi_alocado": round(pct_multi, 2),
            "Pct_Slack_Papeis": round(pct_sl_papel, 2),
            "Slack_Papeis_Media": round(mag_sl_papel, 4),
            "Pct_Slack_Composicao": round(pct_sl_comp, 2),
            "Slack_Composicao_Media": round(mag_sl_comp, 4),
            "Pct_BE_Dist": round(be_dist, 2),
            "Pct_BE_Auto": round(be_auto, 2),
            "Pct_BE_Desc": round(be_desc, 2),
            "Pct_Indep": round(pct_indep, 2),
            "Pct_Indisp": round(pct_indisp, 2),
            "Pct_Treino_NOK": round(pct_treino, 2),
            "N_Projetos": int(n_proj),
            "N_Alocacoes": int(n_aloc),
            "N_Funcionarios_Unicos": int(n_func),
        })

    df_resumo = pd.DataFrame(resumo_rows).sort_values("Tam_Proj").reset_index(drop=True)

    if mostrar_print:
        print("\n=== RESUMO POR TAMANHO (P/M/G) ===")
        print(df_resumo.to_string(index=False))

    if salvar_excel_resumo:
        if out_excel is None:
            out_excel = path_excel.with_name(f"{path_excel.stem}_Resumo_PMG.xlsx")
        df_resumo.to_excel(out_excel, index=False)
        if mostrar_print:
            print(f"\nResumo salvo em: {out_excel}")

    if salvar_graficos:
        if out_dir_figs is None:
            out_dir_figs = path_excel.parent
        out_dir_figs = Path(out_dir_figs)
        out_dir_figs.mkdir(parents=True, exist_ok=True)

        def _plot_bar(col, ylabel):
            plt.figure(figsize=(7,5))
            x = df_resumo["Tam_Proj"].astype(str)
            y = df_resumo[col].astype(float)
            plt.bar(x, y)
            plt.xlabel("Tamanho do Projeto (P/M/G)")
            plt.ylabel(ylabel)
            plt.title(f"{ylabel} por Tamanho")
            plt.tight_layout()
            png_path = out_dir_figs / f"{col}_por_Tamanho.png"
            plt.savefig(png_path, dpi=180)
            plt.close()

        metricas_plot = [
            ("Equipe_media", "Tamanho médio da equipe"),
            ("Pct_Upgrades", "% de upgrades"),
            ("Grau_medio_func", "Grau médio dos funcionários"),
            ("Pct_multi_alocado", "% de multi-alocados"),
            ("Pct_Slack_Papeis", "% alocações com slack de papéis"),
            ("Pct_Slack_Composicao", "% alocações com slack de composição"),
            ("Pct_BE_Dist", "% BE Distância"),
            ("Pct_BE_Auto", "% BE Autoexclusão"),
            ("Pct_BE_Desc", "% BE Descompressão"),
            ("Pct_Indep", "% exclusões por Independência"),
            ("Pct_Indisp", "% exclusões por Indisponibilidade"),
            ("Pct_Treino_NOK", "% Treinamento não válido"),
        ]

        for col, ylabel in metricas_plot:
            _plot_bar(col, ylabel)

        if mostrar_print:
            print(f"Gráficos salvos em: {out_dir_figs}")

    return df_resumo


# 13
# =======================
# Executa a parte dos grafos por tamanho
# =======================



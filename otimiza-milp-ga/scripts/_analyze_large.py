"""
Análise milimétrica da base LARGE_V31 para extrair todas as proporções
que devem ser replicadas nas instâncias sintéticas.
"""
import pandas as pd, numpy as np, os, zipfile, io, json
from geopy.distance import geodesic

ZIP = "data/instances/LARGE_V31.zip"

def load(zip_path):
    tables = {}
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.endswith('.csv'):
                key = os.path.basename(name)
                # Remove prefixes
                for pref in ["LARGE_", "SMALL_"]:
                    if key.startswith(pref):
                        key = key[len(pref):]
                key = key.replace(".csv","")
                raw = zf.read(name)
                tables[key] = pd.read_csv(io.BytesIO(raw), sep=";", encoding="latin-1")
    return tables

t = load(ZIP)
print("=== TABELAS CARREGADAS ===")
for k, v in sorted(t.items()):
    print(f"  {k}: {v.shape[0]} linhas x {v.shape[1]} colunas")

# ============================================================
# 1. FUNCIONÁRIOS
# ============================================================
df_func = t["TbFuncionarios"]
Nf = len(df_func)
print(f"\n=== 1. FUNCIONÁRIOS: {Nf} ===")

# Distribuição por categoria
cat_counts = df_func["ID_Categ"].value_counts().sort_index()
print("\nDistribuição por categoria:")
for cat, cnt in cat_counts.items():
    print(f"  Cat {cat}: {cnt} ({cnt/Nf*100:.1f}%)")

# ============================================================
# 2. PROJETOS
# ============================================================
df_proj = t["TbProjetos"]
Np = len(df_proj)
print(f"\n=== 2. PROJETOS: {Np} ===")

# Distribuição por tamanho
tam_counts = df_proj["Tam_Proj"].value_counts()
print("\nDistribuição por tamanho:")
for tam in ["P", "M", "G"]:
    cnt = tam_counts.get(tam, 0)
    print(f"  {tam}: {cnt} ({cnt/Np*100:.1f}%)")

# Max_Pessoas por tamanho
print("\nMax_Pessoas por tamanho:")
for tam in ["P","M","G"]:
    sub = df_proj[df_proj["Tam_Proj"]==tam]["Max_Pessoas"]
    print(f"  {tam}: mean={sub.mean():.1f}, min={sub.min()}, max={sub.max()}, median={sub.median():.0f}")

# Total de vagas (seats)
total_seats = df_proj["Max_Pessoas"].sum()
print(f"\nTotal de vagas (seats): {total_seats}")
print(f"Ratio Nf/seats: {Nf/total_seats:.3f}")
print(f"Ratio seats/Nf: {total_seats/Nf:.3f}")
print(f"Ratio Np/Nf: {Np/Nf:.3f}")

# ============================================================
# 3. COMPOSIÇÃO IDEAL
# ============================================================
df_comp = t["TbComposicao"]
print(f"\n=== 3. COMPOSIÇÃO (TbComposicao) ===")
print(df_comp.to_string(index=False))

# Calcular a demanda total por categoria
print("\nDemanda total por categoria (Qt_Ideal × nº projetos de cada tam):")
demand_by_cat = {}
for _, row in df_comp.iterrows():
    tam = row["Tam_Proj"]
    cat = row["Categoria"]
    ideal = row["Qt_Ideal"]
    n_proj_tam = tam_counts.get(tam, 0)
    total_demand = ideal * n_proj_tam
    demand_by_cat[cat] = demand_by_cat.get(cat, 0) + total_demand
    print(f"  Tam={tam}, Cat={cat}: Qt_Ideal={ideal} × {n_proj_tam} projs = {total_demand}")

print("\nResumo demanda vs oferta por categoria:")
for cat in sorted(demand_by_cat.keys()):
    supply = cat_counts.get(cat, 0)
    demand = demand_by_cat[cat]
    ratio = supply/demand if demand > 0 else float('inf')
    deficit = supply - demand
    print(f"  Cat {cat}: supply={supply}, demand={demand}, deficit={deficit:+d}, ratio={ratio:.2f}")

total_demand = sum(demand_by_cat.values())
print(f"\nTotal demand: {total_demand}, Total supply: {Nf}")
print(f"Supply/Demand ratio: {Nf/total_demand:.3f}")

# ============================================================
# 4. CATEGORIAS (Lim_Proj, Perc_Tempo)
# ============================================================
df_cat = t["TbCategorias"]
print(f"\n=== 4. CATEGORIAS (TbCategorias) ===")
print(df_cat.to_string(index=False))

# ============================================================
# 5. ALOCAÇÃO ATUAL
# ============================================================
df_aloc = t["TbProjetos_Alocacao"]
print(f"\n=== 5. ALOCAÇÃO ATUAL: {len(df_aloc)} registros ===")
aloc_per_func = df_aloc.groupby("ID_Func").size()
print(f"Funcs com alocação atual: {aloc_per_func.shape[0]} / {Nf}")
print(f"Alocações por func: mean={aloc_per_func.mean():.1f}, max={aloc_per_func.max()}, median={aloc_per_func.median():.0f}")

# Check Lim_Proj vs aloc_atual
merged = df_aloc.groupby("ID_Func").size().reset_index(name="aloc_atual")
merged = merged.merge(df_func[["ID_Func","ID_Categ"]], on="ID_Func")
merged = merged.merge(df_cat[["ID_Categ","Lim_Proj"]], on="ID_Categ")
merged["folga"] = merged["Lim_Proj"] - merged["aloc_atual"]
print(f"\nFolga (Lim_Proj - aloc_atual):")
print(f"  min={merged['folga'].min()}, mean={merged['folga'].mean():.1f}, max={merged['folga'].max()}")
print(f"  Funcs com folga <= 0: {(merged['folga']<=0).sum()}")
print(f"  Funcs com folga <= 1: {(merged['folga']<=1).sum()}")

# ============================================================
# 6. SKILLS / UPGRADES
# ============================================================
df_skill = t["TbFuncionarios_Skill"]
print(f"\n=== 6. SKILLS: {len(df_skill)} registros ===")
skills_per_func = df_skill.groupby("ID_Func").size()
eligible = df_func[df_func["ID_Categ"].isin([4,5,6])]["ID_Func"]
upgradeable = skills_per_func[skills_per_func >= 3].index
upgradeable_eligible = set(upgradeable) & set(eligible)
print(f"Funcs elegíveis para upgrade (cat 4,5,6): {len(eligible)}")
print(f"Funcs com >=3 skills: {len(upgradeable)}")
print(f"Funcs com upgrade efetivo: {len(upgradeable_eligible)}")
print(f"% upgrade: {len(upgradeable_eligible)/Nf*100:.1f}%")

# ============================================================
# 7. INDISPONIBILIDADE
# ============================================================
df_indisp = t.get("TbFuncionarios_Indisponiveis", pd.DataFrame())
print(f"\n=== 7. INDISPONIBILIDADE: {len(df_indisp)} registros ===")
if not df_indisp.empty:
    indisp_funcs = df_indisp["ID_Func"].nunique()
    print(f"Funcs com indisponibilidade: {indisp_funcs} ({indisp_funcs/Nf*100:.1f}%)")

# ============================================================
# 8. TREINAMENTOS
# ============================================================
df_treino = t.get("TbFuncionarios_Treinamentos_Obrigatorios", pd.DataFrame())
df_treino_req = t.get("TbTreinamentos_Obrigatorios", pd.DataFrame())
print(f"\n=== 8. TREINAMENTOS ===")
print(f"Registros de treinamentos realizados: {len(df_treino)}")
print(f"Treinamentos obrigatórios definidos: {len(df_treino_req)}")
if not df_treino.empty:
    treino_per_func = df_treino.groupby("ID_Func").size()
    print(f"Funcs com pelo menos 1 treinamento: {len(treino_per_func)} ({len(treino_per_func)/Nf*100:.1f}%)")
    print(f"Treinamentos por func: mean={treino_per_func.mean():.1f}, max={treino_per_func.max()}")

# ============================================================
# 9. BEM-ESTAR: AUTOEXCLUSÃO
# ============================================================
df_auto = t.get("TbProjetos_Autoexclusao", pd.DataFrame())
print(f"\n=== 9. AUTOEXCLUSÃO: {len(df_auto)} pares ===")
if not df_auto.empty:
    auto_funcs = df_auto["ID_Func"].nunique()
    auto_projs = df_auto["ID_Proj"].nunique()
    print(f"Funcs envolvidos: {auto_funcs} ({auto_funcs/Nf*100:.1f}%)")
    print(f"Projs envolvidos: {auto_projs} ({auto_projs/Np*100:.1f}%)")
    auto_per_func = df_auto.groupby("ID_Func").size()
    print(f"Pares por func: mean={auto_per_func.mean():.1f}, max={auto_per_func.max()}")

# ============================================================
# 10. BEM-ESTAR: DESCOMPRESSÃO
# ============================================================
df_desc = t.get("TbProjetos_Descompressao", pd.DataFrame())
print(f"\n=== 10. DESCOMPRESSÃO: {len(df_desc)} pares ===")
if not df_desc.empty:
    desc_funcs = df_desc["ID_Func"].nunique() if "ID_Func" in df_desc.columns else 0
    print(f"Funcs envolvidos: {desc_funcs} ({desc_funcs/Nf*100:.1f}%)")
    # Pares por func
    if "ID_Func" in df_desc.columns:
        desc_per_func = df_desc.groupby("ID_Func").size()
        print(f"Conflitos por func: mean={desc_per_func.mean():.1f}, max={desc_per_func.max()}")

# ============================================================
# 11. INDEPENDÊNCIA
# ============================================================
df_indep = t.get("TbProjetos_Independencia", pd.DataFrame())
print(f"\n=== 11. INDEPENDÊNCIA: {len(df_indep)} pares ===")
if not df_indep.empty:
    indep_funcs = df_indep["ID_Func"].nunique()
    print(f"Funcs envolvidos: {indep_funcs} ({indep_funcs/Nf*100:.1f}%)")

# ============================================================
# 12. GEOGRAFIA
# ============================================================
df_cli = t["TbClientes"]
print(f"\n=== 12. GEOGRAFIA ===")
print(f"Clientes: {len(df_cli)}")

# Check distance distribution
lat_f = "Latitude_Func" if "Latitude_Func" in df_func.columns else None
lon_f = "Longitude_Func" if "Longitude_Func" in df_func.columns else None
lat_c = "Latitude_Cli" if "Latitude_Cli" in df_cli.columns else None
lon_c = "Longitude_Cli" if "Longitude_Cli" in df_cli.columns else None

if lat_f and lat_c:
    # Sample distances
    print("Calculando distribuição de distâncias (amostra)...")
    dists = []
    for _, f in df_func.iterrows():
        for _, c in df_cli.iterrows():
            try:
                floc = (float(str(f[lat_f]).replace(",",".")), float(str(f[lon_f]).replace(",",".")))
                cloc = (float(str(c[lat_c]).replace(",",".")), float(str(c[lon_c]).replace(",",".")))
                d = geodesic(floc, cloc).km
                dists.append(d)
            except:
                pass
    if dists:
        dists = np.array(dists)
        print(f"Total pares func-cli: {len(dists)}")
        print(f"Distância: min={dists.min():.1f}km, mean={dists.mean():.1f}km, median={np.median(dists):.1f}km, max={dists.max():.1f}km")
        print(f"Pares ≤ 20km: {(dists<=20).sum()} ({(dists<=20).sum()/len(dists)*100:.1f}%)")
        print(f"Pares > 20km: {(dists>20).sum()} ({(dists>20).sum()/len(dists)*100:.1f}%)")
        
    # Unique cities
    func_cities = df_func["Cidade_Func"].unique() if "Cidade_Func" in df_func.columns else []
    cli_cities = df_cli["Cidade_Cli"].unique() if "Cidade_Cli" in df_cli.columns else []
    print(f"\nCidades de funcionários: {list(func_cities)}")
    print(f"Cidades de clientes: {list(cli_cities)}")

# ============================================================
# 13. RESUMO DE PROPORÇÕES-CHAVE
# ============================================================
print("\n" + "="*60)
print("RESUMO DE PROPORÇÕES-CHAVE (LARGE_V31)")
print("="*60)
proportions = {
    "Nf": Nf,
    "Np": Np,
    "Np/Nf": round(Np/Nf, 4),
    "total_seats": int(total_seats),
    "seats/Nf": round(total_seats/Nf, 4),
    "cat_dist_%": {int(k): round(v/Nf*100, 2) for k,v in cat_counts.items()},
    "tam_dist_%": {k: round(v/Np*100, 2) for k,v in tam_counts.items()},
    "supply_demand_ratio": round(Nf/total_demand, 4),
    "upgrade_%": round(len(upgradeable_eligible)/Nf*100, 2),
    "indisp_%": round(indisp_funcs/Nf*100, 2) if not df_indisp.empty else 0,
    "auto_pares": len(df_auto),
    "auto_%_funcs": round(auto_funcs/Nf*100, 2) if not df_auto.empty else 0,
    "desc_pares": len(df_desc),
    "indep_pares": len(df_indep),
}
print(json.dumps(proportions, indent=2, ensure_ascii=False))

# Also analyze SMALL_V15 for comparison
print("\n\n" + "="*60)
print("ANÁLISE RÁPIDA SMALL_V15 (para comparação)")
print("="*60)
t2 = load("data/instances/SMALL_V15.zip")
df2_func = t2["TbFuncionarios"]
df2_proj = t2["TbProjetos"]
df2_comp = t2["TbComposicao"]
df2_cat = t2["TbCategorias"]
Nf2 = len(df2_func)
Np2 = len(df2_proj)
seats2 = df2_proj["Max_Pessoas"].sum()
cat2 = df2_func["ID_Categ"].value_counts().sort_index()
tam2 = df2_proj["Tam_Proj"].value_counts()
print(f"Nf={Nf2}, Np={Np2}, seats={seats2}")
print(f"Np/Nf={Np2/Nf2:.4f}, seats/Nf={seats2/Nf2:.4f}")
print("Cat dist:")
for c, cnt in cat2.items():
    print(f"  Cat {c}: {cnt} ({cnt/Nf2*100:.1f}%)")
print("Tam dist:")
for tam in ["P","M","G"]:
    cnt = tam2.get(tam, 0)
    print(f"  {tam}: {cnt} ({cnt/Np2*100:.1f}%)")
print("Composição:")
print(df2_comp.to_string(index=False))
print("Categorias:")
print(df2_cat.to_string(index=False))

# BE data
df2_auto = t2.get("TbProjetos_Autoexclusao", pd.DataFrame())
df2_desc = t2.get("TbProjetos_Descompressao", pd.DataFrame())
df2_indep = t2.get("TbProjetos_Independencia", pd.DataFrame())
df2_indisp = t2.get("TbFuncionarios_Indisponiveis", pd.DataFrame())
print(f"\nAutoexclusão: {len(df2_auto)} pares")
print(f"Descompressão: {len(df2_desc)} pares")
print(f"Independência: {len(df2_indep)} pares")
print(f"Indisponibilidade: {len(df2_indisp)} registros")

# Alocação atual
df2_aloc = t2.get("TbProjetos_Alocacao", pd.DataFrame())
print(f"Alocação atual: {len(df2_aloc)} registros")
if not df2_aloc.empty:
    a2 = df2_aloc.groupby("ID_Func").size()
    print(f"  mean={a2.mean():.1f}, max={a2.max()}")

# Demand vs supply by cat
demand2 = {}
for _, row in df2_comp.iterrows():
    tam = row["Tam_Proj"]
    cat = row["Categoria"]
    ideal = row["Qt_Ideal"]
    n = tam2.get(tam, 0)
    demand2[cat] = demand2.get(cat, 0) + ideal * n

print("\nDemanda vs Oferta por cat (SMALL):")
for cat in sorted(demand2.keys()):
    s = cat2.get(cat, 0)
    d = demand2[cat]
    print(f"  Cat {cat}: supply={s}, demand={d}, deficit={s-d:+d}, ratio={s/d:.2f}" if d>0 else f"  Cat {cat}: supply={s}, demand=0")

# Skills
df2_skill = t2.get("TbFuncionarios_Skill", pd.DataFrame())
if not df2_skill.empty:
    sk2 = df2_skill.groupby("ID_Func").size()
    elig2 = df2_func[df2_func["ID_Categ"].isin([4,5,6])]["ID_Func"]
    upg2 = set(sk2[sk2>=3].index) & set(elig2)
    print(f"\nUpgrades: {len(upg2)} ({len(upg2)/Nf2*100:.1f}%)")

print("\n\nDONE.")

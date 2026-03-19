"""Quick analysis of SMALL_V15 structure."""
import zipfile, pandas as pd

def read_csv(zf, pattern, sep=";"):
    names = [n for n in zf.namelist() if pattern in n]
    if not names: return pd.DataFrame()
    with zf.open(names[0]) as f:
        df = pd.read_csv(f, sep=sep, dtype=str, keep_default_na=False)
    df.columns = [c.encode("utf-8").decode("utf-8-sig").strip() for c in df.columns]
    return df

with zipfile.ZipFile("data/instances/SMALL_V15.zip") as zf:
    print("Files:", zf.namelist())
    df_f = read_csv(zf, "TbFuncionarios.csv")
    df_p = read_csv(zf, "TbProjetos.csv")
    df_t = read_csv(zf, "TbFuncionarios_Treinamentos")
    df_s = read_csv(zf, "TbFuncionarios_Skill")
    df_i = read_csv(zf, "TbFuncionarios_Indisponiveis")
    df_a = read_csv(zf, "TbProjetos_Alocacao")
    df_au = read_csv(zf, "TbProjetos_Autoexclusao")
    df_de = read_csv(zf, "TbProjetos_Descompressao")
    df_in = read_csv(zf, "TbProjetos_Independencia")
    
    nf = len(df_f)
    np_ = len(df_p)
    print(f"Func: {nf}, Proj: {np_}, Ratio: {nf/np_:.2f}")
    cats = df_f["ID_Categ"].value_counts().sort_index()
    print(f"Cats: {dict(cats)}")
    tams = df_p["Tam_Proj"].value_counts()
    print(f"Tams: {dict(tams)}")
    df_p["Max_Pessoas"] = pd.to_numeric(df_p["Max_Pessoas"])
    seats = df_p["Max_Pessoas"].sum()
    print(f"Seats: {seats}, Ratio seats/func: {seats/nf:.2f}")
    print(f"Treinos func: {df_t['ID_Func'].nunique()}/{nf} ({df_t['ID_Func'].nunique()/nf*100:.0f}%)")
    print(f"Skills func: {df_s['ID_Func'].nunique()}/{nf}")
    print(f"Indisp: {len(df_i)} ({df_i['ID_Func'].nunique()} func)")
    print(f"Aloc hist: {len(df_a)} pares")
    print(f"Autoexc: {len(df_au)}, Descomp: {len(df_de)}, Indep: {len(df_in)}")
    print(f"\nTreinos sample:")
    print(df_t.head(5).to_string(index=False))
    print(f"\nFunc sample:")
    print(df_f.head(3).to_string(index=False))
    print(f"\nProj sample:")
    print(df_p.head(3).to_string(index=False))

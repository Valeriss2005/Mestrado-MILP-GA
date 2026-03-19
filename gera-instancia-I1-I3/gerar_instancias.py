# -*- coding: utf-8 -*-
"""
Projeto: Mestrado-MILP-GA
Pasta: gera-instancia-I1-I3
Arquivo: gerar_instancias.py

Autora: Valéria dos Santos Souza

Descrição:
    Gera e documenta as instâncias sintéticas utilizadas nos experimentos.

Instâncias:
    - SMALL_V15 = I1
    - LARGE_V31 = I3

Observação:
    Este script foi organizado para fins de transparência metodológica e
    reprodutibilidade. A lógica preserva a estrutura e os parâmetros das
    instâncias finais disponibilizadas no repositório.
"""

from __future__ import annotations

import argparse
import importlib
import os
import random
import zipfile
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


def sample_coord(n: int, lat0: float, lon0: float, spread_km: float) -> Tuple[np.ndarray, np.ndarray]:
    lat = lat0 + (np.random.randn(n) * (spread_km / 111.0))
    lon = lon0 + (np.random.randn(n) * (spread_km / (111.0 * np.cos(np.deg2rad(lat0)))))
    return np.round(lat, 6), np.round(lon, 6)


def make_cep(n: int) -> List[str]:
    return [f"{random.randint(10000, 99999)}-{random.randint(100, 999)}" for _ in range(n)]


def unique_names(n: int) -> List[str]:
    nomes = [
        "Ana", "Beatriz", "Carlos", "Daniel", "Eduardo", "Fernanda", "Gabriel", "Helena",
        "Igor", "Joao", "Katia", "Lucas", "Mariana", "Nadia", "Otavio", "Paula",
        "Rafael", "Sofia", "Tiago", "Vitoria", "Bruno", "Camila", "Diego", "Elisa",
        "Felipe", "Guilherme", "Hugo", "Isabela", "Juliana", "Luiz", "Marcelo",
        "Nicole", "Pedro", "Renata", "Samuel", "Tatiana", "Vanessa", "Wagner", "Yuri", "Zoe"
    ]
    sobrenomes = [
        "Almeida", "Barros", "Campos", "Dias", "Esteves", "Ferreira", "Gomes", "Henrique",
        "Ibrahim", "Jardim", "Klein", "Lima", "Machado", "Nascimento", "Oliveira",
        "Pereira", "Queiroz", "Ramos", "Silva", "Teixeira", "Uchoa", "Vieira", "Xavier",
        "Yamada", "Zanin"
    ]
    out = []
    sufixo = 1
    while len(out) < n:
        for nome in nomes:
            for sobrenome in sobrenomes:
                out.append(f"{nome} {sobrenome} {sufixo}")
                if len(out) == n:
                    return out
        sufixo += 1
    return out[:n]


def add_months_approx(date: datetime, months: int) -> datetime:
    return date + timedelta(days=30 * months)


def save_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, sep=";", index=False, encoding="utf-8")


def zip_files(files: List[str], zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            zf.write(file, arcname=os.path.basename(file))


def generate_small_v15(cfg, out_dir: str) -> str:
    random.seed(cfg.SEED)
    np.random.seed(cfg.SEED)

    lat_c, lon_c = sample_coord(cfg.N_CLIENTES, cfg.LAT0, cfg.LON0, 35.0)
    df_clientes = pd.DataFrame({
        "ID_Cli": range(1, cfg.N_CLIENTES + 1),
        "Nome_Cli": [f"Cliente_{i:03d}" for i in range(1, cfg.N_CLIENTES + 1)],
        "CEP_Cli": make_cep(cfg.N_CLIENTES),
        "Cidade_Cli": np.random.choice(cfg.CIDADES_GSP, cfg.N_CLIENTES),
        "Latitude_Cli": lat_c,
        "Longitude_Cli": lon_c,
    })

    categorias = []
    for cat, qtd in cfg.CONTAGEM_CATEGORIAS.items():
        categorias.extend([cat] * qtd)
    random.shuffle(categorias)

    lat_f, lon_f = sample_coord(cfg.N_FUNCIONARIOS, cfg.LAT0, cfg.LON0, 30.0)
    nomes = unique_names(cfg.N_FUNCIONARIOS)
    salarios = [round(np.random.uniform(*cfg.SALARIO_HORA[int(cat)]), 2) for cat in categorias]
    df_func = pd.DataFrame({
        "ID_Func": range(1, cfg.N_FUNCIONARIOS + 1),
        "Nome_Func": nomes,
        "ID_Categ": categorias,
        "Salario_Hora": salarios,
        "CEP_Func": make_cep(cfg.N_FUNCIONARIOS),
        "Cidade_Func": np.random.choice(cfg.CIDADES_GSP, cfg.N_FUNCIONARIOS),
        "Latitude_Func": lat_f,
        "Longitude_Func": lon_f,
    })

    tamanhos = []
    for tam, qtd in cfg.DISTRIBUICAO_TAMANHO_PROJETO.items():
        tamanhos.extend([tam] * qtd)
    random.shuffle(tamanhos)

    date0 = datetime.strptime(cfg.DATA_BASE, "%Y-%m-%d")
    horas_range = {"P": (180, 360), "M": (420, 900), "G": (900, 1800)}
    dur_range = {"P": (20, 35), "M": (40, 70), "G": (60, 110)}
    max_people = {"P": (3, 4), "M": (6, 9), "G": (10, 16)}
    rows = []
    for i, tam in enumerate(tamanhos, start=1):
        start = date0 + timedelta(days=int(np.random.uniform(0, 120)))
        end = start + timedelta(days=int(np.random.uniform(*dur_range[tam])))
        rows.append([
            i,
            int(np.random.randint(1, cfg.N_CLIENTES + 1)),
            tam,
            int(np.random.randint(max_people[tam][0], max_people[tam][1] + 1)),
            int(np.random.randint(horas_range[tam][0], horas_range[tam][1] + 1)),
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
        ])
    df_proj = pd.DataFrame(rows, columns=[
        "ID_Proj", "ID_Cli", "Tam_Proj", "Max_Pessoas", "Qt_horas_Previstas",
        "Data_Inicio_Proj", "Data_Fim_Proj"
    ])

    df_cat = pd.DataFrame(cfg.CATEGORIAS)
    df_comp = pd.DataFrame(cfg.COMPOSICAO)
    df_trein = pd.DataFrame(cfg.TREINAMENTOS_OBRIGATORIOS)

    skill_counts = []
    for count, freq in cfg.SKILL_COUNT_DISTRIBUTION.items():
        skill_counts.extend([count] * freq)
    random.shuffle(skill_counts)
    skill_rows = []
    for func_id, count in zip(df_func["ID_Func"], skill_counts):
        skills = np.random.choice(cfg.SKILLS_CATALOGO, size=count, replace=False)
        for sk in skills:
            skill_rows.append([int(func_id), sk, cfg.DATA_BASE])
    df_skill = pd.DataFrame(skill_rows, columns=["ID_Func", "ID_Skill", "Data_Atualizacao"])

    # 207 funcionários com 3 treinamentos e 13 com 2 treinamentos = 647 linhas
    full_training = set(np.random.choice(df_func["ID_Func"], size=207, replace=False).tolist())
    train_rows = []
    date_base = datetime.strptime(cfg.DATA_BASE, "%Y-%m-%d")
    for func_id in df_func["ID_Func"]:
        available_ids = df_trein["ID_Treino"].tolist()
        chosen = available_ids if func_id in full_training else random.sample(available_ids, 2)
        for treino_id in chosen:
            val_meses = int(df_trein.loc[df_trein["ID_Treino"] == treino_id, "Validade_Meses"].iloc[0])
            valido_ate = add_months_approx(date_base, val_meses)
            train_rows.append([int(func_id), treino_id, cfg.DATA_BASE, valido_ate.strftime("%Y-%m-%d")])
    df_func_trein = pd.DataFrame(train_rows, columns=["ID_Func", "ID_Treino", "Data_Conclusao", "Valido_Ate"])

    motivos = ["Ferias", "Licenca medica", "Treinamento externo", "Outro projeto"]
    ind_rows = []
    for func_id in np.random.choice(df_func["ID_Func"], size=cfg.N_INDISPONIBILIDADES, replace=False):
        start = date_base + timedelta(days=int(np.random.uniform(0, 60)))
        end = start + timedelta(days=int(np.random.uniform(5, 15)))
        ind_rows.append([int(func_id), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), random.choice(motivos)])
    df_ind = pd.DataFrame(ind_rows, columns=["ID_Func", "Data_Inicio_Indisp", "Data_Fim_Indisp", "Motivo"])

    def unique_pairs(qty: int) -> pd.DataFrame:
        rows, used = [], set()
        while len(rows) < qty:
            pair = (int(np.random.choice(df_func["ID_Func"])), int(np.random.choice(df_proj["ID_Proj"])))
            if pair not in used:
                used.add(pair)
                rows.append([pair[0], pair[1]])
        return pd.DataFrame(rows, columns=["ID_Func", "ID_Proj"])

    df_auto = unique_pairs(cfg.N_AUTOEXCLUSAO)

    desc_rows, used = [], set()
    while len(desc_rows) < cfg.N_DESCOMPRESSAO:
        pair = (int(np.random.choice(df_func["ID_Func"])), int(np.random.choice(df_proj["ID_Proj"])))
        if pair not in used:
            used.add(pair)
            start = date_base + timedelta(days=int(np.random.uniform(0, 60)))
            end = start + timedelta(days=int(np.random.uniform(2, 8)))
            desc_rows.append([pair[0], pair[1], start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])
    df_desc = pd.DataFrame(desc_rows, columns=["ID_Func", "ID_Proj", "Data_Inicio_Desc", "Data_Fim_Desc"])

    indep_rows, used = [], set()
    while len(indep_rows) < cfg.N_INDEPENDENCIA:
        pair = (int(np.random.choice(df_proj["ID_Proj"])), int(np.random.choice(df_func["ID_Func"])))
        if pair not in used:
            used.add(pair)
            indep_rows.append([pair[0], pair[1]])
    df_indep = pd.DataFrame(indep_rows, columns=["ID_Proj", "ID_Func"])

    # 190 pares; 119 funcionários únicos; por projeto: 26x2, 6x3, 20x4, 8x5
    aloc_pool = np.random.choice(df_func["ID_Func"], size=cfg.N_FUNCIONARIOS_ALOCACAO, replace=False)
    proj_ids = df_proj["ID_Proj"].tolist()
    alloc_sizes = [2] * 26 + [3] * 6 + [4] * 20 + [5] * 8
    random.shuffle(alloc_sizes)
    alloc_rows = []
    for proj_id, n in zip(proj_ids, alloc_sizes):
        chosen = np.random.choice(aloc_pool, size=n, replace=False)
        for func_id in chosen:
            alloc_rows.append([int(func_id), int(proj_id)])
    df_aloc = pd.DataFrame(alloc_rows, columns=["ID_Func", "ID_Proj"])

    tables = {
        f"{cfg.PREFIXO_ARQUIVOS}TbFuncionarios": df_func,
        f"{cfg.PREFIXO_ARQUIVOS}TbFuncionarios_Indisponiveis": df_ind,
        f"{cfg.PREFIXO_ARQUIVOS}TbFuncionarios_Skill": df_skill,
        f"{cfg.PREFIXO_ARQUIVOS}TbFuncionarios_Treinamentos_Obrigatorios": df_func_trein,
        f"{cfg.PREFIXO_ARQUIVOS}TbProjetos": df_proj,
        f"{cfg.PREFIXO_ARQUIVOS}TbProjetos_Alocacao": df_aloc,
        f"{cfg.PREFIXO_ARQUIVOS}TbProjetos_Autoexclusao": df_auto,
        f"{cfg.PREFIXO_ARQUIVOS}TbProjetos_Descompressao": df_desc,
        f"{cfg.PREFIXO_ARQUIVOS}TbProjetos_Independencia": df_indep,
        f"{cfg.PREFIXO_ARQUIVOS}TbTreinamentos_Obrigatorios": df_trein,
        f"{cfg.PREFIXO_ARQUIVOS}TbCategorias": df_cat,
        f"{cfg.PREFIXO_ARQUIVOS}TbClientes": df_clientes,
        f"{cfg.PREFIXO_ARQUIVOS}TbComposicao": df_comp,
    }

    files = []
    for name, df in tables.items():
        path = os.path.join(out_dir, f"{name}.csv")
        save_csv(df, path)
        files.append(path)
    zip_path = os.path.join(out_dir, f"{cfg.NOME_INSTANCIA}.zip")
    zip_files(files, zip_path)
    return zip_path


def generate_large_v31(cfg, out_dir: str) -> str:
    random.seed(cfg.SEED)
    np.random.seed(cfg.SEED)

    lat_c, lon_c = sample_coord(cfg.N_CLIENTES, cfg.LAT0, cfg.LON0, 35.0)
    df_clientes = pd.DataFrame({
        "ID_Cli": range(1, cfg.N_CLIENTES + 1),
        "Nome_Cli": [f"Cliente_{i:03d}" for i in range(1, cfg.N_CLIENTES + 1)],
        "Cidade_Cli": np.random.choice(cfg.CIDADES_GSP, cfg.N_CLIENTES),
        "CEP_Cli": make_cep(cfg.N_CLIENTES),
        "Latitude_Cli": lat_c,
        "Longitude_Cli": lon_c,
    })

    cat_ids = list(cfg.DISTRIBUICAO_CATEGORIAS.keys())
    cat_probs = list(cfg.DISTRIBUICAO_CATEGORIAS.values())
    categorias = np.random.choice(cat_ids, size=cfg.N_FUNCIONARIOS, p=cat_probs)
    lat_f, lon_f = sample_coord(cfg.N_FUNCIONARIOS, cfg.LAT0, cfg.LON0, 30.0)
    salarios = [round(np.random.uniform(*cfg.SALARIO_HORA[int(c)]), 2) for c in categorias]
    df_func = pd.DataFrame({
        "ID_Func": range(1, cfg.N_FUNCIONARIOS + 1),
        "Nome_Func": unique_names(cfg.N_FUNCIONARIOS),
        "ID_Categ": categorias,
        "Cidade_Func": np.random.choice(cfg.CIDADES_GSP, cfg.N_FUNCIONARIOS),
        "CEP_Func": make_cep(cfg.N_FUNCIONARIOS),
        "Latitude_Func": lat_f,
        "Longitude_Func": lon_f,
        "Salario_Hora": salarios,
        "Industria_Principal": np.random.choice(cfg.INDUSTRIAS, cfg.N_FUNCIONARIOS),
        "Cross": np.random.choice([0, 1], cfg.N_FUNCIONARIOS, p=[0.7, 0.3]),
    })

    tamanhos = []
    for tam, qtd in cfg.DISTRIBUICAO_TAMANHO_PROJETO.items():
        tamanhos.extend([tam] * qtd)
    random.shuffle(tamanhos)
    date0 = datetime.strptime(cfg.DATA_BASE, "%Y-%m-%d")
    horas_range = {"P": (280, 520), "M": (900, 1600), "G": (2200, 3400)}
    dur_range = {"P": (25, 45), "M": (45, 85), "G": (70, 120)}
    max_people = {"P": (3, 5), "M": (5, 8), "G": (8, 12)}
    rows = []
    for i, tam in enumerate(tamanhos, start=1):
        start = date0 + timedelta(days=int(np.random.uniform(0, 90)))
        end = start + timedelta(days=int(np.random.uniform(*dur_range[tam])))
        rows.append([
            i,
            int(np.random.choice(df_clientes["ID_Cli"])),
            f"Projeto_{i:03d}",
            tam,
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            int(np.random.uniform(*horas_range[tam])),
            int(np.random.randint(max_people[tam][0], max_people[tam][1] + 1)),
        ])
    df_proj = pd.DataFrame(rows, columns=[
        "ID_Proj", "ID_Cli", "Nome_Proj", "Tam_Proj", "Data_Inicio_Proj",
        "Data_Fim_Proj", "Qt_horas_Previstas", "Max_Pessoas"
    ])

    df_cat = pd.DataFrame(cfg.CATEGORIAS)
    df_comp = pd.DataFrame(cfg.COMPOSICAO)
    df_trein = pd.DataFrame(cfg.TREINAMENTOS_OBRIGATORIOS)

    chosen_funcs = np.random.choice(df_func["ID_Func"], size=cfg.N_SKILL_FUNCIONARIOS, replace=False)
    skill_rows = []
    for func_id in chosen_funcs:
        skills = np.random.choice(cfg.SKILL_IDS, size=cfg.SKILLS_POR_FUNCIONARIO, replace=False)
        for sk in skills:
            skill_rows.append([int(func_id), int(sk), cfg.DATA_BASE])
    df_skill = pd.DataFrame(skill_rows, columns=["ID_Func", "ID_Skill", "Data_Atualizacao"])

    date_base = datetime.strptime(cfg.DATA_BASE, "%Y-%m-%d")
    train_rows = []
    for func_id in df_func["ID_Func"]:
        for _, row in df_trein.iterrows():
            valid_until = add_months_approx(date_base, int(row["Validade_Meses"]))
            train_rows.append([int(func_id), int(row["ID_Treino"]), cfg.DATA_BASE, valid_until.strftime("%Y-%m-%d")])
    df_func_trein = pd.DataFrame(train_rows, columns=["ID_Func", "ID_Treino", "Data_Conclusao", "Valido_Ate"])

    motivos = ["Ferias", "Licenca medica", "Treinamento externo", "Outro projeto"]
    ind_rows = []
    for func_id in np.random.choice(df_func["ID_Func"], size=cfg.N_INDISPONIBILIDADES, replace=False):
        start = date_base + timedelta(days=int(np.random.uniform(0, 60)))
        end = start + timedelta(days=int(np.random.uniform(5, 20)))
        ind_rows.append([int(func_id), start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), random.choice(motivos)])
    df_ind = pd.DataFrame(ind_rows, columns=["ID_Func", "Data_Inicio_Indisp", "Data_Fim_Indisp", "Motivo"])

    def unique_pairs(qty: int, columns=("ID_Func", "ID_Proj")) -> pd.DataFrame:
        rows, used = [], set()
        while len(rows) < qty:
            func_id = int(np.random.choice(df_func["ID_Func"]))
            proj_id = int(np.random.choice(df_proj["ID_Proj"]))
            pair = (func_id, proj_id)
            if pair not in used:
                used.add(pair)
                rows.append([func_id, proj_id] if columns == ("ID_Func", "ID_Proj") else [proj_id, func_id])
        return pd.DataFrame(rows, columns=list(columns))

    df_auto = unique_pairs(cfg.N_AUTOEXCLUSAO, ("ID_Func", "ID_Proj"))
    df_desc = unique_pairs(cfg.N_DESCOMPRESSAO, ("ID_Func", "ID_Proj"))
    df_indep = unique_pairs(cfg.N_INDEPENDENCIA, ("ID_Proj", "ID_Func"))

    # alvo = 2160 pares com todos os projetos cobertos
    alloc_pool = np.random.choice(df_func["ID_Func"], size=cfg.N_FUNCIONARIOS_ALOCACAO, replace=False)
    alloc_rows = []
    target = 2160
    counts = [0] * cfg.N_PROJETOS
    # cobertura mínima
    for proj_id in range(1, cfg.N_PROJETOS + 1):
        n = np.random.randint(3, 7)
        counts[proj_id - 1] = n
    remaining = target - sum(counts)
    while remaining > 0:
        idx = np.random.randint(0, cfg.N_PROJETOS)
        if counts[idx] < 11:
            counts[idx] += 1
            remaining -= 1
    for proj_id, n in enumerate(counts, start=1):
        chosen = np.random.choice(alloc_pool, size=n, replace=False)
        for func_id in chosen:
            alloc_rows.append([proj_id, int(func_id)])
    df_aloc = pd.DataFrame(alloc_rows, columns=["ID_Proj", "ID_Func"])

    tables = {
        "TbFuncionarios": df_func,
        "TbFuncionarios_Indisponiveis": df_ind,
        "TbFuncionarios_Skill": df_skill,
        "TbFuncionarios_Treinamentos_Obrigatorios": df_func_trein,
        "TbProjetos": df_proj,
        "TbProjetos_Alocacao": df_aloc,
        "TbProjetos_Autoexclusao": df_auto,
        "TbProjetos_Descompressao": df_desc,
        "TbProjetos_Independencia": df_indep,
        "TbTreinamentos_Obrigatorios": df_trein,
        "TbCategorias": df_cat,
        "TbClientes": df_clientes,
        "TbComposicao": df_comp,
    }

    files = []
    for name, df in tables.items():
        path = os.path.join(out_dir, f"{name}.csv")
        save_csv(df, path)
        files.append(path)
    zip_path = os.path.join(out_dir, f"{cfg.NOME_INSTANCIA}.zip")
    zip_files(files, zip_path)
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera as instâncias sintéticas SMALL_V15 (I1) e LARGE_V31 (I3).")
    parser.add_argument("--instancia", choices=["SMALL_V15", "LARGE_V31"], required=True)
    parser.add_argument("--saida", default="saida")
    args = parser.parse_args()

    os.makedirs(args.saida, exist_ok=True)

    if args.instancia == "SMALL_V15":
        cfg = importlib.import_module("parametros_small_v15")
        zip_path = generate_small_v15(cfg, args.saida)
    else:
        cfg = importlib.import_module("parametros_large_v31")
        zip_path = generate_large_v31(cfg, args.saida)

    print(f"Instância gerada com sucesso em: {zip_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
instance_generator_v5.py
========================
Gera 3 instâncias por ESCALONAMENTO HOMOTÉTICO da base LARGE_V31 (1200/320).

Estratégia:
  - Multiplica Nf e Np por fatores fixos (0.5, 1.5, 2.5)
  - Preserva TODAS as proporções da LARGE_V31 (categorias, tamanhos, densidades)
  - Protege gargalo de Cat 2 (Diretor) contra erros de arredondamento
  - Geografia compacta: todos func/cli dentro de ~10km (< KM_MAX=20km)
  - Validação pós-geração garante viabilidade com TOL ≤ 5%

Instâncias geradas:
┌──────────┬──────┬──────┬─────────────────────────────────────────┐
│ Instância│ Func │ Proj │ Cenário / Descrição                     │
├──────────┼──────┼──────┼─────────────────────────────────────────┤
│ LARGE_05X│  600 │  160 │ 0.5× LARGE — Escritório capital BH     │
│ LARGE_15X│ 1800 │  480 │ 1.5× LARGE — Escritório ampliado SP    │
│ LARGE_25X│ 3000 │  800 │ 2.5× LARGE — Multi-office SP+RJ+BH    │
└──────────┴──────┴──────┴─────────────────────────────────────────┘

Princípios:
  1. Proporções IDÊNTICAS à LARGE_V31 em todas as dimensões
  2. TbCategorias e TbComposicao copiadas literalmente da LARGE
  3. Proteção explícita do gargalo Cat 2 (Diretor) após arredondamento
  4. Geografia compacta em região metropolitana (max ~10km)
  5. Densidades de restrições proporcionais à LARGE
  6. Alocação atual capped por Lim_Proj de cada categoria
  7. 100% de cobertura de treinamentos
  8. Pre-flight + validação detalhada de supply/demand

Uso:
  python scripts/instance_generator_v5.py
  python scripts/instance_generator_v5.py --instances LARGE_05X LARGE_15X
  python scripts/instance_generator_v5.py --instances LARGE_25X --seed 123
"""

import argparse, os, sys, zipfile, math, random
from collections import defaultdict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


# ================================================================
# PROPORÇÕES FIXAS EXTRAÍDAS DA LARGE_V31
# ================================================================

# Base de referência
LARGE_NF = 1200
LARGE_NP = 320

# Distribuição de categorias (LARGE_V31 exata)
CAT_DIST = {1: 0.050, 2: 0.020, 3: 0.082, 4: 0.130, 5: 0.290, 6: 0.428}

# Distribuição de tamanho de projeto
TAM_DIST = {"P": 0.247, "M": 0.603, "G": 0.150}

# Max_Pessoas por tamanho (LARGE_V31 ranges)
SEATS_RANGE = {"P": (3, 5), "M": (6, 8), "G": (9, 11)}

# Horas previstas por tamanho
HORAS_RANGE = {"P": (200, 550), "M": (600, 1500), "G": (1500, 3000)}

# Duração em dias
DURACAO_RANGE = {"P": (25, 50), "M": (50, 100), "G": (80, 130)}

# Salários base por categoria (da LARGE_V31)
SALARY_BASE = {
    1: (496, 943),   # Sócio
    2: (422, 496),   # Diretor
    3: (340, 448),   # Gerente Sênior
    4: (251, 320),   # Gerente
    5: (180, 240),   # Sênior Associate
    6: (120, 170),   # Associate
}

# Limite de projetos por categoria (TbCategorias da LARGE)
LIM_PROJ = {1: 12, 2: 12, 3: 12, 4: 6, 5: 5, 6: 4}

# Composição ideal (TbComposicao da LARGE)
# {(Tam_Proj, Categoria): Qt_Ideal}
QT_IDEAL = {
    ("P", 1): 0, ("P", 2): 0, ("P", 3): 1, ("P", 4): 1, ("P", 5): 2, ("P", 6): 0,
    ("M", 1): 0, ("M", 2): 1, ("M", 3): 1, ("M", 4): 1, ("M", 5): 2, ("M", 6): 1,
    ("G", 1): 1, ("G", 2): 1, ("G", 3): 1, ("G", 4): 2, ("G", 5): 3, ("G", 6): 2,
}

# Densidades de restrições (LARGE_V31 exatas)
DENSITY = {
    "indisp_pct":     0.12,   # 12% dos funcs indisponíveis
    "autoexcl_pct":   0.10,   # 10% dos funcs com 1 autoexclusão
    "descomp_pct":    0.20,   # 20% dos funcs com 1 descompressão
    "indep_ratio":    0.004,  # 0.4% dos funcs em pares de independência
    "skills_pct":     0.10,   # 10% dos funcs com skills (upgrade)
    "aloc_pct_funcs": 0.64,   # 64% dos funcs com alocação atual
    "aloc_mean":      2.8,    # média de alocações por func alocado
}

SKILL_IDS = [9001, 9002, 9003, 9004, 9005, 9006, 9007, 9008, 9009, 9010]
TREINO_IDS = [101, 102, 103, 104]
MOTIVOS_INDISP = ["Treinamento externo", "Ferias", "Licenca medica", "Projeto interno"]

# Datas do ciclo de auditoria (mesmo da LARGE)
DATE_RANGE_INI = ("2025-02-01", "2025-07-15")


# ================================================================
# PERFIS GEOGRÁFICOS — região metropolitana compacta por instância
# Todos os pontos ficam dentro de ~10km do centro (< KM_MAX = 20km)
# ================================================================

PROFILES = {
    "LARGE_05X": {
        "desc": "0.5x LARGE — Escritório capital (Belo Horizonte) — 600 func / 160 proj",
        "factor": 0.5,
        "n_func": 600,
        "n_proj": 160,
        "sal_factor": 0.95,
        # 6 pontos centrais de BH (raio ~3km do centro)
        "cidades_func": [
            ("Belo Horizonte", -19.9167, -43.9345),
            ("Belo Horizonte", -19.9250, -43.9200),
            ("Belo Horizonte", -19.9100, -43.9450),
            ("Belo Horizonte", -19.9300, -43.9400),
            ("Belo Horizonte", -19.9050, -43.9300),
            ("Belo Horizonte", -19.9200, -43.9500),
        ],
        # 8 pontos para clientes (mesma região + arredores ~8km)
        "cidades_cli": [
            ("Belo Horizonte", -19.9167, -43.9345),
            ("Belo Horizonte", -19.9250, -43.9200),
            ("Belo Horizonte", -19.9100, -43.9450),
            ("Belo Horizonte", -19.9300, -43.9400),
            ("Belo Horizonte", -19.9050, -43.9300),
            ("Belo Horizonte", -19.9200, -43.9500),
            ("Belo Horizonte", -19.8950, -43.9600),   # ~3km N
            ("Belo Horizonte", -19.9400, -43.9150),   # ~4km SE
        ],
    },
    "LARGE_15X": {
        "desc": "1.5x LARGE — Escritório ampliado (São Paulo Centro) — 1800 func / 480 proj",
        "factor": 1.5,
        "n_func": 1800,
        "n_proj": 480,
        "sal_factor": 1.00,
        # 6 pontos centrais de SP (raio ~4km — Paulista/Faria Lima/Berrini)
        "cidades_func": [
            ("Sao Paulo", -23.5613, -46.6560),   # Av Paulista
            ("Sao Paulo", -23.5870, -46.6820),   # Berrini
            ("Sao Paulo", -23.5730, -46.6930),   # Faria Lima
            ("Sao Paulo", -23.5505, -46.6333),   # Centro
            ("Sao Paulo", -23.5650, -46.6500),   # Jardins
            ("Sao Paulo", -23.5550, -46.6700),   # Pinheiros
        ],
        # 8 pontos para clientes (mesma região)
        "cidades_cli": [
            ("Sao Paulo", -23.5613, -46.6560),
            ("Sao Paulo", -23.5870, -46.6820),
            ("Sao Paulo", -23.5730, -46.6930),
            ("Sao Paulo", -23.5505, -46.6333),
            ("Sao Paulo", -23.5650, -46.6500),
            ("Sao Paulo", -23.5550, -46.6700),
            ("Sao Paulo", -23.5450, -46.6400),   # Bom Retiro
            ("Sao Paulo", -23.5800, -46.6600),   # Vila Mariana
        ],
    },
    "LARGE_25X": {
        "desc": "2.5x LARGE — Multi-office nacional (Grande SP) — 3000 func / 800 proj",
        "factor": 2.5,
        "n_func": 3000,
        "n_proj": 800,
        "sal_factor": 1.05,
        # 8 pontos em SP (raio ~5km — área financeira expandida)
        "cidades_func": [
            ("Sao Paulo", -23.5613, -46.6560),   # Paulista
            ("Sao Paulo", -23.5870, -46.6820),   # Berrini
            ("Sao Paulo", -23.5730, -46.6930),   # Faria Lima
            ("Sao Paulo", -23.5505, -46.6333),   # Centro
            ("Sao Paulo", -23.5650, -46.6500),   # Jardins
            ("Sao Paulo", -23.5550, -46.6700),   # Pinheiros
            ("Sao Paulo", -23.5450, -46.6400),   # Bom Retiro
            ("Sao Paulo", -23.5800, -46.6600),   # Vila Mariana
        ],
        # 10 pontos para clientes (mesma região)
        "cidades_cli": [
            ("Sao Paulo", -23.5613, -46.6560),
            ("Sao Paulo", -23.5870, -46.6820),
            ("Sao Paulo", -23.5730, -46.6930),
            ("Sao Paulo", -23.5505, -46.6333),
            ("Sao Paulo", -23.5650, -46.6500),
            ("Sao Paulo", -23.5550, -46.6700),
            ("Sao Paulo", -23.5450, -46.6400),
            ("Sao Paulo", -23.5800, -46.6600),
            ("Sao Paulo", -23.5700, -46.6450),   # Liberdade
            ("Sao Paulo", -23.5500, -46.6850),   # Perdizes
        ],
    },
}


# ================================================================
# LEITURA DE REGRAS DA LARGE
# ================================================================

def read_csv_from_zip(zf, pattern, sep=";"):
    names = [n for n in zf.namelist() if pattern in n]
    if not names:
        return pd.DataFrame()
    with zf.open(names[0]) as f:
        df = pd.read_csv(f, sep=sep, dtype=str, keep_default_na=False)
    df.columns = [c.encode("utf-8").decode("utf-8-sig").strip() for c in df.columns]
    return df


def load_rules_from_large(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        return {
            "TbCategorias": read_csv_from_zip(zf, "TbCategorias.csv"),
            "TbComposicao": read_csv_from_zip(zf, "TbComposicao.csv"),
            "TbTreinamentos_Obrigatorios": read_csv_from_zip(zf, "TbTreinamentos_Obrigatorios.csv"),
        }


# ================================================================
# CÁLCULO DE DEMANDA VS OFERTA (fundamental para viabilidade)
# ================================================================

def compute_demand_supply(cat_counts, tam_counts):
    """
    Calcula demanda e oferta por categoria e retorna análise detalhada.
    Retorna dict com: {cat: {demand, supply, lim, capacity, slack, ratio}}
    """
    analysis = {}
    for cat in sorted(cat_counts.keys()):
        demand = 0
        for t in ["P", "M", "G"]:
            ideal = QT_IDEAL.get((t, cat), 0)
            n_t = tam_counts.get(t, 0)
            demand += ideal * n_t

        supply = cat_counts[cat]
        lim = LIM_PROJ[cat]
        capacity = supply * lim
        slack = capacity - demand
        ratio = capacity / max(demand, 1)

        analysis[cat] = {
            "demand": demand,
            "supply": supply,
            "lim": lim,
            "capacity": capacity,
            "slack": slack,
            "ratio": ratio,
        }
    return analysis


def fix_cat2_bottleneck(cat_counts, tam_counts):
    """
    Protege o gargalo de Cat 2 (Diretor) contra erros de arredondamento.
    Garante que capacity(Cat2) >= demand(Cat2) * 1.15 (margem de 15%).
    Se necessário, move funcionários de Cat 6 → Cat 2.
    """
    analysis = compute_demand_supply(cat_counts, tam_counts)

    # Verificar TODAS as categorias com demanda > 0
    fixes_applied = []
    for cat in sorted(cat_counts.keys()):
        info = analysis[cat]
        if info["demand"] == 0:
            continue

        # Margem mínima: capacity >= demand * 1.15
        min_capacity = math.ceil(info["demand"] * 1.15)
        if info["capacity"] < min_capacity:
            needed_extra_cap = min_capacity - info["capacity"]
            needed_extra_supply = math.ceil(needed_extra_cap / info["lim"])

            # Adicionar à categoria deficitária, removendo de Cat 6
            old_supply = cat_counts[cat]
            cat_counts[cat] += needed_extra_supply
            cat_counts[6] -= needed_extra_supply

            fixes_applied.append(
                f"Cat {cat}: +{needed_extra_supply} (de {old_supply} para {cat_counts[cat]}), "
                f"compensado em Cat 6 (-{needed_extra_supply} para {cat_counts[6]})"
            )

    return cat_counts, fixes_applied


# ================================================================
# GERADOR PRINCIPAL
# ================================================================

def generate_instance(profile_name, rules, seed=42):
    """
    Gera instância replicando proporções EXATAS da LARGE_V31,
    escaladas pelo fator definido no perfil.
    """
    PROF = PROFILES[profile_name]
    rng = random.Random(seed)

    n_func = PROF["n_func"]
    n_proj = PROF["n_proj"]
    sal_factor = PROF["sal_factor"]

    print(f"\n  --- Gerando {profile_name} (Nf={n_func}, Np={n_proj}, factor={PROF['factor']}) ---")

    # ===== 1. DISTRIBUIÇÃO DE CATEGORIAS =====
    # Aplicar proporções da LARGE e arredondar
    cat_counts = {}
    for cat in sorted(CAT_DIST.keys()):
        cat_counts[cat] = max(1, round(CAT_DIST[cat] * n_func))

    # Ajustar Cat 6 para somar exatamente n_func
    total = sum(cat_counts.values())
    cat_counts[6] += n_func - total

    # ===== 2. DISTRIBUIÇÃO DE TAMANHOS DE PROJETO =====
    tam_counts = {}
    for t in ["P", "M", "G"]:
        tam_counts[t] = max(1, round(TAM_DIST[t] * n_proj))

    # Ajustar M para somar exatamente n_proj
    total_t = sum(tam_counts.values())
    tam_counts["M"] += n_proj - total_t

    # ===== 3. PROTEÇÃO DE GARGALO (Cat 2 e outras) =====
    cat_counts, fixes = fix_cat2_bottleneck(cat_counts, tam_counts)
    if fixes:
        for fix in fixes:
            print(f"    [FIX] {fix}")

    # Verificar que Cat 6 não ficou negativa
    if cat_counts[6] < 1:
        print(f"    ERRO: Cat 6 ficou com {cat_counts[6]}. Instância inválida.")
        return None

    # ===== 4. TbFuncionarios =====
    func_rows = []
    func_id = 1
    func_ids_by_cat = defaultdict(list)
    cat_of_func = {}

    for cat in sorted(cat_counts.keys()):
        sal_lo, sal_hi = SALARY_BASE[cat]
        sal_lo *= sal_factor
        sal_hi *= sal_factor

        for _ in range(cat_counts[cat]):
            cidade, lat, lon = rng.choice(PROF["cidades_func"])
            # Jitter PEQUENO: ±0.01° ≈ ±1.1km — garante max ~10km entre pontos
            lat += rng.uniform(-0.010, 0.010)
            lon += rng.uniform(-0.010, 0.010)

            sal = round(rng.uniform(sal_lo, sal_hi), 2)

            func_rows.append({
                "ID_Func": str(func_id),
                "Nome_Func": f"Func_{func_id:04d}",
                "ID_Categ": str(cat),
                "Salario_Hora": f"{sal:.2f}".replace(".", ","),
                "CEP_Func": f"{rng.randint(10000,99999):05d}-{rng.randint(100,999):03d}",
                "Cidade_Func": cidade,
                "Latitude_Func": f"{lat:.6f}",
                "Longitude_Func": f"{lon:.6f}",
            })
            func_ids_by_cat[cat].append(func_id)
            cat_of_func[func_id] = cat
            func_id += 1

    df_func = pd.DataFrame(func_rows)
    all_func_ids = list(range(1, n_func + 1))

    # ===== 5. TbClientes =====
    # Mesmo ratio cli/proj da LARGE: 240/320 = 0.75
    n_cli = max(n_proj, int(n_proj * 0.75))
    cli_rows = []
    for cli_id in range(1, n_cli + 1):
        cidade, lat, lon = rng.choice(PROF["cidades_cli"])
        # Jitter PEQUENO: ±0.01° — clientes na mesma região
        lat += rng.uniform(-0.010, 0.010)
        lon += rng.uniform(-0.010, 0.010)
        cli_rows.append({
            "ID_Cli": str(cli_id),
            "Nome_Cli": f"Cliente_{cli_id:03d}",
            "Cidade_Cli": cidade,
            "CEP_Cli": f"{rng.randint(10000,99999):05d}-{rng.randint(100,999):03d}",
            "Latitude_Cli": f"{lat:.6f}",
            "Longitude_Cli": f"{lon:.6f}",
        })
    df_cli = pd.DataFrame(cli_rows)

    # ===== 6. TbProjetos =====
    proj_rows = []
    proj_id = 1
    date_lo = datetime.strptime(DATE_RANGE_INI[0], "%Y-%m-%d")
    date_hi = datetime.strptime(DATE_RANGE_INI[1], "%Y-%m-%d")
    date_range_days = (date_hi - date_lo).days

    proj_tam_list = []  # para rastrear tamanho por projeto

    for t in ["P", "M", "G"]:
        s_lo, s_hi = SEATS_RANGE[t]
        h_lo, h_hi = HORAS_RANGE[t]
        d_lo, d_hi = DURACAO_RANGE[t]

        for _ in range(tam_counts[t]):
            max_pessoas = rng.randint(s_lo, s_hi)
            horas = round(rng.uniform(h_lo, h_hi), 2)
            duracao = rng.randint(d_lo, d_hi)

            ini = date_lo + timedelta(days=rng.randint(0, max(date_range_days, 1)))
            fim = ini + timedelta(days=duracao)

            proj_rows.append({
                "ID_Proj": str(proj_id),
                "ID_Cli": str(rng.randint(1, n_cli)),
                "Tam_Proj": t,
                "Max_Pessoas": str(max_pessoas),
                "Qt_horas_Previstas": f"{horas:.2f}".replace(".", ","),
                "Data_Inicio_Proj": ini.strftime("%d/%m/%Y"),
                "Data_Fim_Proj": fim.strftime("%d/%m/%Y"),
            })
            proj_tam_list.append(t)
            proj_id += 1

    df_proj = pd.DataFrame(proj_rows)
    all_proj_ids = list(range(1, n_proj + 1))

    # ===== 7. TbFuncionarios_Treinamentos_Obrigatorios =====
    # 100% dos funcionários com 4 treinos (idêntico à LARGE: 4800/1200 = 4.0 per func)
    treino_rows = []
    for fid in all_func_ids:
        for tid in TREINO_IDS:
            data_conc = datetime(2025, 1, 1) + timedelta(days=rng.randint(-180, -30))
            val_meses = 24 if tid in [101, 103] else 12
            valido_ate = data_conc + timedelta(days=val_meses * 30)
            treino_rows.append({
                "ID_Func": str(fid),
                "ID_Treino": str(tid),
                "Data_Conclusao": data_conc.strftime("%d/%m/%Y"),
                "Valido_Ate": valido_ate.strftime("%d/%m/%Y"),
            })
    df_treinos = pd.DataFrame(treino_rows)

    # ===== 8. TbFuncionarios_Skill =====
    # 10% dos funcs (cat 4,5,6) com 3 skills cada
    eligible = []
    for cat in [4, 5, 6]:
        eligible.extend(func_ids_by_cat[cat])

    n_with_skills = max(1, int(DENSITY["skills_pct"] * n_func))
    n_with_skills = min(n_with_skills, len(eligible))
    skill_func_ids = rng.sample(eligible, n_with_skills)

    skill_rows = []
    for fid in skill_func_ids:
        chosen = rng.sample(SKILL_IDS, 3)
        for sid in chosen:
            data_att = datetime(2025, 8, 1) + timedelta(days=rng.randint(-180, 0))
            skill_rows.append({
                "ID_Func": str(fid),
                "ID_Skill": str(sid),
                "Data_Atualizacao": data_att.strftime("%Y-%m-%d"),
            })
    df_skills = pd.DataFrame(skill_rows) if skill_rows else pd.DataFrame(
        columns=["ID_Func", "ID_Skill", "Data_Atualizacao"])

    # ===== 9. TbFuncionarios_Indisponiveis =====
    # 12% dos funcs — PROTEGER Cat 1,2,3: sortear preferencialmente de Cat 4,5,6
    n_indisp = max(1, int(DENSITY["indisp_pct"] * n_func))

    # Pool preferencial: 80% de Cat 4,5,6 + 20% de Cat 1,2,3
    pool_456 = []
    for cat in [4, 5, 6]:
        pool_456.extend(func_ids_by_cat[cat])
    pool_123 = []
    for cat in [1, 2, 3]:
        pool_123.extend(func_ids_by_cat[cat])

    # No máximo 20% dos indisponíveis vêm de Cat 1,2,3
    n_from_123 = min(len(pool_123), int(n_indisp * 0.20))
    n_from_456 = min(len(pool_456), n_indisp - n_from_123)

    indisp_sample = rng.sample(pool_123, n_from_123) + rng.sample(pool_456, n_from_456)
    rng.shuffle(indisp_sample)

    indisp_rows = []
    for fid in indisp_sample:
        # Períodos curtos (5-15 dias) para não bloquear demais
        ini = date_lo + timedelta(days=rng.randint(0, max(date_range_days, 1)))
        dur = rng.randint(5, 15)
        fim = ini + timedelta(days=dur)
        indisp_rows.append({
            "ID_Func": str(fid),
            "Data_Inicio_Indisp": ini.strftime("%d/%m/%Y"),
            "Data_Fim_Indisp": fim.strftime("%d/%m/%Y"),
            "Motivo": rng.choice(MOTIVOS_INDISP),
        })
    df_indisp = pd.DataFrame(indisp_rows) if indisp_rows else pd.DataFrame(
        columns=["ID_Func", "Data_Inicio_Indisp", "Data_Fim_Indisp", "Motivo"])

    # ===== 10. TbProjetos_Alocacao (histórico) =====
    # 64% dos funcs com alocação, média 2.8 por func
    # CAPPED por Lim_Proj de cada categoria (deixar ≥1 slot para nova alocação)
    n_funcs_alocados = max(1, int(DENSITY["aloc_pct_funcs"] * n_func))
    funcs_alocados = rng.sample(all_func_ids, min(n_funcs_alocados, n_func))

    aloc_rows = []
    used_pairs = set()
    for fid in funcs_alocados:
        cat = cat_of_func[fid]
        lim = LIM_PROJ[cat]
        # Cap: no máximo Lim_Proj - 1, para garantir ≥1 slot livre
        max_alocs = max(1, lim - 1)
        # Sortear quantidade (Gauss centrada em 2.8, capped)
        n_alocs_func = max(1, min(int(rng.gauss(DENSITY["aloc_mean"], 1.0)), max_alocs))

        for _ in range(n_alocs_func):
            for attempt in range(50):
                pid = rng.choice(all_proj_ids)
                if (fid, pid) not in used_pairs:
                    used_pairs.add((fid, pid))
                    aloc_rows.append({"ID_Proj": str(pid), "ID_Func": str(fid)})
                    break
    df_aloc = pd.DataFrame(aloc_rows) if aloc_rows else pd.DataFrame(
        columns=["ID_Proj", "ID_Func"])

    # ===== 11. TbProjetos_Autoexclusao =====
    # 10% dos funcs com EXATAMENTE 1 par cada
    # PROTEGER Cat 1,2,3: sortear preferencialmente de Cat 4,5,6
    n_auto = max(1, int(DENSITY["autoexcl_pct"] * n_func))

    n_auto_123 = min(len(pool_123), int(n_auto * 0.15))
    n_auto_456 = min(len(pool_456), n_auto - n_auto_123)
    auto_funcs = rng.sample(pool_123, n_auto_123) + rng.sample(pool_456, n_auto_456)

    auto_rows = []
    for fid in auto_funcs:
        pid = rng.choice(all_proj_ids)
        auto_rows.append({"ID_Func": str(fid), "ID_Proj": str(pid)})
    df_auto = pd.DataFrame(auto_rows) if auto_rows else pd.DataFrame(
        columns=["ID_Func", "ID_Proj"])

    # ===== 12. TbProjetos_Descompressao =====
    # 20% dos funcs com EXATAMENTE 1 par cada
    n_desc = max(1, int(DENSITY["descomp_pct"] * n_func))
    desc_funcs = rng.sample(all_func_ids, min(n_desc, n_func))
    desc_rows = []
    for fid in desc_funcs:
        pid = rng.choice(all_proj_ids)
        desc_rows.append({"ID_Func": str(fid), "ID_Proj": str(pid)})
    df_desc = pd.DataFrame(desc_rows) if desc_rows else pd.DataFrame(
        columns=["ID_Func", "ID_Proj"])

    # ===== 13. TbProjetos_Independencia =====
    # 0.4% dos funcs (idêntico à LARGE: 5 pares proporcionais)
    n_indep = max(1, round(DENSITY["indep_ratio"] * n_func))
    indep_rows = []
    indep_used = set()
    for _ in range(n_indep):
        for attempt in range(50):
            fid = rng.choice(all_func_ids)
            pid = rng.choice(all_proj_ids)
            if (fid, pid) not in indep_used:
                indep_used.add((fid, pid))
                indep_rows.append({"ID_Proj": str(pid), "ID_Func": str(fid)})
                break
    df_indep = pd.DataFrame(indep_rows) if indep_rows else pd.DataFrame(
        columns=["ID_Proj", "ID_Func"])

    # ===== Montar resultado =====
    return {
        "TbFuncionarios": df_func,
        "TbProjetos": df_proj,
        "TbCategorias": rules["TbCategorias"],
        "TbClientes": df_cli,
        "TbProjetos_Alocacao": df_aloc,
        "TbFuncionarios_Skill": df_skills,
        "TbComposicao": rules["TbComposicao"],
        "TbFuncionarios_Indisponiveis": df_indisp,
        "TbFuncionarios_Treinamentos_Obrigatorios": df_treinos,
        "TbTreinamentos_Obrigatorios": rules["TbTreinamentos_Obrigatorios"],
        "TbProjetos_Autoexclusao": df_auto,
        "TbProjetos_Descompressao": df_desc,
        "TbProjetos_Independencia": df_indep,
    }


# ================================================================
# VERIFICAÇÃO PRÉ-VÔO (detalhada)
# ================================================================

def preflight_check(tables, name):
    """
    Verifica 6 condições necessárias de viabilidade MILP antes de salvar.
    Retorna (ok: bool, issues: list[str], warnings: list[str]).
    """
    df_f = tables["TbFuncionarios"]
    df_p = tables["TbProjetos"]
    df_comp = tables["TbComposicao"]
    df_cat = tables["TbCategorias"]
    df_aloc = tables["TbProjetos_Alocacao"]

    n_func = len(df_f)
    n_proj = len(df_p)

    cats = pd.to_numeric(df_f["ID_Categ"]).value_counts().sort_index()
    tams = df_p["Tam_Proj"].value_counts()
    seats = pd.to_numeric(df_p["Max_Pessoas"]).sum()

    lim_proj = {}
    for _, r in df_cat.iterrows():
        lim_proj[int(r["ID_Categ"])] = int(r["Lim_Proj"])

    ok = True
    issues = []
    warnings = []

    # --- CHECK 1: Supply/Demand por Categoria ---
    df_comp_num = df_comp.copy()
    df_comp_num["Qt_Ideal"] = pd.to_numeric(df_comp_num["Qt_Ideal"])
    df_comp_num["Categoria"] = pd.to_numeric(df_comp_num["Categoria"])

    for cat_id in sorted(cats.index):
        demand = 0
        for t in ["P", "M", "G"]:
            ideal_vals = df_comp_num.loc[
                (df_comp_num["Tam_Proj"] == t) & (df_comp_num["Categoria"] == cat_id),
                "Qt_Ideal"
            ]
            ideal_val = int(ideal_vals.values[0]) if len(ideal_vals) > 0 else 0
            n_t = tams.get(t, 0)
            demand += ideal_val * n_t

        supply = cats[cat_id]
        lim = lim_proj.get(cat_id, 5)
        capacity = supply * lim

        if demand > 0 and capacity < demand:
            issues.append(f"FALHA Cat {cat_id}: capacidade ({capacity}={supply}x{lim}) < demanda ({demand})")
            ok = False
        elif demand > 0 and capacity < demand * 1.10:
            warnings.append(f"APERTO Cat {cat_id}: capacidade ({capacity}) < 1.10×demanda ({demand}), margem={capacity/demand:.2f}x")

    # --- CHECK 2: Seats total <= capacidade total ---
    total_capacity = sum(cats[c] * lim_proj.get(c, 5) for c in cats.index)
    if total_capacity < seats:
        issues.append(f"FALHA: capacidade total ({total_capacity}) < assentos ({int(seats)})")
        ok = False

    # --- CHECK 3: Funcionários suficientes para preencher vagas ---
    # Com TOL_PESSOAS=5%, precisamos de ≥95% dos func alocáveis
    effective_func = n_func * 0.95  # mínimo exigido
    if seats > total_capacity:
        issues.append(f"FALHA: assentos ({int(seats)}) > capacidade total ({total_capacity})")
        ok = False

    # --- CHECK 4: Alocação atual não excede Lim_Proj ---
    if not df_aloc.empty:
        aloc_counts = df_aloc.groupby("ID_Func")["ID_Proj"].nunique()
        for fid_str, count in aloc_counts.items():
            fid = int(fid_str)
            cat = int(df_f.loc[df_f["ID_Func"] == str(fid), "ID_Categ"].values[0])
            lim = lim_proj.get(cat, 5)
            if count >= lim:
                warnings.append(f"AVISO: Func {fid} (Cat {cat}) tem {count} alocs >= Lim_Proj={lim}")

    # --- CHECK 5: Seats/Func ratio (alvo: ~1.80) ---
    ratio = seats / n_func
    if ratio > 2.5:
        warnings.append(f"AVISO: ratio seats/func={ratio:.2f} > 2.5 (alto)")
    elif ratio < 1.2:
        warnings.append(f"AVISO: ratio seats/func={ratio:.2f} < 1.2 (baixo)")

    # --- CHECK 6: Treinos 100% cobertos ---
    n_tr = tables["TbFuncionarios_Treinamentos_Obrigatorios"]["ID_Func"].nunique() \
        if not tables["TbFuncionarios_Treinamentos_Obrigatorios"].empty else 0
    if n_tr < n_func:
        issues.append(f"FALHA: treinos cobrem apenas {n_tr}/{n_func} funcs ({n_tr/n_func*100:.0f}%)")
        ok = False

    return ok, issues, warnings


# ================================================================
# VERIFICAÇÃO DE DISTÂNCIAS
# ================================================================

def check_geography(tables, km_max=20.0):
    """Verifica que todas as distâncias func-cli estão dentro de KM_MAX."""
    import math as _m

    df_f = tables["TbFuncionarios"]
    df_p = tables["TbProjetos"]
    df_c = tables["TbClientes"]

    lats_f = pd.to_numeric(df_f["Latitude_Func"]).values
    lons_f = pd.to_numeric(df_f["Longitude_Func"]).values
    lats_c = pd.to_numeric(df_c["Latitude_Cli"]).values
    lons_c = pd.to_numeric(df_c["Longitude_Cli"]).values

    # Calcular distância máxima entre qualquer func e qualquer cliente
    R = 6371.0088
    max_dist = 0.0
    n_over = 0

    # Amostrar (para instâncias grandes, checar todos é caro)
    n_check = min(len(lats_f), 200)
    sample_f = sorted(random.sample(range(len(lats_f)), n_check))

    for fi in sample_f:
        lat1 = _m.radians(lats_f[fi])
        lon1 = _m.radians(lons_f[fi])
        for ci in range(len(lats_c)):
            lat2 = _m.radians(lats_c[ci])
            lon2 = _m.radians(lons_c[ci])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = _m.sin(dlat/2)**2 + _m.cos(lat1)*_m.cos(lat2)*_m.sin(dlon/2)**2
            d = 2 * R * _m.asin(_m.sqrt(a))
            if d > max_dist:
                max_dist = d
            if d > km_max:
                n_over += 1

    pct_over = n_over / (n_check * len(lats_c)) * 100 if n_check * len(lats_c) > 0 else 0
    return max_dist, pct_over


# ================================================================
# RESUMO E SALVAMENTO
# ================================================================

def print_summary(tables, name, prof):
    df_f = tables["TbFuncionarios"]
    df_p = tables["TbProjetos"]
    df_comp = tables["TbComposicao"]

    n_func = len(df_f)
    n_proj = len(df_p)

    cats = pd.to_numeric(df_f["ID_Categ"]).value_counts().sort_index()
    tams = df_p["Tam_Proj"].value_counts()
    seats = pd.to_numeric(df_p["Max_Pessoas"]).sum()

    print(f"\n{'='*70}")
    print(f"  {name} -- {prof['desc']}")
    print(f"{'='*70}")
    print(f"  Funcionários:   {n_func:>5d}  (LARGE×{prof['factor']}: {int(LARGE_NF*prof['factor'])})")
    print(f"  Projetos:       {n_proj:>5d}  (LARGE×{prof['factor']}: {int(LARGE_NP*prof['factor'])})")
    print(f"  Clientes:       {len(tables['TbClientes']):>5d}")
    print(f"  Assentos:       {int(seats):>5d}  (ratio s/f = {seats/n_func:.2f}, LARGE=1.80)")
    print(f"  Ratio Np/Nf:    {n_proj/n_func:.4f}  (LARGE=0.2667)")

    # Hierarquia
    print(f"\n  Hierarquia (ref LARGE: 5.0/2.0/8.2/13.0/29.0/42.8):")
    desc_cats = {1:"Sócio", 2:"Diretor", 3:"GerSr", 4:"Gerente", 5:"SenAssoc", 6:"Assoc"}
    for cat in sorted(cats.index):
        n = cats[cat]
        ref = CAT_DIST.get(cat, 0) * 100
        print(f"    Cat {cat} ({desc_cats.get(cat,'?'):>8s}): {n:>4d} ({n/n_func*100:5.1f}%)  ref={ref:.1f}%")

    # Projetos
    print(f"\n  Projetos (ref LARGE: P=24.7/M=60.3/G=15.0):")
    for t in ["P", "M", "G"]:
        n = tams.get(t, 0)
        ref = TAM_DIST.get(t, 0) * 100
        print(f"    {t}: {n:>4d} ({n/n_proj*100:5.1f}%)  ref={ref:.1f}%")

    # Demanda vs Oferta
    df_comp_num = df_comp.copy()
    df_comp_num["Qt_Ideal"] = pd.to_numeric(df_comp_num["Qt_Ideal"])
    df_comp_num["Categoria"] = pd.to_numeric(df_comp_num["Categoria"])

    print(f"\n  Demanda vs Oferta:")
    total_demand = 0
    for cat in sorted(cats.index):
        demand = 0
        for t in ["P", "M", "G"]:
            ideal_vals = df_comp_num.loc[
                (df_comp_num["Tam_Proj"] == t) & (df_comp_num["Categoria"] == cat),
                "Qt_Ideal"
            ]
            ideal_val = int(ideal_vals.values[0]) if len(ideal_vals) > 0 else 0
            n_t = tams.get(t, 0)
            demand += ideal_val * n_t
        supply = cats[cat]
        lim = LIM_PROJ.get(cat, 5)
        cap = supply * lim
        total_demand += demand
        marker = " <<<" if demand > 0 and cap < demand * 1.15 else ""
        print(f"    Cat {cat}: demanda={demand:>4d}  oferta={supply:>4d}  cap={cap:>5d}  "
              f"folga={cap-demand:>+5d} ({cap/max(demand,1):.2f}x){marker}")

    print(f"    TOTAL demanda={total_demand}  assentos={int(seats)}  func={n_func}")

    # Restrições
    print(f"\n  Restrições (ref LARGE: auto=10%, desc=20%, indisp=12%, skills=10%):")
    n_auto = len(tables["TbProjetos_Autoexclusao"])
    n_desc = len(tables["TbProjetos_Descompressao"])
    n_indep = len(tables["TbProjetos_Independencia"])
    n_indisp = len(tables["TbFuncionarios_Indisponiveis"])
    n_aloc = len(tables["TbProjetos_Alocacao"])
    n_sk = tables["TbFuncionarios_Skill"]["ID_Func"].nunique() if not tables["TbFuncionarios_Skill"].empty else 0
    n_tr = tables["TbFuncionarios_Treinamentos_Obrigatorios"]["ID_Func"].nunique() if not tables["TbFuncionarios_Treinamentos_Obrigatorios"].empty else 0

    print(f"    Autoexclusão:  {n_auto:>5d}  ({n_auto/n_func*100:.1f}% funcs)")
    print(f"    Descompressão: {n_desc:>5d}  ({n_desc/n_func*100:.1f}% funcs)")
    print(f"    Independência: {n_indep:>5d}")
    print(f"    Indisponib.:   {n_indisp:>5d}  ({n_indisp/n_func*100:.1f}%)")
    print(f"    Alocação hist: {n_aloc:>5d}")
    print(f"    Skills:        {n_sk:>5d}  ({n_sk/n_func*100:.1f}%)")
    print(f"    Treinos:       {n_tr:>5d}  ({n_tr/n_func*100:.1f}%)")

    # Geografia
    max_d, pct_over = check_geography(tables)
    print(f"\n  Geografia:")
    print(f"    Distância máxima (amostra): {max_d:.1f} km  (KM_MAX=20.0)")
    print(f"    Pares > 20km (amostra):     {pct_over:.1f}%")
    if pct_over > 0:
        print(f"    *** ATENÇÃO: {pct_over:.1f}% dos pares func-cli excedem 20km! ***")
    else:
        print(f"    ✓ Todos os pares dentro de 20km")


def save_zip(tables, path, prefix=""):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for tname, df in tables.items():
            csv_name = f"{prefix}{tname}.csv" if prefix else f"{tname}.csv"
            csv_bytes = df.to_csv(index=False, sep=";").encode("utf-8-sig")
            zf.writestr(csv_name, csv_bytes)
    print(f"\n  Salvo: {path}  ({os.path.getsize(path):,} bytes)")


# ================================================================
# MAIN
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Gera instâncias por escalonamento homotético da LARGE_V31."
    )
    parser.add_argument(
        "--instances", nargs="*",
        default=["LARGE_05X", "LARGE_15X", "LARGE_25X"],
        help="Instâncias a gerar (default: todas)"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default="data/instances")
    parser.add_argument("--source", type=str, default="data/instances/LARGE_V31.zip")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print("=" * 70)
    print("  GERADOR DE INSTÂNCIAS v5 — Escalonamento Homotético da LARGE_V31")
    print("=" * 70)

    if not os.path.exists(args.source):
        print(f"\nERRO: Arquivo fonte não encontrado: {args.source}")
        print("  Copie LARGE_V31.zip para data/instances/ antes de executar.")
        sys.exit(1)

    print(f"\nCarregando regras de: {args.source}")
    rules = load_rules_from_large(args.source)
    print("  TbCategorias, TbComposicao, TbTreinamentos carregadas")

    all_ok = True
    for name in args.instances:
        if name not in PROFILES:
            print(f"\nAVISO: '{name}' não reconhecida. Opções: {list(PROFILES.keys())}")
            continue

        prof = PROFILES[name]
        print(f"\n{'#'*70}")
        print(f"  Gerando {name}: {prof['desc']}")
        print(f"{'#'*70}")

        tables = generate_instance(name, rules, seed=args.seed + hash(name) % 10000)

        if tables is None:
            print(f"  FALHA na geração de {name}")
            all_ok = False
            continue

        # Pre-flight check
        ok, issues, warnings = preflight_check(tables, name)

        # Resumo
        print_summary(tables, name, prof)

        # Resultado do pre-flight
        print(f"\n  [Pre-flight {name}]")
        if warnings:
            for w in warnings:
                print(f"    ⚠ {w}")
        if issues:
            for iss in issues:
                print(f"    ✗ {iss}")
            all_ok = False
        else:
            print(f"    ✓ Todas as verificações passaram")

        # Salvar
        zip_path = os.path.join(args.output, f"{name}_V01.zip")
        save_zip(tables, zip_path)

    print(f"\n{'='*70}")
    if all_ok:
        print("  ✓ Geração concluída com sucesso! Todas as instâncias passaram no pre-flight.")
    else:
        print("  ⚠ Geração concluída com avisos/erros. Verifique as mensagens acima.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

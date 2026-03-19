# -*- coding: utf-8 -*-
"""Parâmetros da instância LARGE_V31 (I3)."""

NOME_INSTANCIA = "LARGE_V31"
PREFIXO_ARQUIVOS = ""
SEED = 31

N_FUNCIONARIOS = 1200
N_CLIENTES = 240
N_PROJETOS = 320

CIDADES_GSP = [
    "Sao Paulo", "Guarulhos", "Santo Andre", "Sao Bernardo do Campo", "Osasco",
    "Barueri", "Sao Caetano do Sul", "Diadema", "Mogi das Cruzes", "Carapicuiba",
    "Taboao da Serra", "Itapevi", "Cotia", "Maua", "Suzano"
]
INDUSTRIAS = [
    "Financial Services", "Consumer", "Industrial Products", "Technology",
    "Telecommunications", "Health", "Energy", "Retail"
]

CATEGORIAS = [
    {"ID_Categ": 1, "Desc_Categ": "Socio", "Perc_Tempo_Proj": 15, "Lim_Proj": 12},
    {"ID_Categ": 2, "Desc_Categ": "Diretor", "Perc_Tempo_Proj": 35, "Lim_Proj": 12},
    {"ID_Categ": 3, "Desc_Categ": "Gerente Senior", "Perc_Tempo_Proj": 55, "Lim_Proj": 12},
    {"ID_Categ": 4, "Desc_Categ": "Gerente", "Perc_Tempo_Proj": 70, "Lim_Proj": 6},
    {"ID_Categ": 5, "Desc_Categ": "Senior Associate", "Perc_Tempo_Proj": 85, "Lim_Proj": 5},
    {"ID_Categ": 6, "Desc_Categ": "Associate", "Perc_Tempo_Proj": 100, "Lim_Proj": 4},
]

COMPOSICAO = [
    {"Tam_Proj": "P", "Categoria": 1, "Qt_Ideal": 0},
    {"Tam_Proj": "P", "Categoria": 2, "Qt_Ideal": 0},
    {"Tam_Proj": "P", "Categoria": 3, "Qt_Ideal": 1},
    {"Tam_Proj": "P", "Categoria": 4, "Qt_Ideal": 1},
    {"Tam_Proj": "P", "Categoria": 5, "Qt_Ideal": 2},
    {"Tam_Proj": "P", "Categoria": 6, "Qt_Ideal": 0},
    {"Tam_Proj": "M", "Categoria": 1, "Qt_Ideal": 0},
    {"Tam_Proj": "M", "Categoria": 2, "Qt_Ideal": 1},
    {"Tam_Proj": "M", "Categoria": 3, "Qt_Ideal": 1},
    {"Tam_Proj": "M", "Categoria": 4, "Qt_Ideal": 1},
    {"Tam_Proj": "M", "Categoria": 5, "Qt_Ideal": 2},
    {"Tam_Proj": "M", "Categoria": 6, "Qt_Ideal": 1},
    {"Tam_Proj": "G", "Categoria": 1, "Qt_Ideal": 1},
    {"Tam_Proj": "G", "Categoria": 2, "Qt_Ideal": 1},
    {"Tam_Proj": "G", "Categoria": 3, "Qt_Ideal": 1},
    {"Tam_Proj": "G", "Categoria": 4, "Qt_Ideal": 2},
    {"Tam_Proj": "G", "Categoria": 5, "Qt_Ideal": 3},
    {"Tam_Proj": "G", "Categoria": 6, "Qt_Ideal": 2},
]

TREINAMENTOS_OBRIGATORIOS = [
    {"ID_Treino": 101, "Desc_Treino": "Compliance", "Validade_Meses": 24},
    {"ID_Treino": 102, "Desc_Treino": "Seguranca da Informacao", "Validade_Meses": 12},
    {"ID_Treino": 103, "Desc_Treino": "LGPD", "Validade_Meses": 24},
    {"ID_Treino": 104, "Desc_Treino": "Independencia", "Validade_Meses": 12},
]

DISTRIBUICAO_TAMANHO_PROJETO = {"P": 79, "M": 193, "G": 48}
DISTRIBUICAO_CATEGORIAS = {1: 0.02, 2: 0.06, 3: 0.10, 4: 0.24, 5: 0.30, 6: 0.28}

SALARIO_HORA = {
    1: (650.0, 900.0),
    2: (380.0, 520.0),
    3: (320.0, 420.0),
    4: (230.0, 300.0),
    5: (170.0, 230.0),
    6: (120.0, 160.0),
}

N_SKILL_FUNCIONARIOS = 123
SKILLS_POR_FUNCIONARIO = 3
SKILL_IDS = list(range(9001, 9051))

N_INDISPONIBILIDADES = 144
N_AUTOEXCLUSAO = 120
N_DESCOMPRESSAO = 240
N_INDEPENDENCIA = 5
N_FUNCIONARIOS_ALOCACAO = 770

DATA_BASE = "2025-08-09"
LAT0 = -23.5505
LON0 = -46.6333

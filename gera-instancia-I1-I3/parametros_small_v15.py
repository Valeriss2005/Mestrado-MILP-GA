# -*- coding: utf-8 -*-
"""Parâmetros da instância SMALL_V15 (I1)."""

NOME_INSTANCIA = "SMALL_V15"
PREFIXO_ARQUIVOS = "SMALL_"
SEED = 15

N_FUNCIONARIOS = 220
N_CLIENTES = 60
N_PROJETOS = 60

CIDADES_GSP = [
    "Sao Paulo", "Guarulhos", "Santo Andre", "Sao Bernardo do Campo", "Osasco",
    "Barueri", "Sao Caetano do Sul", "Diadema", "Mogi das Cruzes", "Carapicuiba",
    "Taboao da Serra", "Itapevi", "Cotia", "Maua", "Suzano"
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
    {"Tam_Proj": "P", "Categoria": 2, "Qt_Ideal": 1},
    {"Tam_Proj": "P", "Categoria": 3, "Qt_Ideal": 0},
    {"Tam_Proj": "P", "Categoria": 4, "Qt_Ideal": 2},
    {"Tam_Proj": "P", "Categoria": 5, "Qt_Ideal": 1},
    {"Tam_Proj": "P", "Categoria": 6, "Qt_Ideal": 0},
    {"Tam_Proj": "M", "Categoria": 1, "Qt_Ideal": 1},
    {"Tam_Proj": "M", "Categoria": 2, "Qt_Ideal": 1},
    {"Tam_Proj": "M", "Categoria": 3, "Qt_Ideal": 1},
    {"Tam_Proj": "M", "Categoria": 4, "Qt_Ideal": 3},
    {"Tam_Proj": "M", "Categoria": 5, "Qt_Ideal": 3},
    {"Tam_Proj": "M", "Categoria": 6, "Qt_Ideal": 1},
    {"Tam_Proj": "G", "Categoria": 1, "Qt_Ideal": 1},
    {"Tam_Proj": "G", "Categoria": 2, "Qt_Ideal": 1},
    {"Tam_Proj": "G", "Categoria": 3, "Qt_Ideal": 2},
    {"Tam_Proj": "G", "Categoria": 4, "Qt_Ideal": 5},
    {"Tam_Proj": "G", "Categoria": 5, "Qt_Ideal": 5},
    {"Tam_Proj": "G", "Categoria": 6, "Qt_Ideal": 2},
]

TREINAMENTOS_OBRIGATORIOS = [
    {"ID_Treino": 101, "Nome_Treino": "Independencia e Etica", "Validade_Meses": 36},
    {"ID_Treino": 102, "Nome_Treino": "Seguranca da Informacao", "Validade_Meses": 24},
    {"ID_Treino": 103, "Nome_Treino": "LGPD e Privacidade", "Validade_Meses": 24},
]

DISTRIBUICAO_TAMANHO_PROJETO = {"P": 26, "M": 19, "G": 15}
CONTAGEM_CATEGORIAS = {1: 4, 2: 11, 3: 40, 4: 77, 5: 55, 6: 33}

SALARIO_HORA = {
    1: (650.0, 900.0),
    2: (380.0, 520.0),
    3: (320.0, 420.0),
    4: (230.0, 300.0),
    5: (170.0, 230.0),
    6: (120.0, 160.0),
}

SKILLS_CATALOGO = [
    "IFRS", "USGAAP", "SOX", "Audit Analytics", "Internal Controls", "Compliance",
    "Risk Assessment", "Data Analysis", "Financial Reporting", "Tax", "Forensics",
    "IT Audit", "Cyber", "Valuation", "Treasury", "FP&A", "ESG", "Controllership"
]
SKILL_COUNT_DISTRIBUTION = {1: 43, 2: 66, 3: 78, 4: 16, 5: 13, 6: 4}

N_INDISPONIBILIDADES = 22
N_AUTOEXCLUSAO = 7
N_DESCOMPRESSAO = 11
N_INDEPENDENCIA = 5
ALOCACAO_POR_PROJETO = {2: 26, 3: 6, 4: 20, 5: 8}
N_FUNCIONARIOS_ALOCACAO = 119

DATA_BASE = "2025-08-09"
LAT0 = -23.5505
LON0 = -46.6333

# Mestrado-MILP-GA

![Status](https://img.shields.io/badge/status-em%20desenvolvimento-blue)
![Research](https://img.shields.io/badge/foco-disserta%C3%A7%C3%A3o%20de%20mestrado-6f42c1)
![Optimization](https://img.shields.io/badge/m%C3%A9todos-MILP%20%7C%20GA-success)
![Data](https://img.shields.io/badge/bases-sint%C3%A9ticas-orange)
![Reproducibility](https://img.shields.io/badge/reprodutibilidade-alta-brightgreen)

Repositório da dissertação de mestrado de **Valéria dos Santos Souza**, dedicada ao problema de **designação de profissionais em projetos de auditoria externa**, com comparação entre duas abordagens de otimização:

- **MILP** (*Mixed-Integer Linear Programming*)
- **GA** (*Genetic Algorithm*)

Este repositório reúne, em um único lugar:

- a documentação das **instâncias sintéticas** usadas no estudo;
- os scripts de **geração e escalonamento** das bases;
- os **modelos de otimização**;
- os **scripts de análise, métricas e consolidação de resultados**;
- e os **artefatos experimentais** associados à dissertação.

O objetivo deste README é mostrar **como tudo se relaciona**, **qual pasta usar em cada caso** e **qual sequência seguir**, dependendo do que você deseja fazer.

---

## Sumário

- [Visão geral](#visão-geral)
- [Quick Start](#quick-start)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Como as pastas se relacionam](#como-as-pastas-se-relacionam)
- [Por onde começar](#por-onde-começar)
- [Correspondência entre instâncias e dissertação](#correspondência-entre-instâncias-e-dissertação)
- [Fluxos de uso mais comuns](#fluxos-de-uso-mais-comuns)
- [Reprodutibilidade](#reprodutibilidade)
- [Autora](#autora)

---

## Visão geral

O projeto foi organizado em três blocos principais:

### `gera-instancia-I1-I3`
Pasta dedicada à geração e documentação das duas instâncias-base do estudo:

- `SMALL_V15` = **I1**
- `LARGE_V31` = **I3**

Aqui ficam os scripts, parâmetros e arquivos de apoio para compreender como essas duas bases sintéticas foram estruturadas.

---

### `gera-instancias-I2-I4-I5`
Pasta dedicada ao **escalonamento da base `LARGE_V31`**, gerando as demais instâncias do experimento.

É aqui que se reproduz a lógica de ampliação das instâncias intermediárias e maiores, derivadas da base large.

---

### `otimiza-milp-ga`
Pasta dedicada à **execução dos modelos**, à **análise dos resultados** e à **consolidação dos artefatos experimentais**.

É o ponto central para quem deseja:
- rodar o MILP;
- rodar o GA;
- usar as bases prontas;
- reproduzir resultados;
- gerar métricas, tabelas, comparações e gráficos;
- analisar as saídas experimentais da dissertação.

---

## Quick Start

### Quero apenas rodar os experimentos com as bases já prontas
Vá direto para:

```bash
otimiza-milp-ga
```

Esse é o melhor caminho para quem quer usar o projeto sem regenerar as bases.

Nessa pasta, o fluxo recomendado é:

1. executar os modelos;
2. gerar as métricas e análises com os scripts específicos.

---

### Quero gerar novamente as bases `SMALL_V15` e `LARGE_V31`
Vá para:

```bash
gera-instancia-I1-I3
```

---

### Quero escalar a `LARGE_V31` para gerar as outras instâncias
Vá para:

```bash
gera-instancias-I2-I4-I5
```

---

### Quero entender o projeto completo antes de executar qualquer coisa
Siga esta ordem:

1. leia este `README`;
2. abra `gera-instancia-I1-I3/README.md`;
3. abra `gera-instancias-I2-I4-I5/README.md`;
4. abra `otimiza-milp-ga/README.md`.

---

## Estrutura do repositório

```text
Mestrado-MILP-GA/
├── gera-instancia-I1-I3/
│   ├── README.md
│   ├── gerar_instancias.py
│   ├── parametros_small_v15.py
│   ├── parametros_large_v31.py
│   ├── data/
│   │   ├── SMALL_V15.zip
│   │   └── LARGE_V31.zip
│   └── docs/
│
├── gera-instancias-I2-I4-I5/
│   ├── README.md
│   ├── scripts/
│   │   └── instance_generator_v5.py
│   └── data/
│       └── instances/
│
└── otimiza-milp-ga/
    ├── README.md
    └── ...
```

---

## Como as pastas se relacionam

O fluxo lógico do repositório acompanha a lógica metodológica da pesquisa.

### Etapa 1 — Instâncias-base
A base do processo começa em:

```bash
gera-instancia-I1-I3
```

Aqui estão as duas instâncias-base documentadas no estudo:
- `SMALL_V15` (**I1**)
- `LARGE_V31` (**I3**)

---

### Etapa 2 — Escalonamento
Se o objetivo for reproduzir a expansão das instâncias, o próximo passo é:

```bash
gera-instancias-I2-I4-I5
```

Essa pasta usa a `LARGE_V31` como referência para gerar as instâncias escaladas.

---

### Etapa 3 — Otimização e análise
Depois, para executar os modelos, consolidar métricas e reproduzir os artefatos analíticos do experimento:

```bash
otimiza-milp-ga
```

Essa pasta concentra a parte computacional e analítica do estudo.

---

## Por onde começar

### Caso 1 — Quero usar as bases já disponíveis
Comece por:

```bash
otimiza-milp-ga
```

Você não precisa regenerar as instâncias antes.

---

### Caso 2 — Quero entender como as bases foram construídas
Comece por:

```bash
gera-instancia-I1-I3
```

Essa pasta documenta a geração de `SMALL_V15` e `LARGE_V31`.

---

### Caso 3 — Quero gerar as instâncias maiores do experimento
Siga esta ordem:

```bash
gera-instancia-I1-I3
gera-instancias-I2-I4-I5
```

Primeiro entenda ou gere a base `LARGE_V31`; depois faça o escalonamento.

---

### Caso 4 — Quero entender o pipeline completo da dissertação
A sequência recomendada é:

1. bases iniciais;
2. escalonamento;
3. otimização;
4. análises, métricas e consolidação dos resultados.

No repositório, isso corresponde a:

```bash
gera-instancia-I1-I3
gera-instancias-I2-I4-I5
otimiza-milp-ga
```

---

## Correspondência entre instâncias e dissertação

Para manter consistência com a nomenclatura adotada na dissertação:

- **I1** → `SMALL_V15`
- **I3** → `LARGE_V31`

As instâncias geradas por escalonamento a partir da `LARGE_V31` ficam concentradas na pasta `gera-instancias-I2-I4-I5`, correspondendo às demais instâncias do experimento.

---

## Fluxos de uso mais comuns

### Fluxo A — Reproduzir os experimentos
1. Use as bases já disponíveis no repositório.
2. Vá para `otimiza-milp-ga`.
3. Instale as dependências da pasta.
4. Execute os scripts dos modelos.
5. Gere as métricas, tabelas e análises com os scripts específicos da própria pasta.

---

### Fluxo B — Reproduzir a construção das bases
1. Vá para `gera-instancia-I1-I3`.
2. Gere ou inspecione `SMALL_V15` e `LARGE_V31`.
3. Vá para `gera-instancias-I2-I4-I5`.
4. Gere as instâncias escaladas a partir da base large.

---

### Fluxo C — Estudar apenas a metodologia
1. Leia a dissertação.
2. Leia este README.
3. Consulte os READMEs das pastas internas.
4. Veja primeiro as bases e depois os modelos e análises.

---

## Reprodutibilidade

Este repositório foi organizado para apoiar a **transparência metodológica** e a **reprodutibilidade** da pesquisa.

Por isso, ele inclui:

- bases sintéticas prontas;
- scripts que documentam a geração das instâncias-base;
- scripts que permitem escalar a instância large;
- códigos usados para executar os experimentos com MILP e GA;
- scripts para geração de métricas, tabelas, análises e gráficos.

Na prática:

- quem quiser **usar o projeto rapidamente** pode ir direto para `otimiza-milp-ga`;
- quem quiser **entender a construção dos dados** deve começar por `gera-instancia-I1-I3`;
- quem quiser **replicar o crescimento das instâncias** deve seguir para `gera-instancias-I2-I4-I5`.

---

## Autora

**Valéria dos Santos Souza**

Dissertação de mestrado em Computação Aplicada, com foco em otimização da designação de profissionais em auditoria externa, comparação entre abordagens exatas e meta-heurísticas e incorporação de variáveis de bem-estar ao problema de alocação.

---

# Otimização MILP-GA

Esta pasta reúne os códigos de otimização, análise e consolidação de resultados usados na dissertação para resolver o problema de designação de profissionais em projetos de auditoria externa por duas abordagens:

- **MILP** (*Mixed-Integer Linear Programming*)
- **GA** (*Genetic Algorithm*)

Além da execução dos modelos, esta pasta também concentra os scripts responsáveis por gerar **métricas, tabelas, consolidações e gráficos** utilizados na análise experimental da dissertação.

---

## Estrutura geral

```text
otimiza-milp-ga/
├── README.md
├── configs/
├── data/
│   ├── instances/
│   └── results/
├── models/
│   ├── ga_model.py
│   └── milp_model.py
├── scripts/
│   ├── analyze_experiment.py
│   ├── analyze_results.py
│   ├── analyze_multiseed.py
│   ├── analyze_large.py
│   └── analyze_small.py
└── ...
```

> A estrutura exata pode variar conforme a versão do projeto, mas a lógica permanece a mesma: **rodar os modelos primeiro** e **executar as análises depois**.

---

## O que esta pasta faz

Esta pasta permite:

- executar o **MILP** sobre uma instância sintética;
- executar o **GA** sobre uma instância sintética;
- salvar os resultados brutos do processamento;
- gerar métricas consolidadas do experimento;
- produzir tabelas, comparações e gráficos usados na dissertação.

---

## Antes de começar

Certifique-se de que:

1. as instâncias já foram geradas ou copiadas para a pasta de dados;
2. as dependências do projeto estão instaladas;
3. os caminhos dos arquivos estão corretos no seu ambiente.

As instâncias-base e os scripts de geração estão nas outras pastas do repositório:

- `gera-instancia-I1-I3`
- `gera-instancias-I2-I4-I5`

Se você **já tem as bases prontas**, pode começar diretamente por esta pasta.

---

## Fluxo recomendado

### 1. Coloque as instâncias na pasta de entrada
Use as bases sintéticas já disponíveis no repositório ou gere novas instâncias nas pastas apropriadas.

### 2. Execute os modelos
Rode o modelo desejado:

- **MILP**
- **GA**

Nesta etapa, o objetivo é gerar os resultados brutos do experimento.

### 3. Gere as análises e métricas
Com os resultados já produzidos, rode os scripts da pasta `scripts/` para gerar:

- métricas consolidadas;
- tabelas comparativas;
- análises por instância;
- comparações entre seeds;
- gráficos e artefatos analíticos.

---

## Execução dos modelos

### Rodar o MILP
Exemplo genérico:

```bash
python models/milp_model.py
```

### Rodar o GA
Exemplo genérico:

```bash
python models/ga_model.py
```

> Dependendo da organização atual da pasta, os arquivos podem estar em subdiretórios diferentes. Ajuste o caminho conforme necessário.

---

## Geração das análises e métricas

Após o processamento, utilize os scripts da pasta `scripts/` para gerar os artefatos analíticos.

### 1. Análise geral do experimento

```bash
python scripts/analyze_experiment.py --input data/results/experiment_metrics.csv
```

Esse script usa como entrada um arquivo de métricas do experimento e gera análises consolidadas.

---

### 2. Geração de tabelas e saídas analíticas

```bash
python scripts/analyze_results.py --input data/results/experiment_metrics.csv --output data/results/
```

Esse script permite gerar saídas consolidadas a partir do arquivo de métricas, com diretório de saída configurável.

---

### 3. Comparação multiseed

```bash
python scripts/analyze_multiseed.py --original data/results/experiment_metrics.csv --multiseed data/results/experiment_metrics_multiseed.csv --milp-nobe data/results/experiment_metrics_milp_noBE.csv
```

Esse script foi preparado para comparar:

- o arquivo original de métricas;
- o arquivo de métricas com múltiplas seeds;
- e o arquivo de métricas do MILP sem bem-estar.

---

### 4. Análises específicas por porte ou grupo

Se necessário, utilize também:

```bash
python scripts/analyze_large.py
python scripts/analyze_small.py
```

Esses scripts podem ser usados para análises específicas por conjunto de instâncias ou por recorte experimental.

---

## Onde os resultados são salvos

Os arquivos gerados pelos scripts de análise tendem a ser gravados em:

- `data/results/`
- `data/results/analysis/`
- ou em subpastas específicas de cada instância

Procure por arquivos como:

- `.csv`
- `.xlsx`
- `.png`
- `.pdf`

---

## Quando usar esta pasta

Use `otimiza-milp-ga` quando você quiser:

- rodar os modelos diretamente;
- reproduzir os experimentos;
- gerar os resultados brutos;
- calcular métricas;
- produzir tabelas e gráficos da dissertação.

---

## Relação com o restante do repositório

Esta pasta representa a etapa de **execução experimental e análise dos resultados**.

A relação com as demais pastas é:

- `gera-instancia-I1-I3` → gera e documenta as instâncias-base;
- `gera-instancias-I2-I4-I5` → escala a base `LARGE_V31`;
- `otimiza-milp-ga` → executa os modelos, consolida métricas e produz os artefatos analíticos do experimento.

---

## Sequência recomendada

Se você quer reproduzir o pipeline completo, siga esta ordem:

1. gerar ou obter as instâncias;
2. executar o MILP e/ou o GA;
3. executar os scripts de análise e métricas.

Se você já possui as bases prontas, comece diretamente pelo passo 2.

---

## Observação final

Este README concentra, em um único lugar, o fluxo principal da pasta de otimização:

- executar os modelos;
- salvar os resultados;
- gerar métricas, tabelas e gráficos depois.


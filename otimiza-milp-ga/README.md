# Otimização MILP-GA

Esta pasta reúne os códigos de otimização, consolidação de métricas e análise de resultados usados na dissertação para resolver o problema de designação de profissionais em projetos de auditoria externa.

As abordagens consideradas no projeto são:

- **MILP** (*Mixed-Integer Linear Programming*)
- **GA** (*Genetic Algorithm*)

Além dos modelos, esta pasta contém os scripts responsáveis por executar o experimento formal, complementar os cenários necessários e gerar os arquivos analíticos usados na dissertação.

---

## Estrutura geral

```text
otimiza-milp-ga/
├── README.md
├── requirements.txt
├── data/
│   ├── instances/
│   └── results/
├── models/
│   ├── ga_model.py
│   └── milp_model.py
└── scripts/
    ├── _calibrate_all.py
    ├── run_all.py
    ├── run_milp_noBE.py
    ├── run_multiseed.py
    ├── analyze_experiment.py
    └── ...
```

---

## O que esta pasta faz

Esta pasta permite:

- executar a calibração necessária do MILP;
- rodar o pipeline principal do experimento;
- completar o cenário de **MILP sem bem-estar**;
- executar rodadas **multiseed**;
- gerar métricas consolidadas;
- produzir análises finais a partir dos arquivos gerados.

---

## Antes de começar

Certifique-se de que:

1. as instâncias já estão disponíveis em `data/instances/`;
2. as dependências foram instaladas com `requirements.txt`;
3. os caminhos dos arquivos estão corretos no seu ambiente.

Se você ainda não gerou as bases, use antes as outras pastas do repositório principal:

- `gera-instancia-I1-I3`
- `gera-instancias-I2-I4-I5`

---

## Instalação do ambiente

### Windows

```bash
cd otimiza-milp-ga
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux / macOS

```bash
cd otimiza-milp-ga
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Sequência correta de execução

A reprodução do experimento deve seguir esta ordem:

### 1. Calibração
```bash
python scripts/_calibrate_all.py
```
Use este passo **apenas uma vez**, ou novamente **somente se novas bases tiverem sido geradas**.

---

### 2. Execução principal do experimento
```bash
python scripts/run_all.py
```
Este passo executa o pipeline principal e **atualiza**:

```text
data/results/experiment_metrics.csv
```

---

### 3. Execução complementar do MILP sem BE
```bash
python scripts/run_milp_noBE.py
```
Este passo **completa** o `run_all.py`, adicionando os resultados do cenário de **MILP sem bem-estar**.

---

### 4. Execução multiseed
```bash
python scripts/run_multiseed.py
```
Este passo **atualiza**:

```text
data/results/experiment_metrics_multiseed.csv
```

> Observação: esta etapa pode levar **até 3 dias**, dependendo da máquina utilizada.

---

### 5. Análise final do experimento
```bash
python scripts/analyze_experiment.py
```
Este passo consolida as análises finais a partir dos arquivos de métricas gerados nas etapas anteriores.

---

## Fluxo completo recomendado

```bash
python scripts/_calibrate_all.py
python scripts/run_all.py
python scripts/run_milp_noBE.py
python scripts/run_multiseed.py
python scripts/analyze_experiment.py
```

---

## O que cada etapa produz

### `python scripts/_calibrate_all.py`
Produz ou atualiza os resultados de calibração usados pelo MILP.

### `python scripts/run_all.py`
Produz ou atualiza:

```text
data/results/experiment_metrics.csv
```

### `python scripts/run_milp_noBE.py`
Complementa o conjunto principal de métricas com o cenário de MILP sem bem-estar.

### `python scripts/run_multiseed.py`
Produz ou atualiza:

```text
data/results/experiment_metrics_multiseed.csv
```

### `python scripts/analyze_experiment.py`
Gera a análise consolidada a partir dos arquivos de métricas produzidos anteriormente.

---

## Quando recalibrar

Você só precisa rodar novamente:

```bash
python scripts/_calibrate_all.py
```

quando:

- gerar novas instâncias;
- alterar as bases;
- ou modificar a lógica que afeta os parâmetros calibrados do MILP.

Se nada disso mudou, não é necessário recalibrar antes de cada execução.

---

## Onde os resultados são salvos

Os principais arquivos de saída ficam em:

```text
data/results/
```

Entre eles:

- `experiment_metrics.csv`
- `experiment_metrics_multiseed.csv`

Dependendo da etapa executada, outros arquivos analíticos também podem ser gerados nessa mesma estrutura.

---

## Execução manual dos modelos

Se necessário, você também pode rodar os modelos isoladamente.

### Rodar o MILP
```bash
python models/milp_model.py
```

### Rodar o GA
```bash
python models/ga_model.py
```

Use esse caminho quando quiser testar ou depurar um modelo específico fora do pipeline principal.

---

## Relação com o restante do repositório

Esta pasta representa a etapa de **execução experimental e análise dos resultados**.

A relação com as demais pastas é:

- `gera-instancia-I1-I3` → gera e documenta as instâncias-base;
- `gera-instancias-I2-I4-I5` → escala a base `LARGE_V31` para gerar as demais instâncias;
- `otimiza-milp-ga` → executa os modelos, consolida métricas e analisa os resultados.

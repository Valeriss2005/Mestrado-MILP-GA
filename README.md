# Mestrado-MILP-GA

![Status](https://img.shields.io/badge/status-concluído-brightgreen)
![Research](https://img.shields.io/badge/foco-dissertação%20de%20mestrado-6f42c1)
![Optimization](https://img.shields.io/badge/métodos-MILP%20%7C%20GA-success)
![Data](https://img.shields.io/badge/bases-sintéticas-orange)
![Reproducibility](https://img.shields.io/badge/reprodutibilidade-alta-brightgreen)

Repositório da dissertação de mestrado de **Valéria dos Santos Souza**, dedicada ao problema de **designação de profissionais em projetos de auditoria externa**, com comparação entre duas abordagens de otimização:

- **MILP** (*Mixed-Integer Linear Programming*)
- **GA** (*Genetic Algorithm*)

O repositório está organizado para separar:

- a **geração das instâncias sintéticas**;
- o **escalonamento das bases**;
- a **execução da otimização**;
- a **consolidação das métricas**;
- e a **análise final dos resultados**.

---

## Estrutura do repositório

```text
Mestrado-MILP-GA/
├── gera-instancia-I1-I3/
├── gera-instancias-I2-I4-I5/
└── otimiza-milp-ga/
```

---

## O papel de cada pasta

### `gera-instancia-I1-I3`
Contém os scripts e arquivos necessários para gerar e documentar as instâncias-base do estudo.

### `gera-instancias-I2-I4-I5`
Contém o processo de escalonamento da base `LARGE_V31` para gerar as demais instâncias derivadas usadas no experimento.

### `otimiza-milp-ga`
Contém o pipeline principal de otimização, consolidação de métricas e análise de resultados.

É nesta pasta que a reprodução do experimento é efetivamente executada.

---

## Fluxo recomendado de uso

### 1. Gerar as instâncias-base
Use a pasta:

```bash
gera-instancia-I1-I3
```

Essa etapa é necessária apenas se você quiser recriar as bases originais do estudo.

---

### 2. Gerar as instâncias escaladas
Use a pasta:

```bash
gera-instancias-I2-I4-I5
```

Essa etapa é necessária apenas se você quiser reproduzir o escalonamento das instâncias intermediárias e maiores.

---

### 3. Executar a otimização e a análise
Use a pasta:

```bash
otimiza-milp-ga
```

Nela está o fluxo correto de processamento do experimento.

---

## Sequência correta de processamento da otimização

Dentro de `otimiza-milp-ga`, o processamento deve seguir esta ordem:

### 1. Calibração
```bash
python scripts/_calibrate_all.py
```
Executar **apenas uma vez**, ou novamente **somente se novas bases tiverem sido geradas**.

### 2. Execução principal
```bash
python scripts/run_all.py
```
Atualiza o arquivo:

```text
data/results/experiment_metrics.csv
```

### 3. Completação do cenário MILP sem BE
```bash
python scripts/run_milp_noBE.py
```
Completa a execução iniciada em `run_all.py`.

### 4. Execução multiseed
```bash
python scripts/run_multiseed.py
```
Atualiza o arquivo:

```text
data/results/experiment_metrics_multiseed.csv
```

> Observação: esta etapa pode levar **até 3 dias**, dependendo da máquina utilizada.

### 5. Análise final
```bash
python scripts/analyze_experiment.py
```
Consolida a análise final a partir das métricas geradas nas etapas anteriores.

---

## Fluxo mínimo para reprodução do experimento

```bash
cd otimiza-milp-ga
python scripts/_calibrate_all.py
python scripts/run_all.py
python scripts/run_milp_noBE.py
python scripts/run_multiseed.py
python scripts/analyze_experiment.py
```

---

## Observação importante

A calibração (`scripts/_calibrate_all.py`) **não precisa ser executada toda vez**. Ela deve ser rodada apenas quando houver alteração nas bases ou geração de novas instâncias.

---

## Reprodutibilidade

Para reproduzir corretamente o experimento:

1. garanta que as instâncias estejam disponíveis na estrutura esperada;
2. instale as dependências descritas em `otimiza-milp-ga/requirements.txt`;
3. siga rigorosamente a ordem de execução descrita acima.

---

## Autora

**Valéria dos Santos Souza**  
Dissertação de mestrado em Computação Aplicada.

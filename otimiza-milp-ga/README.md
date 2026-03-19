# Otimização MILP-GA

Esta pasta reúne os códigos de otimização usados na dissertação para resolver o problema de designação de profissionais em projetos de auditoria externa por duas abordagens:

- **MILP** (*Mixed-Integer Linear Programming*)
- **GA** (*Genetic Algorithm*)

O fluxo foi organizado em duas etapas separadas:

1. **processamento** das instâncias;
2. **análise posterior** dos resultados.

Os scripts principais de otimização foram ajustados para rodar de forma **limpa**, isto é, sem geração automática de:

- arquivos Excel;
- gráficos;
- relatórios extensos no console;
- artefatos auxiliares de análise.

Assim, o processamento fica mais controlado e a geração de métricas, tabelas, diagnósticos e figuras pode ser feita depois, de forma separada.

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
├── analysis/
├── metrics/
└── ...
```

> A estrutura exata pode variar conforme a versão do projeto, mas a lógica permanece a mesma: **rodar primeiro os modelos** e **analisar depois os resultados**.

---

## O que esta pasta faz

Esta pasta permite:

- executar o **MILP** sobre uma instância sintética;
- executar o **GA** sobre uma instância sintética;
- salvar os resultados principais do processamento;
- e, em uma etapa posterior, gerar as **análises e métricas** usadas na dissertação.

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

### 2. Execute o processamento
Rode o modelo desejado:

- **MILP**
- **GA**

Nesta etapa, o objetivo é apenas obter a solução e salvar os resultados principais.

### 3. Execute as análises depois
Com os resultados já produzidos, rode separadamente os scripts de:

- métricas;
- diagnósticos;
- consolidação;
- tabelas;
- figuras;
- comparações entre cenários.

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

## Comportamento atual dos scripts de otimização

Os scripts `ga_model.py` e `milp_model.py` foram ajustados para:

- evitar geração automática de saídas auxiliares;
- evitar poluição do console;
- manter apenas mensagens curtas de status;
- preservar a lógica principal de processamento.

Em outras palavras:

- o modelo **resolve primeiro**;
- a análise **vem depois**.

Isso foi feito para deixar o pipeline mais robusto, mais limpo e mais aderente à lógica da dissertação, em que os artefatos analíticos são produzidos em uma etapa posterior ao processamento bruto.

---

## O que foi desativado no processamento automático

Durante a execução principal dos modelos, ficaram desativados por padrão:

- exportações automáticas para `.xlsx`;
- geração automática de gráficos;
- diagnósticos detalhados impressos em tela;
- relatórios auxiliares longos;
- saídas visuais não essenciais ao processamento.

As funções relacionadas a essas análises **não foram removidas**. Elas apenas deixaram de ser chamadas automaticamente no fluxo principal.

---

## Etapa de análise posterior

Depois que MILP e GA terminarem o processamento, a análise pode ser executada separadamente para gerar os artefatos usados na dissertação, como por exemplo:

- métricas consolidadas;
- tabelas comparativas;
- listas de alocados e não alocados;
- diagnósticos de cobertura;
- verificações de composição;
- resumos por porte de projeto;
- figuras e grafos.

Essa separação ajuda a:

- reduzir risco de quebra durante o processamento;
- facilitar depuração;
- permitir reuso dos resultados;
- manter o pipeline mais organizado.

---

## Quando usar esta pasta

Use `otimiza-milp-ga` quando você quiser:

- rodar os modelos diretamente;
- reproduzir os experimentos;
- comparar MILP e GA;
- gerar os resultados-base que serão analisados depois.

---

## Relação com o restante do repositório

Esta pasta representa a etapa de **execução experimental** do projeto.

A relação com as demais pastas é:

- `gera-instancia-I1-I3` → gera e documenta as instâncias-base;
- `gera-instancias-I2-I4-I5` → escala a base `LARGE_V31`;
- `otimiza-milp-ga` → executa os modelos e produz os resultados do experimento.

---

## Sequência recomendada

Se você quer reproduzir o pipeline completo, siga esta ordem:

1. gerar ou obter as instâncias;
2. executar o MILP e/ou o GA;
3. executar as análises e métricas separadamente.

Se você já possui as bases prontas, comece diretamente pelo passo 2.

---

## Observação final

Este README substitui instruções dispersas em arquivos auxiliares e concentra, em um único lugar, o fluxo principal da pasta de otimização.

A ideia é simples:

- **processar primeiro**;
- **analisar depois**.


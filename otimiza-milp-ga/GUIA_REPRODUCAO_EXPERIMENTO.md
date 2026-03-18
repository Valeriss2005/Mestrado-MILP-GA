# Guia Rápido: Como Reproduzir o Experimento da Dissertação

Este guia mostra como qualquer pessoa pode refazer o experimento completo, usando os scripts e arquivos certos da pasta disserta_v2.

## 1. Instale as dependências

```sh
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

## 2. Entenda a estrutura
- `configs/experiment_config.json`: define instâncias, cenários e tolerâncias.
- `models/`: modelos GA e MILP.
- `scripts/`: orquestração, análise, geração de instâncias.
- `data/instances/`: instâncias sintéticas.

## 3. Execute o experimento completo

```sh
python scripts/run_experiment.py --config configs/experiment_config.json
```

- O script irá:
  - Calibrar tolerâncias (MILP)
  - Rodar GA sem BE, GA com BE, MILP com BE para cada instância
  - Coletar métricas em CSV

## 4. Analise os resultados
- Os resultados e métricas ficam em `data/results/`.
- Use os scripts de análise em `scripts/` para gerar gráficos e tabelas.

## 5. Dicas
- Para rodar no Google Colab, siga as instruções impressas pelo script.
- Para rodar apenas um cenário/modelo, edite o JSON ou use os scripts específicos.
- Consulte o README e a dissertação para detalhes teóricos e metodológicos.

---

**Dica:** Sempre sincronize scripts, configs e modelos para garantir reprodutibilidade!

---

Dúvidas? Consulte a dissertação ou abra um dos notebooks/scripts para exemplos detalhados.

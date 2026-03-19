## OTIMIZAÇÃO DA DESIGNAÇÃO DE PROFISSIONAIS DE AUDITORIA INCORPORANDO VARIÁVEIS DE BEM-ESTAR: UMA COMPARAÇÃO ENTRE MODELOS MATEMÁTICOS E META-HEURÍSTICAS

Este repositório contém o código, modelos e instâncias sintéticas necessários para reproduzir e aprimorar o experimento descrito na dissertação de mestrado.

## Estrutura do Projeto

- `requirements.txt` — Dependências Python
- `LICENSE` — Licença do projeto
- `configs/` — Arquivos de configuração do experimento
- `models/` — Modelos de otimização (GA, MILP)
- `scripts/` — Scripts de execução, análise e geração de instâncias
- `data/instances/` — Instâncias sintéticas principais

## Como rodar

1. Crie um ambiente virtual Python e instale as dependências:
   ```sh
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
2. Execute os scripts principais em `scripts/` conforme o README detalhado.
3. Para gerar novas instâncias sintéticas, utilize o script de geração em `scripts/`.

## Resultados e Saídas
- Os resultados, gráficos e arquivos XLS são gerados em subpastas de `data/results/`.
- O usuário pode escolher quais saídas gerar.

## Monitoramento e Logs
- O painel CLI permite acompanhar o progresso, pausar/retomar execuções e registra início/fim de cada experimento.
- O sistema registra informações do ambiente para reprodutibilidade.

## Contribuição
Pull requests são bem-vindos! Veja as instruções no README detalhado.

---

> Para detalhes completos, consulte o README detalhado e a documentação nos scripts.

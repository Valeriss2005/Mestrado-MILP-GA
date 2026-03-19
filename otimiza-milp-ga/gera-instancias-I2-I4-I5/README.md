## OTIMIZAÇÃO DA DESIGNAÇÃO DE PROFISSIONAIS DE AUDITORIA INCORPORANDO VARIÁVEIS DE BEM-ESTAR: UMA COMPARAÇÃO ENTRE MODELOS MATEMÁTICOS E META-HEURÍSTICAS

Este repositório contém o código, modelos e instâncias sintéticas necessários para reproduzir e aprimorar o experimento descrito na dissertação de mestrado.

# Dissertação - Experimento de Otimização

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



> Para detalhes completos, consulte o README detalhado e a documentação nos scripts.

Neste projeto, as “instâncias” são bases de dados sintéticas que simulam cenários reais de alocação de funcionários em projetos, baseando-se na estrutura e características da base real denominada `LARGE_V31.zip`. Cada instância representa um conjunto de funcionários, projetos, clientes e suas relações, com diferentes tamanhos e complexidades.

### Características das instâncias

- **Origem:** Todas as instâncias são derivadas da base real `LARGE_V31.zip`, que contém dados reais anonimizados de uma grande empresa.
- **Proporções realistas:** As instâncias mantêm proporções de categorias de funcionários, tamanhos de projetos e densidades de vínculos (treinamentos, skills, restrições) observadas na base real.
- **Tipos de instâncias geradas:**
   - **LARGE_05X:** Redução para 50% do tamanho da base original (aprox. 600 funcionários, 160 projetos).
   - **LARGE_15X:** Expansão para 150% do tamanho original (aprox. 1800 funcionários, 480 projetos).
   - **LARGE_25X:** Expansão para 250% do tamanho original (aprox. 3000 funcionários, 800 projetos).
- **Como são geradas:**
   - Instâncias menores são criadas por subamostragem estratificada, preservando as proporções de categorias e tamanhos.
   - Instâncias maiores são criadas por expansão, clonando e perturbando registros da base original para simular novos funcionários e projetos.
- **Coerência:** Todas as referências cruzadas (IDs, vínculos) são mantidas válidas, garantindo que as instâncias possam ser usadas em experimentos de otimização e simulação sem inconsistências.

### Para que servem?

Essas instâncias permitem:
- Testar algoritmos de alocação em diferentes escalas.
- Avaliar desempenho e robustez de modelos em cenários realistas.
- Compartilhar experimentos reprodutíveis sem expor dados sensíveis.

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

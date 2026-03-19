# Geração das Instâncias I2, I4 e I5

Esta pasta contém os scripts usados para gerar as instâncias escaladas do experimento a partir da base `LARGE_V31.zip`.

Na nomenclatura da dissertação, esta pasta cobre:

- **I2**
- **I4**
- **I5**

As instâncias geradas preservam a lógica estrutural da base `LARGE_V31`, aplicando escalonamento proporcional para suportar testes de maior ou menor porte.

---

## O que esta pasta gera

A partir de `LARGE_V31.zip`, o script desta pasta pode gerar:

- `LARGE_05X_V01.zip` → instância reduzida (**I2**)
- `LARGE_15X_V01.zip` → instância expandida (**I4**)
- `LARGE_25X_V01.zip` → instância expandida em maior escala (**I5**)

Essas instâncias são usadas nos experimentos comparativos do MILP e do GA em cenários de porte crescente.

---

## Estrutura esperada

```text
gera-instancias-I2-I4-I5/
├── README.md
├── requirements.txt
├── data/
│   └── instances/
│       └── LARGE_V31.zip
└── scripts/
    └── instance_generator_v5.py
```

---

## Antes de executar

Certifique-se de que:

1. a base `LARGE_V31.zip` está em `data/instances/`;
2. as dependências estão instaladas;
3. você está posicionado na pasta `gera-instancias-I2-I4-I5`.

---

## Instalação do ambiente

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Como executar

Entre na pasta:

```bash
cd gera-instancias-I2-I4-I5
```

### Passo 1 — Verifique se a base está no lugar certo

O arquivo de entrada deve estar em:

```text
data/instances/LARGE_V31.zip
```

### Passo 2 — Execute o gerador

Comando principal:

```bash
python scripts/instance_generator_v5.py
```

Esse comando lê a base `LARGE_V31.zip` e gera, por padrão, as três instâncias escaladas.

---

## Parâmetros suportados

O script `scripts/instance_generator_v5.py` aceita os seguintes parâmetros:

### `--instances`
Define quais instâncias devem ser geradas.

Opções válidas:

- `LARGE_05X`
- `LARGE_15X`
- `LARGE_25X`

Se o parâmetro não for informado, o script gera as três instâncias.

### `--seed`
Define a seed base da geração.

Valor padrão:

```text
42
```

### `--source`
Define o caminho do arquivo de entrada.

Valor padrão:

```text
data/instances/LARGE_V31.zip
```

### `--output`
Define a pasta de saída das instâncias geradas.

Valor padrão:

```text
data/instances
```

---

## Execução comando a comando

### Gerar todas as instâncias
```bash
python scripts/instance_generator_v5.py
```

### Gerar apenas a I2
```bash
python scripts/instance_generator_v5.py --instances LARGE_05X
```

### Gerar apenas a I4
```bash
python scripts/instance_generator_v5.py --instances LARGE_15X
```

### Gerar apenas a I5
```bash
python scripts/instance_generator_v5.py --instances LARGE_25X
```

### Gerar I2 e I4 juntas
```bash
python scripts/instance_generator_v5.py --instances LARGE_05X LARGE_15X
```

### Definir seed manualmente
```bash
python scripts/instance_generator_v5.py --instances LARGE_25X --seed 123
```

### Informar origem e saída explicitamente
```bash
python scripts/instance_generator_v5.py --source data/instances/LARGE_V31.zip --output data/instances
```

---

## Fluxo mínimo completo

### Windows

```bash
cd gera-instancias-I2-I4-I5
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/instance_generator_v5.py
```

### Linux / macOS

```bash
cd gera-instancias-I2-I4-I5
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/instance_generator_v5.py
```

---

## O que o script faz

O script `scripts/instance_generator_v5.py`:

1. lê a base `LARGE_V31.zip`;
2. extrai as tabelas da instância original;
3. aplica regras de escalonamento proporcional;
4. preserva coerência entre funcionários, projetos, clientes e vínculos;
5. grava as novas instâncias na pasta de saída.

---

## Onde os arquivos são gravados

Por padrão, os arquivos gerados são salvos em:

```text
data/instances/
```

Após a execução, verifique a presença de arquivos como:

- `LARGE_05X_V01.zip`
- `LARGE_15X_V01.zip`
- `LARGE_25X_V01.zip`

---

## Relação com o restante do repositório

O fluxo completo do projeto é:

1. `gera-instancia-I1-I3`  
   Gera e documenta as instâncias-base `SMALL_V15` e `LARGE_V31`.

2. `gera-instancias-I2-I4-I5`  
   Escala a `LARGE_V31` para gerar as demais instâncias do experimento.

3. `otimiza-milp-ga`  
   Executa os modelos MILP e GA e gera as análises e métricas da dissertação.

---

## Sequência recomendada

### Caso A — Já tenho a `LARGE_V31.zip`
Rode:

```bash
cd gera-instancias-I2-I4-I5
python scripts/instance_generator_v5.py
```

### Caso B — Ainda não tenho a `LARGE_V31.zip`
Primeiro gere ou copie a base a partir da pasta:

```text
gera-instancia-I1-I3
```

Depois volte para:

```text
gera-instancias-I2-I4-I5
```

e execute:

```bash
python scripts/instance_generator_v5.py
```

---

## Resultado esperado

Ao final, você terá as instâncias derivadas da `LARGE_V31` prontas para uso na pasta de otimização.

Essas bases podem então ser copiadas ou referenciadas a partir de:

```text
otimiza-milp-ga
```

---

## Observação final

Esta pasta não executa os modelos de otimização. Ela prepara as instâncias escaladas que serão usadas depois nos experimentos com MILP e GA.

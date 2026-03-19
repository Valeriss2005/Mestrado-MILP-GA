# Geração das Instâncias Sintéticas I1 e I3

Esta pasta contém o código e a documentação das bases sintéticas utilizadas nos experimentos do estudo de designação de profissionais em projetos de auditoria externa.

## Correspondência com a dissertação

- `SMALL_V15` = **I1**
- `LARGE_V31` = **I3**

A instância `SMALL_V15` representa o cenário de menor porte utilizado nos experimentos, enquanto a instância `LARGE_V31` representa o cenário ampliado empregado nas análises de maior escala.

## Objetivo

Documentar, de forma transparente e reproduzível, como as bases sintéticas utilizadas nos experimentos foram construídas.

O repositório inclui tanto as bases finais utilizadas nos experimentos quanto os scripts de geração correspondentes, disponibilizados para fins de transparência metodológica e reprodutibilidade.

## Arquivos principais

- `gerar_instancias.py`: script principal para geração das instâncias
- `parametros_small_v15.py`: parâmetros da instância `SMALL_V15` (**I1**)
- `parametros_large_v31.py`: parâmetros da instância `LARGE_V31` (**I3**)
- `data/SMALL_V15.zip`: instância correspondente à **I1**
- `data/LARGE_V31.zip`: instância correspondente à **I3**
- `docs/dicionario_tabelas.md`: descrição das tabelas e campos

## Estrutura das bases

### `SMALL_V15` (I1)

Contém as tabelas:

- `SMALL_TbFuncionarios`
- `SMALL_TbClientes`
- `SMALL_TbProjetos`
- `SMALL_TbCategorias`
- `SMALL_TbComposicao`
- `SMALL_TbFuncionarios_Skill`
- `SMALL_TbTreinamentos_Obrigatorios`
- `SMALL_TbFuncionarios_Treinamentos_Obrigatorios`
- `SMALL_TbFuncionarios_Indisponiveis`
- `SMALL_TbProjetos_Autoexclusao`
- `SMALL_TbProjetos_Descompressao`
- `SMALL_TbProjetos_Independencia`
- `SMALL_TbProjetos_Alocacao`

Resumo estrutural:

- 220 funcionários
- 60 clientes
- 60 projetos
- 6 categorias profissionais
- 3 treinamentos obrigatórios
- 22 indisponibilidades
- 7 autoexclusões
- 11 descompressões
- 5 independências
- 190 pares candidato-projeto

### `LARGE_V31` (I3)

Contém as tabelas:

- `TbFuncionarios`
- `TbClientes`
- `TbProjetos`
- `TbCategorias`
- `TbComposicao`
- `TbFuncionarios_Skill`
- `TbTreinamentos_Obrigatorios`
- `TbFuncionarios_Treinamentos_Obrigatorios`
- `TbFuncionarios_Indisponiveis`
- `TbProjetos_Autoexclusao`
- `TbProjetos_Descompressao`
- `TbProjetos_Independencia`
- `TbProjetos_Alocacao`

Resumo estrutural:

- 1.200 funcionários
- 240 clientes
- 320 projetos
- 6 categorias profissionais
- 4 treinamentos obrigatórios
- 144 indisponibilidades
- 120 autoexclusões
- 240 descompressões
- 5 independências
- 2.160 pares candidato-projeto

## Como executar

Instale as dependências:

```bash
pip install -r requirements.txt
```

Gere a instância I1:

```bash
python gerar_instancias.py --instancia SMALL_V15
```

Gere a instância I3:

```bash
python gerar_instancias.py --instancia LARGE_V31
```

Por padrão, os arquivos CSV e o arquivo ZIP são gerados em uma pasta chamada `saida/`.

Também é possível definir um diretório de saída:

```bash
python gerar_instancias.py --instancia SMALL_V15 --saida minha_saida
```

## Nota sobre reprodutibilidade

Esta pasta disponibiliza tanto as instâncias sintéticas finais utilizadas nos experimentos quanto os scripts que documentam sua geração. O objetivo é garantir transparência metodológica e facilitar a compreensão da lógica de construção das bases.

As bases são sintéticas e foram estruturadas para representar cenários plausíveis de designação de profissionais em projetos de auditoria externa no contexto de firmas Big Four.

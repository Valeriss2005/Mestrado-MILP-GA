# Dicionário das Tabelas

## Instância `SMALL_V15` (I1)

### `SMALL_TbFuncionarios`
Contém os profissionais sintéticos da firma.

Campos:
- `ID_Func`
- `Nome_Func`
- `ID_Categ`
- `Salario_Hora`
- `CEP_Func`
- `Cidade_Func`
- `Latitude_Func`
- `Longitude_Func`

### `SMALL_TbClientes`
Campos:
- `ID_Cli`
- `Nome_Cli`
- `CEP_Cli`
- `Cidade_Cli`
- `Latitude_Cli`
- `Longitude_Cli`

### `SMALL_TbProjetos`
Campos:
- `ID_Proj`
- `ID_Cli`
- `Tam_Proj`
- `Max_Pessoas`
- `Qt_horas_Previstas`
- `Data_Inicio_Proj`
- `Data_Fim_Proj`

### `SMALL_TbCategorias`
Contém as categorias profissionais e seus parâmetros de capacidade.

### `SMALL_TbComposicao`
Define a composição ideal mínima de equipe por porte de projeto.

### `SMALL_TbFuncionarios_Skill`
Relaciona funcionários a skills adicionais.

### `SMALL_TbTreinamentos_Obrigatorios`
Lista os treinamentos obrigatórios considerados na instância.

### `SMALL_TbFuncionarios_Treinamentos_Obrigatorios`
Relaciona funcionários aos treinamentos obrigatórios realizados.

### `SMALL_TbFuncionarios_Indisponiveis`
Registra períodos de indisponibilidade.

### `SMALL_TbProjetos_Autoexclusao`
Registra pares funcionário-projeto com autoexclusão.

### `SMALL_TbProjetos_Descompressao`
Registra pares funcionário-projeto com janela de descompressão.

### `SMALL_TbProjetos_Independencia`
Registra pares projeto-funcionário com restrição de independência.

### `SMALL_TbProjetos_Alocacao`
Contém os pares candidato-projeto considerados nos experimentos.

---

## Instância `LARGE_V31` (I3)

### `TbFuncionarios`
Contém os profissionais sintéticos da firma.

Campos:
- `ID_Func`
- `Nome_Func`
- `ID_Categ`
- `Cidade_Func`
- `CEP_Func`
- `Latitude_Func`
- `Longitude_Func`
- `Salario_Hora`
- `Industria_Principal`
- `Cross`

### `TbClientes`
Campos:
- `ID_Cli`
- `Nome_Cli`
- `Cidade_Cli`
- `CEP_Cli`
- `Latitude_Cli`
- `Longitude_Cli`

### `TbProjetos`
Campos:
- `ID_Proj`
- `ID_Cli`
- `Nome_Proj`
- `Tam_Proj`
- `Data_Inicio_Proj`
- `Data_Fim_Proj`
- `Qt_horas_Previstas`
- `Max_Pessoas`

### `TbCategorias`
Contém as categorias profissionais e seus parâmetros de capacidade.

### `TbComposicao`
Define a composição ideal mínima de equipe por porte de projeto.

### `TbFuncionarios_Skill`
Relaciona funcionários a skills adicionais.

### `TbTreinamentos_Obrigatorios`
Lista os treinamentos obrigatórios considerados na instância.

### `TbFuncionarios_Treinamentos_Obrigatorios`
Relaciona funcionários aos treinamentos obrigatórios realizados.

### `TbFuncionarios_Indisponiveis`
Registra períodos de indisponibilidade.

### `TbProjetos_Autoexclusao`
Registra pares funcionário-projeto com autoexclusão.

### `TbProjetos_Descompressao`
Registra pares funcionário-projeto sujeitos à descompressão.

### `TbProjetos_Independencia`
Registra pares projeto-funcionário com restrição de independência.

### `TbProjetos_Alocacao`
Contém os pares candidato-projeto considerados nos experimentos.

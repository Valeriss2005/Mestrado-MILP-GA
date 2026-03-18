import os
import sys
import json
import time
from datetime import datetime
import subprocess

CHECKPOINT_FILE = "experiment_checkpoint.json"

# Lista de instâncias e cenários (exemplo)
INSTANCIAS = [
    "data/instances/SMALL_V15.zip",
    # Adicione outras instâncias aqui
]
CENARIOS = [
    True,  # Bem-estar ativado
    False  # Bem-estar desativado
]

def perguntar_geracao():
    resp = input("Deseja gerar arquivos de gráficos e XLS? (s/n): ").strip().lower()
    return resp == 's'

def salvar_checkpoint(idx_inst, idx_cen):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({"idx_inst": idx_inst, "idx_cen": idx_cen}, f)

def carregar_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"idx_inst": 0, "idx_cen": 0}

def main():
    print("==== GERENCIADOR DE EXPERIMENTOS ====")
    print(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    gerar_saidas = perguntar_geracao()
    checkpoint = carregar_checkpoint()
    try:
        for idx_inst, instancia in enumerate(INSTANCIAS[checkpoint["idx_inst"]:], start=checkpoint["idx_inst"]):
            for idx_cen, bem_estar in enumerate(CENARIOS[checkpoint["idx_cen"]:] if idx_inst == checkpoint["idx_inst"] else CENARIOS):
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Rodando instância {instancia} | Cenário: {'Bem-estar' if bem_estar else 'Sem bem-estar'} ({idx_inst+1}/{len(INSTANCIAS)})")
                start = time.time()
                args = [sys.executable, "models/ga_model.py", instancia]
                if not bem_estar:
                    args.append("--no-be")
                if not gerar_saidas:
                    os.environ["NO_OUTPUT"] = "1"
                proc = subprocess.run(args)
                end = time.time()
                print(f"Tempo de execução: {end-start:.2f}s")
                salvar_checkpoint(idx_inst, idx_cen)
    except KeyboardInterrupt:
        print("\nExecução pausada pelo usuário. Progresso salvo.")
        sys.exit(0)
    print(f"\nFim: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    print("Experimento concluído!")

if __name__ == "__main__":
    main()

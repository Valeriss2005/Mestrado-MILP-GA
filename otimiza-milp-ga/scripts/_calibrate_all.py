#!/usr/bin/env python3
"""
Calibração / validação MILP para todas as 5 instâncias do experimento.
Executa cada instância com BE ativo e tolerâncias padrão (1%/2%/5%).
Se viável → registra. Se inviável → tenta grid-search progressivo.

Uso: python scripts/_calibrate_all.py
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Fix encoding for Windows redirection
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from models.milp_model import executar_modelo, PAR

# ── Instâncias na ordem crescente de tamanho ─────────────────────────
INSTANCES = [
    ("I1_SMALL",      "SMALL_V15.zip",      "SMALL (220/60)"),
    ("I2_LARGE_05X",  "LARGE_05X_V01.zip",  "LARGE_05X (600/160)"),
    ("I3_LARGE",      "LARGE_V31.zip",      "LARGE (1200/320)"),
    ("I4_LARGE_15X",  "LARGE_15X_V01.zip",  "LARGE_15X (1800/480)"),
    ("I5_LARGE_25X",  "LARGE_25X_V01.zip",  "LARGE_25X (3000/800)"),
]

# ── Tolerâncias padrão (calibradas na LARGE_V31) ─────────────────────
DEFAULT_TOLS = {
    "TOL_COMPOSICAO":       0.01,
    "TOL_TREINO":           0.02,
    "TOL_PESSOAS_ALOCADAS": 0.05,
}

# ── Grid-search progressivo se default falhar ─────────────────────────
TOL_GRID = [0.00, 0.01, 0.02, 0.03, 0.05]

def set_tolerances(tol_comp, tol_treino, tol_pessoas):
    """Configura tolerâncias no PAR global."""
    PAR["TOL_COMPOSICAO"]       = tol_comp
    PAR["TOL_TREINO"]           = tol_treino
    PAR["TOL_PESSOAS_ALOCADAS"] = tol_pessoas
    PAR["TOL_DIST"]             = 0.00
    PAR["TOL_AUTO"]             = 0.00
    PAR["TOL_DESC"]             = 0.00
    PAR["TOL_COBERTURA_PROJETOS"] = 0.00
    PAR["TOL_SDEM_GLOBAL"]      = 0.00
    PAR["TOL_SDEM_LOCAL"]       = 0.00

def run_milp(zip_path, timeout=900, gap=0.01):
    """Executa MILP e retorna resultado."""
    PAR["TIMEOUT"] = timeout
    PAR["GAPREL"]  = gap
    PAR["ARQUIVO_ZIP"] = zip_path
    return executar_modelo(zip_path, ativar_bem_estar=True)

def grid_search(zip_path, timeout=600):
    """Grid-search progressivo de tolerâncias."""
    combos = []
    for tc in TOL_GRID:
        for tt in TOL_GRID:
            for tp in TOL_GRID:
                if tc <= 0.05 and tt <= 0.05 and tp <= 0.05:
                    combos.append((tc, tt, tp, tc + tt + tp))
    combos.sort(key=lambda x: x[3])  # soma crescente

    for i, (tc, tt, tp, soma) in enumerate(combos):
        print(f"    Grid [{i+1}/{len(combos)}] comp={tc} treino={tt} pessoas={tp} (soma={soma:.2f})")
        set_tolerances(tc, tt, tp)
        try:
            res = run_milp(zip_path, timeout=timeout, gap=0.02)
            status = res.get("status_txt", "???")
            if status == "Optimal":
                return {"status": "Optimal", "tols": (tc, tt, tp), "resultado": res}
        except Exception as e:
            print(f"      ERRO: {e}")
            continue
    return {"status": "Infeasible", "tols": None, "resultado": None}

# ── Arquivo de saída ──────────────────────────────────────────────────
OUTPUT_FILE = os.path.join("data", "results", "calibration_results.json")
RESULTS = {}

# ── Selecionar instância via argumento ────────────────────────────────
selected = None
if len(sys.argv) > 1:
    selected = sys.argv[1].upper()
    print(f"Filtro: executando apenas instâncias que contêm '{selected}'")

# ── Loop principal ────────────────────────────────────────────────────
for inst_id, zipname, desc in INSTANCES:
    if selected and selected not in inst_id.upper():
        continue

    zip_path = os.path.join("data", "instances", zipname)
    if not os.path.exists(zip_path):
        print(f"\nSKIP: {zip_path} não encontrado")
        continue

    print(f"\n{'='*70}")
    print(f"  CALIBRAÇÃO: {desc} — {zipname}")
    print(f"  Tolerâncias padrão: COMP={DEFAULT_TOLS['TOL_COMPOSICAO']}, "
          f"TREINO={DEFAULT_TOLS['TOL_TREINO']}, "
          f"PESSOAS={DEFAULT_TOLS['TOL_PESSOAS_ALOCADAS']}")
    print(f"{'='*70}")

    # Definir timeout por tamanho
    nf_approx = int(desc.split("(")[1].split("/")[0])
    if nf_approx <= 300:
        timeout = 300
    elif nf_approx <= 700:
        timeout = 600
    elif nf_approx <= 1500:
        timeout = 900
    else:
        timeout = 1200

    print(f"  Timeout: {timeout}s")

    # Tentar com tolerâncias padrão primeiro
    set_tolerances(DEFAULT_TOLS["TOL_COMPOSICAO"], DEFAULT_TOLS["TOL_TREINO"], DEFAULT_TOLS["TOL_PESSOAS_ALOCADAS"])
    t0 = time.time()

    try:
        resultado = run_milp(zip_path, timeout=timeout, gap=0.01)
        elapsed = time.time() - t0
        status = resultado.get("status_txt", "???")

        print(f"\n  >>> STATUS: {status}")
        print(f"  >>> Tempo total: {elapsed:.1f}s")

        if status == "Optimal":
            # Extrair métricas do resultado MILP (dados internos, não campos diretos)
            x = resultado.get("x", {})
            y = resultado.get("y", {})

            total_x = sum(1 for (i,j) in x if (x[i,j].varValue or 0) >= 0.9)
            total_y = sum(1 for j in y if (y[j].varValue or 0) >= 0.5)
            func_alocados = len(set(i for (i,j) in x if (x[i,j].varValue or 0) >= 0.9))
            nf = len(resultado.get("funcionarios", []))
            np_ = len(resultado.get("projetos", []))
            perc_func = 100.0 * func_alocados / max(1, nf)

            # Custo real (usando lookup dicts em vez de .loc repetido)
            df_func, df_proj, df_cli = resultado.get("dfs", (None, None, None))
            perc_tempo = resultado.get("perc_tempo", {})
            custo = 0.0
            if df_func is not None:
                _categ_map = dict(zip(df_func["ID_Func"], df_func["ID_Categ"].astype(int)))
                _sal_map   = dict(zip(df_func["ID_Func"], df_func["Salario_Hora"].astype(float)))
                _horas_map = dict(zip(df_proj["ID_Proj"], df_proj["Qt_horas_Previstas"].astype(float)))
                for (i,j) in x:
                    v = x[i,j].varValue or 0.0
                    if v >= 0.9:
                        c = _categ_map.get(i, 0)
                        horas = _horas_map.get(j, 0.0)
                        sal = _sal_map.get(i, 0.0)
                        perc = float(perc_tempo.get(c, 100.0))/100.0
                        custo += sal*horas*perc

            # Violações BE
            pares_dist = resultado.get("pares_dist", set())
            pares_auto = resultado.get("pares_auto", set())
            viol_dist = sum(1 for (i,j) in pares_dist if (i,j) in x and (x[i,j].varValue or 0) >= 0.9)
            viol_auto = sum(1 for (i,j) in pares_auto if (i,j) in x and (x[i,j].varValue or 0) >= 0.9)

            print(f"  >>> VIÁVEL com tolerâncias padrão!")
            print(f"  >>> Custo: R$ {custo:,.2f}")
            print(f"  >>> Projetos ativos: {total_y}/{np_}")
            print(f"  >>> Func alocados: {func_alocados}/{nf} ({perc_func:.1f}%)")
            print(f"  >>> Total alocações: {total_x}")
            print(f"  >>> Viol dist/auto: {viol_dist}/{viol_auto}")

            RESULTS[inst_id] = {
                "status": "Optimal",
                "TOL_COMPOSICAO": DEFAULT_TOLS["TOL_COMPOSICAO"],
                "TOL_TREINO": DEFAULT_TOLS["TOL_TREINO"],
                "TOL_PESSOAS_ALOCADAS": DEFAULT_TOLS["TOL_PESSOAS_ALOCADAS"],
                "custo_total_folha": round(custo, 2),
                "projetos_ativos": total_y,
                "total_projetos": np_,
                "funcionarios_alocados": func_alocados,
                "total_funcionarios": nf,
                "perc_funcionarios_alocados": round(perc_func, 1),
                "total_alocacoes": total_x,
                "tempo_total_s": round(elapsed, 1),
                "viol_distancia": viol_dist,
                "viol_autoexclusao": viol_auto,
            }
        else:
            print(f"  >>> Resultado: {status}. Iniciando grid-search...")
            gs = grid_search(zip_path, timeout=timeout)
            if gs["status"] == "Optimal":
                tc, tt, tp = gs["tols"]
                res = gs["resultado"]
                print(f"  >>> Grid-search encontrou solução: comp={tc}, treino={tt}, pessoas={tp}")
                RESULTS[inst_id] = {
                    "status": "Optimal",
                    "TOL_COMPOSICAO": tc,
                    "TOL_TREINO": tt,
                    "TOL_PESSOAS_ALOCADAS": tp,
                    "custo_total_folha": res.get("custo_total_folha", 0),
                    "tempo_total_s": round(time.time() - t0, 1),
                    "nota": "calibrado via grid-search"
                }
            else:
                print(f"  >>> INVIÁVEL — nenhuma combinação de tolerâncias funcionou!")
                RESULTS[inst_id] = {
                    "status": "Infeasible",
                    "nota": "Nenhuma combinação com TOL <= 5% viabilizou"
                }

    except Exception as e:
        elapsed = time.time() - t0
        print(f"  >>> ERRO após {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()
        RESULTS[inst_id] = {
            "status": "Erro",
            "erro": str(e),
            "tempo_total_s": round(elapsed, 1),
        }

    # Salvar resultados parciais a cada instância
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=2, ensure_ascii=False)
    print(f"\n  Resultados parciais salvos em {OUTPUT_FILE}")

# ── Resumo final ──────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("  RESUMO DA CALIBRAÇÃO")
print(f"{'='*70}")
for inst_id, res in RESULTS.items():
    status = res.get("status", "???")
    tempo = res.get("tempo_total_s", "?")
    if status == "Optimal":
        custo = res.get("custo_total_folha", 0)
        tols = f"comp={res.get('TOL_COMPOSICAO')}, treino={res.get('TOL_TREINO')}, pessoas={res.get('TOL_PESSOAS_ALOCADAS')}"
        print(f"  {inst_id:20s} → ✓ Optimal  R$ {custo:>15,.2f}  ({tempo}s)  [{tols}]")
    else:
        print(f"  {inst_id:20s} → ✗ {status}  ({tempo}s)")

print(f"\nResultados salvos em: {OUTPUT_FILE}")

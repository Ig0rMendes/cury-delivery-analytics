"""Preenche a seção "Principais resultados" do README com os números reais da sua base.

Uso (na raiz do projeto, com data/train.csv no lugar):

    python scripts/update_findings.py            # prazo de entrega padrão: 30 min
    python scripts/update_findings.py --sla 35   # outro prazo
    python scripts/update_findings.py --data "C:/caminho/train.csv"

Também grava docs/RESULTADOS.md com os insights completos (detalhes e ações).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# descobre a raiz do projeto e poe no path, assim o script roda de qualquer pasta
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.processing.loader import DataNotFoundError, SchemaError  # noqa: E402
from src.processing.pipeline import load_analytical_data  # noqa: E402
from src.reporting import findings_markdown, replace_block  # noqa: E402


# gera o bloco de resultados do README e o docs/RESULTADOS.md a partir dos dados reais
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sla", type=int, default=30, help="Prazo da etapa de entrega, em minutos.")
    ap.add_argument("--data", default=None, help="Caminho do train.csv (padrão: data/train.csv).")
    args = ap.parse_args()

    try:
        df, report = load_analytical_data(args.data)
    except (DataNotFoundError, SchemaError) as exc:
        print(f"Erro: {exc}")
        return 1

    # versao curta vai pro README, versao completa vai pro arquivo de resultados
    short = findings_markdown(df, report, args.sla, full=False)
    full = findings_markdown(df, report, args.sla, full=True)

    readme = ROOT / "README.md"
    if readme.exists():
        readme.write_text(replace_block(readme.read_text(encoding="utf-8"), short), encoding="utf-8")
        print(f"README atualizado: {readme}")
    else:
        print("README.md não encontrado; nada foi alterado.")

    out = ROOT / "docs" / "RESULTADOS.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("# Resultados completos\n\n" + full, encoding="utf-8")
    print(f"Resultados completos: {out}")
    print()
    print(short)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

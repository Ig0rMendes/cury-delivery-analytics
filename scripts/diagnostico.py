"""Diagnóstico rápido da base `train`: funil de limpeza e checagens de sanidade.

    python scripts/diagnostico.py

Não altera nenhum arquivo. Útil para conferir a qualidade dos dados antes de abrir o painel.
"""
from __future__ import annotations

import sys
from pathlib import Path

# mesma ideia: acha a raiz e ajusta o path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.metrics.experience import rating_granularity  # noqa: E402
from src.processing.loader import DataNotFoundError, SchemaError  # noqa: E402
from src.processing.pipeline import load_analytical_data  # noqa: E402

pd.set_option("display.width", 140)


# diagnostico rapido da base: mostra funil, ausencias e checagens. nao altera nenhum arquivo
def main() -> int:
    try:
        df, rep = load_analytical_data()
    except (DataNotFoundError, SchemaError) as exc:
        print(f"Erro: {exc}")
        return 1

    print(f"Fonte: {rep.source}")
    print(f"Registros brutos: {rep.raw_rows:,} | analisados: {rep.final_rows:,} ({rep.retention:.1%})\n")
    print("Funil de tratamento:")
    for s in rep.steps:
        print(f"  - {s['label']:<48} removidas: {s['removed']:>6,}  restantes: {s['remaining']:>7,}")
    print(f"\nAusências por campo (antes da remoção): {rep.missing_by_field}")
    print(f"Coordenadas com sinal corrigido: {rep.coords_sign_fixed:,}")
    print(f"Localização inválida (mantidas, sem distância): {rep.invalid_location_rows:,} ({rep.invalid_location_share:.1%})")
    print(f"Festival sem informação: {rep.festival_unknown:,}")

    print("\nDistância (km), só localizações válidas:")
    print(df["distance_km"].describe().round(2).to_string())
    print("\nTempos (min):")
    print(df[["prep_time_min", "delivery_time_min", "total_time_min"]].describe().round(2).to_string())

    # checa se a nota e por pedido ou atributo do entregador
    g = rating_granularity(df)
    print(f"\nNota: {g['constant_share']:.1%} dos entregadores (com 2+ pedidos) têm nota única.")
    print("  -> nota como ATRIBUTO do entregador" if g["is_courier_attribute"] else "  -> nota varia entre pedidos do mesmo entregador")

    print(f"\nCidades identificadas: {df['city'].nunique()} | restaurantes (proxy): {df['restaurant_id'].nunique():,}")
    print(df["city"].value_counts().head(10).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

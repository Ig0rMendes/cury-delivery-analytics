import sys
from pathlib import Path

import pytest

# poe a raiz do projeto no path, assim os testes acham o pacote src de qualquer lugar
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.processing.pipeline import process  # noqa: E402
from tests.synthetic import make_raw  # noqa: E402


# fixtures: dados sinteticos criados uma vez so pra sessao toda (mais rapido)
# a 'raw' imita o formato bruto do train.csv, com sujeira e tudo
@pytest.fixture(scope="session")
def raw():
    return make_raw(6000, seed=11)


@pytest.fixture(scope="session")
def analytic(raw):
    df, report = process(raw, source="sintetico")
    return df, report


@pytest.fixture(scope="session")
def df(analytic):
    return analytic[0]


@pytest.fixture(scope="session")
def report(analytic):
    return analytic[1]

import pytest

from src.reporting import MARK_END, MARK_START, findings_markdown, replace_block


# versao curta e completa do markdown de resultados
def test_findings_markdown_short_and_full(df, report):
    short = findings_markdown(df, report, 30, full=False)
    full = findings_markdown(df, report, 30, full=True)
    for page in ["Visão Executiva", "Operação", "Fatores Externos", "Entregadores", "Restaurantes", "Experiência do Cliente"]:
        assert f"**{page}**" in short
    assert len(full) > len(short) and "Ação sugerida" in full
    assert "ℹ️" not in short  # ressalvas só no relatório completo


# troca o bloco entre os marcadores sem estragar o resto do README
def test_replace_block_roundtrip():
    text = f"antes\n{MARK_START}\nvelho\n{MARK_END}\ndepois"
    out = replace_block(text, "novo\n")
    assert "velho" not in out and "novo" in out and out.startswith("antes") and out.endswith("depois")
    assert replace_block(out, "novo2\n").count(MARK_START) == 1


# sem marcadores tem que dar erro claro
def test_replace_block_without_markers_fails():
    with pytest.raises(ValueError):
        replace_block("sem marcadores", "x")

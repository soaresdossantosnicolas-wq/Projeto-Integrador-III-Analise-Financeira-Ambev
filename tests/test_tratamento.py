import pandas as pd


def test_escala_monetaria_e_idempotencia(tratamento):
    base = pd.DataFrame({"VL_CONTA": [10, 20], "ESCALA_MOEDA": ["MIL", "UNIDADE"]})
    convertido = tratamento.converter_numerico(base)
    assert convertido["VL_CONTA"].tolist() == [10000, 20]
    pd.testing.assert_frame_equal(tratamento.converter_numerico(convertido), convertido)
    assert base["VL_CONTA"].tolist() == [10, 20]


def test_exercicio_atual_e_conta_exata(tratamento):
    base = pd.DataFrame({
        "ORDEM_EXERC": ["PENÚLTIMO", " ÚLTIMO ", "ÚLTIMO"],
        "CD_CONTA": ["3.01", "3.01", "3.01.01"],
        "VL_CONTA": [90, 100, 50],
    })
    atual = tratamento.filtrar_ultimo_exercicio(base)
    conta = tratamento.localizar_conta_por_codigo(atual, "3.01")
    assert conta["VL_CONTA"].tolist() == [100]

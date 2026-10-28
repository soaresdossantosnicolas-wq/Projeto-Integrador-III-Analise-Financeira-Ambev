import pandas as pd


def test_escala_monetaria_e_idempotencia(tratamento):
    base = pd.DataFrame({"VL_CONTA": [10, 20], "ESCALA_MOEDA": ["MIL", "UNIDADE"]})
    convertido = tratamento.converter_numerico(base)
    assert convertido["VL_CONTA"].tolist() == [10000, 20]
    pd.testing.assert_frame_equal(tratamento.converter_numerico(convertido), convertido)
    assert base["VL_CONTA"].tolist() == [10, 20]


def test_exercicio_atual_e_conta_exata(tratamento):
    base = pd.DataFrame(
        {
            "ORDEM_EXERC": ["PENÚLTIMO", " ÚLTIMO ", "ÚLTIMO"],
            "CD_CONTA": ["3.01", "3.01", "3.01.01"],
            "VL_CONTA": [90, 100, 50],
        }
    )
    atual = tratamento.filtrar_ultimo_exercicio(base)
    conta = tratamento.localizar_conta_por_codigo(atual, "3.01")
    assert conta["VL_CONTA"].tolist() == [100]


def test_datas_reais_antes_de_rotular_ano(tratamento, cvm_dre):
    atual = tratamento.preparar_demonstrativo(cvm_dre, 2025, "DRE")
    assert atual.ANO_ANALISE.unique().tolist() == [2025]
    assert atual.loc[atual.CD_CONTA.eq("3.01"), "VL_CONTA"].tolist() == [1000000]


def test_rejeita_arquivo_reaproveitado_de_outro_ano(tratamento, cvm_dre):
    import pytest
    from excecoes import ErroValidacaoDados

    with pytest.raises(ErroValidacaoDados, match="DT_REFER"):
        tratamento.preparar_demonstrativo(cvm_dre, 2024, "DRE")


def test_rejeita_fim_do_exercicio_deslocado(tratamento, cvm_dre):
    import pytest
    from excecoes import ErroValidacaoDados

    cvm_dre.loc[cvm_dre.ORDEM_EXERC.eq("ÚLTIMO"), "DT_FIM_EXERC"] = "2024-12-31"
    with pytest.raises(ErroValidacaoDados, match="DT_FIM_EXERC"):
        tratamento.preparar_demonstrativo(cvm_dre, 2025, "DRE")


def test_rejeita_duplicatas_conflitantes(tratamento, cvm_dre):
    import pytest
    from excecoes import ErroValidacaoDados

    duplicada = cvm_dre.iloc[[0]].copy()
    duplicada["VL_CONTA"] = 999
    with pytest.raises(ErroValidacaoDados, match="duplicada"):
        tratamento.preparar_demonstrativo(pd.concat([cvm_dre, duplicada], ignore_index=True), 2025, "DRE")


def test_ultima_versao_e_duplicata_identica(tratamento, cvm_dre):
    versao2 = cvm_dre.copy()
    versao2["VERSAO"] = 2
    versao2["VL_CONTA"] *= 2
    base = pd.concat([cvm_dre, versao2, versao2], ignore_index=True)
    df = tratamento.preparar_demonstrativo(base, 2025, "DRE")
    assert len(df) == 12
    assert df.VERSAO.eq(2).all()
    assert df.loc[df.CD_CONTA.eq("3.01"), "VL_CONTA"].iloc[0] == 2000000


def test_comparativo_nunca_e_fallback(tratamento, cvm_dre):
    import pytest
    from excecoes import ErroValidacaoDados

    with pytest.raises(ErroValidacaoDados, match="ÚLTIMO"):
        tratamento.preparar_demonstrativo(cvm_dre[cvm_dre.ORDEM_EXERC.eq("PENÚLTIMO")], 2025, "DRE")


def test_moeda_escala_identidade_estritas(tratamento, cvm_dre):
    import pytest
    from excecoes import ErroValidacaoDados

    for campo, valor in (
        ("MOEDA", "DOLAR"),
        ("ESCALA_MOEDA", "DESCONHECIDA"),
        ("CNPJ_CIA", "00.000.000/0001-00"),
        ("GRUPO_DFP", "DF Individual"),
        ("DT_INI_EXERC", "2025-10-01"),
    ):
        invalida = cvm_dre.copy()
        invalida[campo] = valor
        with pytest.raises(ErroValidacaoDados):
            tratamento.preparar_demonstrativo(invalida, 2025, "DRE")


def test_pivot_proibe_media(tratamento):
    import pytest
    from excecoes import ErroValidacaoDados

    base = pd.DataFrame(
        {"ANO_ANALISE": [2025, 2025], "INDICADOR": ["receita_liquida"] * 2, "VL_CONTA": [100, 200]}
    )
    with pytest.raises(ErroValidacaoDados, match="média"):
        tratamento.criar_tabela_financeira(base)


def test_fallback_lucro_bruto_registrado(tratamento, caplog):
    base = pd.DataFrame({"ANO_ANALISE": [2025], "receita_liquida": [1000], "custo_vendas": [-600]})
    resultado = tratamento.derivar_lucro_bruto(base)
    assert resultado.lucro_bruto.iloc[0] == 400
    assert "3.03 ausente" in caplog.text


def test_identidade_invalida_impede_publicacao(tratamento):
    import pytest
    from excecoes import ErroValidacaoDados

    base = pd.DataFrame({"ANO_ANALISE": [2025], "ativo_total": [1000000]})
    with pytest.raises(ErroValidacaoDados, match="Identidade"):
        tratamento.validar_igualdade(base, "ativo_total", pd.Series([900000]), "balanço")


def test_conta_estoques_ausente_gera_motivo(analise, caplog):
    base = pd.DataFrame({"ativo_circulante": [100], "passivo_circulante": [50]})
    assert analise.calcular_liquidez(base).liquidez_seca.isna().all()
    assert "estoques" in caplog.text

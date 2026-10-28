"""Textos didáticos de apresentação; exemplos hipotéticos não alteram os dados financeiros."""

import config

# título, significado, cuidado de interpretação, exemplo hipotético
GLOSSARIO = {
    "ano_analise": (
        "Exercício",
        "Ano ao qual pertencem os resultados e o balanço.",
        "O ano dos dados não é necessariamente o ano em que o arquivo foi publicado.",
        "O exercício de 2025 termina em 31/12/2025.",
    ),
    "receita_liquida": (
        "Receita líquida",
        "Valor das vendas após deduções, como impostos sobre vendas, devoluções e descontos.",
        "Ainda não é lucro: custos e outras despesas precisam ser considerados.",
        "Vendas de R$ 110, com R$ 10 de deduções, resultam em R$ 100 de receita líquida.",
    ),
    "custo_vendas": (
        "Custo das vendas",
        "Gastos diretamente relacionados aos produtos vendidos.",
        "A DFP registra esse custo com sinal negativo, pois reduz o resultado.",
        "Receita de R$ 100 e custo de R$ 60 deixam R$ 40 de lucro bruto.",
    ),
    "lucro_bruto": (
        "Lucro bruto",
        "Receita líquida menos o custo dos produtos vendidos.",
        "Ainda não desconta todas as despesas operacionais, financeiras e tributos sobre o lucro.",
        "Receita de R$ 100 menos custo de R$ 60 gera lucro bruto de R$ 40.",
    ),
    "despesas_receitas_operacionais": (
        "Despesas/receitas operacionais",
        "Saldo de gastos e receitas ligados à operação, após o custo das vendas.",
        "Pode incluir vendas, administração e equivalência patrimonial; o sinal indica se aumenta ou reduz o resultado.",
        "Lucro bruto de R$ 40 e saldo operacional de −R$ 15 levam a EBIT de R$ 25.",
    ),
    "resultado_operacional": (
        "EBIT — resultado operacional CVM",
        "Resultado antes do resultado financeiro e dos tributos sobre o lucro.",
        "Neste projeto, a conta CVM 3.05 inclui equivalência patrimonial; por isso pode diferir do EBIT do release. Não é EBITDA nem fluxo de caixa.",
        "Um EBIT de R$ 25 não significa que R$ 25 entraram no caixa.",
    ),
    "resultado_financeiro": (
        "Resultado financeiro",
        "Saldo das receitas e despesas financeiras, como juros e determinados efeitos cambiais.",
        "Um saldo negativo reduz o resultado antes dos tributos.",
        "EBIT de R$ 25 e resultado financeiro de −R$ 5 deixam R$ 20 antes dos tributos.",
    ),
    "resultado_antes_tributos": (
        "Resultado antes dos tributos",
        "Resultado após considerar a operação e o resultado financeiro, antes dos tributos sobre o lucro.",
        "Ainda não corresponde ao lucro líquido.",
        "R$ 20 antes dos tributos, menos R$ 5 de tributos, deixam R$ 15 nas operações continuadas.",
    ),
    "tributos_lucro": (
        "Tributos sobre o lucro",
        "Efeito do imposto de renda e da contribuição social no resultado.",
        "Pode incluir tributos correntes e diferidos; não equivale necessariamente ao imposto pago em caixa naquele ano.",
        "Um efeito de −R$ 5 reduz o resultado em R$ 5.",
    ),
    "resultado_continuado": (
        "Resultado das operações continuadas",
        "Resultado após os tributos das atividades que continuam na empresa.",
        "É separado de resultados de operações classificadas como descontinuadas.",
        "Resultado continuado de R$ 15 e descontinuado de R$ 0 levam a lucro consolidado de R$ 15.",
    ),
    "resultado_descontinuado": (
        "Resultado das operações descontinuadas",
        "Resultado de atividades classificadas contabilmente como descontinuadas.",
        "Pode ser lucro, prejuízo ou zero; não deve ser confundido com toda venda de um ativo.",
        "Resultado continuado de R$ 15 e perda descontinuada de R$ 2 levam a lucro de R$ 13.",
    ),
    "lucro_liquido": (
        "Lucro líquido consolidado",
        "Resultado que sobra após custos, despesas, resultado financeiro e tributos.",
        "Inclui a participação de não controladores. Lucro não é o mesmo que caixa disponível ou dividendo pago.",
        "Receita de R$ 100 e lucro líquido de R$ 18 correspondem a margem líquida de 18%.",
    ),
    "equivalencia_patrimonial": (
        "Equivalência patrimonial",
        "Parcela do resultado de determinadas empresas investidas reconhecida contabilmente pela Ambev.",
        "Não significa necessariamente recebimento de dinheiro no período e entra no EBIT CVM usado aqui.",
        "O reconhecimento de R$ 2 de resultado de uma investida não implica recebimento imediato de R$ 2.",
    ),
    "ativo_total": (
        "Ativo total",
        "Conjunto dos recursos e direitos reconhecidos no balanço, como caixa, estoques e instalações.",
        "É um valor contábil, não o valor de mercado da empresa.",
        "Ativos de R$ 100 podem ser financiados por R$ 40 de obrigações e R$ 60 de patrimônio líquido.",
    ),
    "ativo_circulante": (
        "Ativo circulante",
        "Recursos e direitos classificados no curto prazo, em geral no ciclo operacional ou em até 12 meses.",
        "Inclui estoques e valores a receber; nem tudo já está disponível em dinheiro.",
        "R$ 20 em caixa, R$ 30 a receber e R$ 10 em estoques somam R$ 60 de ativo circulante.",
    ),
    "ativo_nao_circulante": (
        "Ativo não circulante",
        "Recursos e direitos classificados fora do circulante, como instalações e determinados investimentos.",
        "Não representa uma reserva de dinheiro de uso imediato.",
        "Uma fábrica pode integrar o ativo não circulante.",
    ),
    "caixa_equivalentes": (
        "Caixa e equivalentes",
        "Dinheiro e aplicações de alta liquidez que atendem à definição contábil de equivalente de caixa.",
        "Não inclui automaticamente todas as aplicações financeiras e não representa todo o ativo circulante.",
        "Caixa de R$ 20 é diferente de ativo circulante de R$ 60.",
    ),
    "estoques": (
        "Estoques",
        "Bens e materiais mantidos para produção ou venda, reconhecidos no balanço.",
        "Dependem de uso ou venda para virar recebimentos; são descontados na liquidez seca.",
        "Ativo circulante de R$ 60 menos estoques de R$ 10 deixa R$ 50 na base da liquidez seca.",
    ),
    "passivo_circulante": (
        "Passivo circulante",
        "Obrigações classificadas no curto prazo, como fornecedores, tributos e certas parcelas de empréstimos.",
        "Não corresponde somente a empréstimos bancários.",
        "Obrigações de curto prazo de R$ 50 formam o denominador da liquidez corrente.",
    ),
    "passivo_nao_circulante": (
        "Passivo não circulante",
        "Obrigações classificadas fora do curto prazo.",
        "Pode incluir empréstimos, provisões e outras obrigações, não apenas dívida bancária.",
        "R$ 30 no curto prazo e R$ 10 no longo prazo somam R$ 40 de passivo exigível.",
    ),
    "passivo_total": (
        "Passivo + PL — total da CVM",
        "Na conta CVM 2, o total reúne obrigações com terceiros e patrimônio líquido.",
        "Por identidade contábil, é igual ao ativo total. Não deve ser usado como dívida no endividamento geral.",
        "Obrigações de R$ 40 e PL de R$ 60 formam total CVM de R$ 100.",
    ),
    "patrimonio_liquido": (
        "Patrimônio líquido — PL",
        "Diferença contábil entre ativos e obrigações com terceiros; inclui capital e resultados acumulados.",
        "Não é o valor das ações na bolsa nem dinheiro disponível para saque.",
        "Ativos de R$ 100 menos obrigações de R$ 40 deixam PL de R$ 60.",
    ),
    "passivo_exigivel": (
        "Passivo exigível",
        "Soma das obrigações do passivo circulante e não circulante, excluindo o patrimônio líquido.",
        "É mais amplo que dívida financeira: inclui fornecedores e outras obrigações.",
        "PC de R$ 30 mais PNC de R$ 10 resultam em R$ 40 de passivo exigível.",
    ),
    "liquidez_corrente": (
        "Liquidez corrente",
        "Compara o ativo circulante com as obrigações de curto prazo.",
        "Acima de 1 não garante capacidade de pagamento: prazo e qualidade dos ativos também importam.",
        "Índice de 0,96 significa R$ 0,96 de ativos circulantes para cada R$ 1 de obrigação de curto prazo.",
    ),
    "liquidez_seca": (
        "Liquidez seca",
        "Compara o ativo circulante, descontados os estoques, com o passivo circulante.",
        "Mesmo sem estoques, a base ainda contém direitos a receber; não mede só o dinheiro em caixa.",
        "Índice de 0,73 representa R$ 0,73 na base sem estoques para cada R$ 1 de obrigação de curto prazo.",
    ),
    "margem_bruta": (
        "Margem bruta",
        "Mostra quanto da receita sobra após o custo dos produtos vendidos.",
        "Não considera todas as despesas; uma margem maior, isoladamente, não prova melhora do negócio.",
        "Margem bruta de 40% significa R$ 40 de lucro bruto para cada R$ 100 de receita líquida.",
    ),
    "margem_operacional": (
        "Margem operacional — CVM",
        "Parcela da receita representada pelo resultado operacional CVM.",
        "Inclui equivalência patrimonial neste projeto; compare sempre o mesmo conceito de EBIT.",
        "Margem operacional de 25% corresponde a R$ 25 de EBIT CVM para cada R$ 100 de receita.",
    ),
    "margem_liquida": (
        "Margem líquida",
        "Mostra quanto da receita se transforma em lucro líquido consolidado.",
        "Pode variar por efeitos financeiros e tributários, além da operação.",
        "Margem líquida de 18% significa aproximadamente R$ 18 de lucro para cada R$ 100 de receita líquida.",
    ),
    "roa": (
        "ROA — retorno sobre os ativos",
        "Compara o lucro anual com o ativo total de encerramento.",
        "Usa saldo final, não médio. Não mede o retorno recebido por um investidor.",
        "ROA de 10% corresponde a R$ 10 de lucro anual para cada R$ 100 de ativos finais.",
    ),
    "roe": (
        "ROE — retorno sobre o patrimônio",
        "Compara o lucro anual consolidado com o patrimônio líquido consolidado de encerramento.",
        "Não representa a rentabilidade das ações na bolsa. PL baixo ou negativo pode distorcer a interpretação.",
        "ROE de 18% corresponde a R$ 18 de lucro anual para cada R$ 100 de patrimônio líquido final.",
    ),
    "endividamento_geral": (
        "Endividamento geral",
        "Parcela dos ativos financiada por obrigações com terceiros, excluindo o patrimônio líquido.",
        "Inclui fornecedores e outras obrigações, além de empréstimos. Menor não é automaticamente melhor.",
        "Endividamento de 40% significa R$ 40 de obrigações com terceiros para cada R$ 100 de ativos.",
    ),
    "capital_terceiros_patrimonio": (
        "Capital de terceiros / PL",
        "Compara as obrigações com terceiros com o patrimônio líquido.",
        "Pode ultrapassar 100%. PL pequeno ou negativo exige cuidado; não é a mesma base do endividamento geral.",
        "Índice de 60% corresponde a R$ 60 de obrigações para cada R$ 100 de PL.",
    ),
    "divida_liquida": (
        "Dívida líquida",
        "Compara dívida financeira com caixa; a definição de aplicações incluídas deve ser informada.",
        "Não disponível aqui: o pipeline não extrai dívida financeira. Passivo exigível não substitui essa dívida.",
        "Em uma definição que desconta caixa, dívida de R$ 50 menos caixa de R$ 20 resulta em R$ 30.",
    ),
    "divida_liquida_ebitda": (
        "Dívida líquida / EBITDA",
        "Compara a dívida líquida com uma medida de resultado antes de juros, tributos, depreciação e amortização.",
        "Não disponível aqui: dívida financeira e EBITDA normalizado não são extraídos. Não é um prazo garantido para quitar a dívida.",
        "Razão de 2 vezes não significa que a dívida necessariamente será paga em dois anos.",
    ),
}

for _campo in ("receita_liquida", "lucro_liquido", "lucro_bruto", "ativo_total", "patrimonio_liquido"):
    _rotulo = config.NOMES[_campo].lower()
    GLOSSARIO[f"crescimento_{_campo}"] = (
        f"Variação anual — {_rotulo}",
        f"Mostra quanto {_rotulo} mudou contra o ano calendário anterior.",
        "Usa (atual − anterior) / valor absoluto do anterior. Sem par anual válido ou com base zero, fica n/d; a variação é nominal, sem descontar inflação.",
        "Passar de R$ 100 para R$ 110 representa aumento de 10%. Não confunda porcentagem com pontos percentuais.",
    )

EXPLICACOES_GRAFICOS = {
    "geral": "Receita é o valor vendido após deduções; lucro é o resultado que sobra após custos e despesas. Compare a evolução das séries, sem tratar receita como lucro ou caixa.",
    "cascata": "Leia da esquerda para a direita: as barras mostram como receita, custos, despesas, resultado financeiro e tributos chegam ao lucro. Bruto, EBIT e líquido são subtotais, não receitas adicionais.",
    "vertical": "Cada barra compara uma conta com R$ 100 de receita do mesmo ano. Custos aparecem negativos; lucro bruto, EBIT e lucro líquido são etapas sobrepostas e não devem ser somados.",
    "margens": "Uma margem de 18% representa R$ 18 de resultado para cada R$ 100 de receita. Bruta, operacional e líquida descontam grupos diferentes de custos e despesas.",
    "retornos": "ROA compara lucro com ativos; ROE compara lucro com patrimônio líquido. Ambos usam saldos finais neste projeto e não medem o ganho de quem comprou ações.",
    "liquidez": "A linha de 1,0 indica R$ 1 de ativos na base para cada R$ 1 de obrigação de curto prazo. Na liquidez seca, os estoques são descontados. Acima de 1 não garante pagamento; abaixo de 1 não prova insolvência.",
    "endividamento": "Endividamento geral usa os ativos como base; capital de terceiros / PL usa o patrimônio líquido. Ambos incluem obrigações além de empréstimos. Menor endividamento, isoladamente, não significa melhor desempenho.",
    "balanco": "A altura total representa os ativos. As partes mostram seu financiamento: obrigações de curto prazo, de longo prazo e patrimônio líquido. Patrimônio líquido não é uma dívida bancária.",
    "comparacao": "A tabela compara os dois extremos selecionados. Mudanças em margens e retornos são pontos percentuais: passar de 18% para 20% significa +2 p.p., não +2%.",
    "horizontal": "Cada barra mostra a mudança contra o ano calendário anterior, mesmo se ele estiver oculto pelo filtro. Aumento ou redução descreve a direção; o contexto define se isso é favorável.",
}


def ajuda_indicador(nome: str) -> str:
    """Texto curto para o ícone de ajuda, com definição, cuidado e fórmula técnica."""
    _, significado, cuidado, _ = GLOSSARIO[nome]
    formula = config.FORMULAS.get(nome)
    return f"{significado} {cuidado}" + (f" Fórmula: {formula}" if formula else "")

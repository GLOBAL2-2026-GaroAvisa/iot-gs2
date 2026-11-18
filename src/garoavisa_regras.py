import json
import random
import re

import requests

CAMPOS_DIA = [
    "temperature_2m_max",
    "temperature_2m_min",
    "uv_index_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_gusts_10m_max",
]
CAMPOS_HORA = ["relative_humidity_2m", "precipitation"]

LIMITES = {
    "chuva_prob": 60,
    "calor": 30,
    "uv": 8,
    "vento": 50,
    "frio": 14,
    "amplitude": 10,
    "umidade": 30,
    "seca_mm": 1,
    "seca_dias": 5,
    "mudanca_temp": 4,
    "mudanca_chuva": 30,
}

FAIXAS = {"CHUVA": (5, 10), "CALOR": (30, 35), "UV": (8, 11), "VENTO": (50, 75)}

ORDEM = ["CHUVA", "CALOR", "UV", "VENTO", "FRIO", "AMPLITUDE", "UMIDADE", "SECA"]
PESO = {"ALTA": 0, "MEDIA": 1, "BAIXA": 2}
NIVEL_TEXTO = {"ALTA": "alto", "MEDIA": "médio", "BAIXA": "baixo"}

CAMPOS_NUMERICOS = ["tmax", "tmin", "uv", "chuva_prob", "chuva_mm_h", "vento", "umid_min"]
OBRIGATORIOS_DIA = CAMPOS_NUMERICOS + ["semana_seca"]
OBRIGATORIOS_MUDANCA = ["nome", "tmax_antes", "chuva_antes", "tmax_agora", "chuva_agora"]

FIM = " [FIM]"
NUMEROS_FIXOS = {10.0, 16.0}
MSG_INDISPONIVEL = "Previsão indisponível no momento. Tente novamente mais tarde."

LOCAIS_TESTE = {
    "Tatuapé (São Paulo)": (-23.54, -46.576),
    "Bela Vista (São Paulo)": (-23.5614, -46.6559),
    "Centro (Guarulhos)": (-23.4543, -46.5333),
    "Copacabana (Rio de Janeiro)": (-22.9711, -43.1822),
    "Gonzaga (Santos)": (-23.968, -46.333),
}

COMPROMISSOS = [
    "Reunião de equipe",
    "Aula de Banco de Dados",
    "Consulta médica",
    "Dia de praia",
    "Churrasco em família",
    "Apresentação de Projeto",
    "Corrida no parque",
    "Passeio no parque",
    "Jogo de futebol",
    "Feira de domingo",
    "Casamento",
    "Show ao ar livre",
]

INTROS = [
    "Hoje a máxima será de {tmax}°C e a mínima de {tmin}°C.",
    "A previsão de hoje é de máxima de {tmax}°C e mínima de {tmin}°C.",
]

SEM_ALERTA = ["Não há alertas para hoje.", "Dia tranquilo, sem alertas."]

DICA_NEUTRA = [
    "Dica do dia: aproveite o dia com tranquilidade.",
    "Dica do dia: beba água ao longo do dia.",
]

FRASES = {
    "CHUVA": [
        "Alerta de chuva (nível {nivel}): {chuva_prob}% de chance, com até {chuva_mm_h} mm/h.",
        "Chuva prevista, nível {nivel}: {chuva_prob}% de chance e até {chuva_mm_h} mm/h.",
    ],
    "CALOR": [
        "Alerta de calor (nível {nivel}): máxima de {tmax}°C.",
        "Calor previsto, nível {nivel}, com máxima de {tmax}°C.",
    ],
    "UV": [
        "Alerta de UV (nível {nivel}): índice máximo de {uv}.",
        "Radiação UV em nível {nivel}, com índice máximo de {uv}.",
    ],
    "VENTO": [
        "Alerta de vento (nível {nivel}): rajadas de até {vento} km/h.",
        "Vento forte previsto, nível {nivel}, com rajadas de até {vento} km/h.",
    ],
    "FRIO": [
        "Alerta de frio (nível {nivel}): mínima de {tmin}°C.",
        "Manhã fria, nível {nivel}, com mínima de {tmin}°C.",
    ],
    "AMPLITUDE": [
        "Alerta de amplitude térmica (nível {nivel}): {tmin}°C de manhã e {tmax}°C à tarde.",
        "A temperatura muda muito no dia, nível {nivel}: de {tmin}°C a {tmax}°C.",
    ],
    "UMIDADE": [
        "Alerta de ar seco (nível {nivel}): umidade em {umid_min}%.",
        "Umidade baixa, nível {nivel}: {umid_min}% à tarde.",
    ],
    "SECA": [
        "Alerta de seca (nível {nivel}): semana com pouca chuva.",
        "Semana sem chuva prevista, nível {nivel}.",
    ],
}

DICAS = {
    "CHUVA": "leve guarda-chuva.",
    "CALOR": "leve garrafa de água e use roupa leve.",
    "UV": "use protetor solar e óculos e evite o sol das 10h às 16h.",
    "VENTO": "cuidado com árvores, placas e fios, e não estacione embaixo de árvores.",
    "FRIO": "leve um casaco.",
    "AMPLITUDE": "saia com casaco na mochila.",
    "UMIDADE": "beba bastante água e evite exercício ao ar livre à tarde.",
    "SECA": "economize água e regue as plantas à noite, pois há risco de queimadas.",
}

PALAVRAS_CHAVE = {
    "CHUVA": ["chuva"],
    "CALOR": ["calor"],
    "UV": ["uv"],
    "VENTO": ["vento"],
    "FRIO": ["frio", "fria"],
    "AMPLITUDE": ["amplitude", "muda muito"],
    "UMIDADE": ["ar seco", "umidade"],
    "SECA": ["seca", "sem chuva"],
}

PREFIXOS_MUDANCA = [
    "A previsão para {nome} mudou: ",
    "Atenção, o clima de {nome} mudou: ",
]

SEM_MUDANCA = [
    "A previsão para {nome} não mudou muito: máxima de {tmax_agora}°C e chuva de {chuva_agora}%.",
    "O clima de {nome} segue parecido: máxima de {tmax_agora}°C e chuva de {chuva_agora}%. A previsão não mudou muito.",
]


def _n(valor):
    return f"{round(float(valor), 1):g}"


def _inteiro(valor):
    return None if valor is None else round(valor)


def _escolher(opcoes, rng):
    return opcoes[rng.randrange(len(opcoes))] if rng else opcoes[0]


def conferir(dados, campos):
    faltando = [c for c in campos if dados.get(c) is None]
    if faltando:
        raise ValueError(f"campos ausentes: {faltando}")


def gravidade(tipo, valor):
    if tipo not in FAIXAS:
        return "BAIXA"
    media, alta = FAIXAS[tipo]
    if valor >= alta:
        return "ALTA"
    if valor >= media:
        return "MEDIA"
    return "BAIXA"


def gerar_alertas(dia):
    alertas = []
    if dia["chuva_prob"] >= LIMITES["chuva_prob"]:
        alertas.append({"tipo": "CHUVA", "gravidade": gravidade("CHUVA", dia["chuva_mm_h"])})
    if dia["tmax"] >= LIMITES["calor"]:
        alertas.append({"tipo": "CALOR", "gravidade": gravidade("CALOR", dia["tmax"])})
    if dia["uv"] >= LIMITES["uv"]:
        alertas.append({"tipo": "UV", "gravidade": gravidade("UV", dia["uv"])})
    if dia["vento"] >= LIMITES["vento"]:
        alertas.append({"tipo": "VENTO", "gravidade": gravidade("VENTO", dia["vento"])})
    if dia["tmin"] <= LIMITES["frio"]:
        alertas.append({"tipo": "FRIO", "gravidade": "BAIXA"})
    if dia["tmax"] - dia["tmin"] >= LIMITES["amplitude"]:
        alertas.append({"tipo": "AMPLITUDE", "gravidade": "BAIXA"})
    if dia["umid_min"] < LIMITES["umidade"]:
        alertas.append({"tipo": "UMIDADE", "gravidade": "BAIXA"})
    if dia["semana_seca"]:
        alertas.append({"tipo": "SECA", "gravidade": "BAIXA"})
    return alertas


def principais(alertas, quantidade=3):
    ordenados = sorted(alertas, key=lambda a: (PESO[a["gravidade"]], ORDEM.index(a["tipo"])))
    return ordenados[:quantidade]


def mudancas(dados):
    lista = []
    dif_chuva = dados["chuva_agora"] - dados["chuva_antes"]
    dif_temp = dados["tmax_agora"] - dados["tmax_antes"]
    if dif_chuva >= LIMITES["mudanca_chuva"]:
        lista.append("CHUVA SUBIU")
    elif dif_chuva <= -LIMITES["mudanca_chuva"]:
        lista.append("CHUVA CAIU")
    if dif_temp >= LIMITES["mudanca_temp"]:
        lista.append("TEMPERATURA SUBIU")
    elif dif_temp <= -LIMITES["mudanca_temp"]:
        lista.append("TEMPERATURA CAIU")
    return lista


def mudou(dados):
    return len(mudancas(dados)) > 0


def pergunta_dia(dia):
    conferir(dia, OBRIGATORIOS_DIA)
    lista = ", ".join(f"{a['tipo']} {a['gravidade']}" for a in principais(gerar_alertas(dia)))
    seca = "sim" if dia["semana_seca"] else "não"
    return (
        f"Resuma o dia. Máxima {_n(dia['tmax'])}, mínima {_n(dia['tmin'])}, UV {_n(dia['uv'])}, "
        f"chuva {_n(dia['chuva_prob'])}% com {_n(dia['chuva_mm_h'])} mm/h, "
        f"vento {_n(dia['vento'])} km/h, umidade {_n(dia['umid_min'])}%, semana seca {seca}. "
        f"Alertas: {lista or 'nenhum'}."
    )


def pergunta_mudanca(dados):
    conferir(dados, OBRIGATORIOS_MUDANCA)
    return (
        f"O compromisso {dados['nome']} mudou? "
        f"Antes: máxima {_n(dados['tmax_antes'])}°C e chuva {_n(dados['chuva_antes'])}%. "
        f"Agora: máxima {_n(dados['tmax_agora'])}°C e chuva {_n(dados['chuva_agora'])}%. "
        f"Mudanças: {', '.join(mudancas(dados)) or 'nenhuma'}."
    )


def resposta_dia(dia, rng=None):
    valores = {k: _n(dia[k]) for k in CAMPOS_NUMERICOS}
    alertas = principais(gerar_alertas(dia))
    partes = [_escolher(INTROS, rng).format(**valores)]
    if not alertas:
        partes.append(_escolher(SEM_ALERTA, rng))
        partes.append(_escolher(DICA_NEUTRA, rng))
    else:
        for alerta in alertas:
            frase = _escolher(FRASES[alerta["tipo"]], rng)
            partes.append(frase.format(nivel=NIVEL_TEXTO[alerta["gravidade"]], **valores))
        partes.append("Dica do dia: " + DICAS[alertas[0]["tipo"]])
    return " ".join(partes)


def resposta_mudanca(dados, rng=None):
    v = {k: (dados[k] if k == "nome" else _n(dados[k])) for k in OBRIGATORIOS_MUDANCA}
    flags = mudancas(dados)
    if not flags:
        return _escolher(SEM_MUDANCA, rng).format(**v)
    partes = []
    dica = None
    if "CHUVA SUBIU" in flags:
        partes.append(f"a chance de chuva subiu de {v['chuva_antes']}% para {v['chuva_agora']}%")
        dica = "Leve guarda-chuva ou reveja o plano."
    if "CHUVA CAIU" in flags:
        partes.append(f"a chance de chuva caiu de {v['chuva_antes']}% para {v['chuva_agora']}%")
        dica = "Boa notícia para o seu compromisso."
    if "TEMPERATURA CAIU" in flags:
        partes.append(f"a máxima caiu de {v['tmax_antes']}°C para {v['tmax_agora']}°C")
        dica = dica or "Leve um casaco."
    if "TEMPERATURA SUBIU" in flags:
        partes.append(f"a máxima subiu de {v['tmax_antes']}°C para {v['tmax_agora']}°C")
        dica = dica or "Leve água e use roupa leve."
    prefixo = _escolher(PREFIXOS_MUDANCA, rng).format(nome=v["nome"])
    return f"{prefixo}{' e '.join(partes)}. {dica}"


PERGUNTAS = {"dia": pergunta_dia, "mudanca": pergunta_mudanca}
RESPOSTAS = {"dia": resposta_dia, "mudanca": resposta_mudanca}


def _limitar(valor, minimo, maximo):
    return max(minimo, min(maximo, round(valor)))


def sortear_dia(rng):
    if rng.random() < 0.6:
        tmax = _limitar(rng.gauss(27, 6), 12, 40)
        tmin = max(2, tmax - rng.randint(4, 13))
        uv = _limitar(rng.gauss(6, 3.5), 0, 13)
        chuva_prob = rng.randint(0, 40) if rng.random() < 0.5 else rng.randint(41, 100)
        vento = _limitar(rng.gauss(30, 15), 5, 90)
        umid_min = _limitar(rng.gauss(50, 20), 12, 95)
    else:
        tmax = rng.randint(12, 40)
        tmin = max(2, tmax - rng.randint(4, 16))
        uv = rng.randint(0, 13)
        chuva_prob = rng.randint(0, 100)
        vento = rng.randint(5, 90)
        umid_min = rng.randint(12, 95)
    limite_chuva = 15 if chuva_prob >= 40 else 2
    return {
        "tmax": tmax,
        "tmin": tmin,
        "uv": uv,
        "chuva_prob": chuva_prob,
        "chuva_mm_h": round(rng.uniform(0, limite_chuva), 1),
        "vento": vento,
        "umid_min": umid_min,
        "semana_seca": rng.random() < 0.15,
    }


def sortear_mudanca(rng):
    tmax_antes = rng.randint(15, 38)
    chuva_antes = rng.randint(0, 90)
    if rng.random() < 0.7:
        dif_temp = rng.randint(4, 10) * rng.choice([-1, 1]) if rng.random() < 0.6 else rng.randint(-3, 3)
        if rng.random() < 0.6 or abs(dif_temp) < 4:
            dif_chuva = rng.randint(30, 70) * rng.choice([-1, 1])
        else:
            dif_chuva = rng.randint(-25, 25)
    else:
        dif_temp = rng.randint(-3, 3)
        dif_chuva = rng.randint(-25, 25)
    return {
        "nome": rng.choice(COMPROMISSOS),
        "tmax_antes": tmax_antes,
        "chuva_antes": chuva_antes,
        "tmax_agora": min(42, max(5, tmax_antes + dif_temp)),
        "chuva_agora": min(100, max(0, chuva_antes + dif_chuva)),
    }


def gerar_dataset(quantidade=1700, semente=42, proporcao_dia=0.7):
    rng = random.Random(semente)
    itens = []
    vistos = set()
    while len(itens) < quantidade:
        tarefa = "dia" if rng.random() < proporcao_dia else "mudanca"
        dados = sortear_dia(rng) if tarefa == "dia" else sortear_mudanca(rng)
        pergunta = PERGUNTAS[tarefa](dados)
        if pergunta in vistos:
            continue
        vistos.add(pergunta)
        itens.append(
            {
                "question": pergunta,
                "answer": RESPOSTAS[tarefa](dados, rng),
                "tarefa": tarefa,
                "dados": dados,
            }
        )
    return itens


def salvar_dataset(itens, caminho):
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(itens, arquivo, ensure_ascii=False, indent=1)


def url_previsao(latitude, longitude, dias=7):
    return (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&daily={','.join(CAMPOS_DIA)}"
        f"&hourly={','.join(CAMPOS_HORA)}"
        f"&timezone=auto&forecast_days={dias}"
    )


def buscar_previsao(latitude, longitude, dias=7):
    resposta = requests.get(url_previsao(latitude, longitude, dias), timeout=15)
    resposta.raise_for_status()
    return resposta.json()


def extrair_dias(previsao):
    diario = previsao["daily"]
    horario = previsao["hourly"]
    secos = sum(
        1 for p in diario["precipitation_sum"] if p is not None and p < LIMITES["seca_mm"]
    )
    dias = []
    for i, data in enumerate(diario["time"]):
        faixa = slice(i * 24, (i + 1) * 24)
        umidades = [v for v in horario["relative_humidity_2m"][faixa] if v is not None]
        chuvas = [v for v in horario["precipitation"][faixa] if v is not None]
        dias.append(
            {
                "data": data,
                "tmax": _inteiro(diario["temperature_2m_max"][i]),
                "tmin": _inteiro(diario["temperature_2m_min"][i]),
                "uv": _inteiro(diario["uv_index_max"][i]),
                "chuva_prob": _inteiro(diario["precipitation_probability_max"][i]),
                "chuva_mm_h": round(max(chuvas), 1) if chuvas else None,
                "vento": _inteiro(diario["wind_gusts_10m_max"][i]),
                "umid_min": round(min(umidades)) if umidades else None,
                "semana_seca": i == 0 and secos >= LIMITES["seca_dias"],
            }
        )
    return dias


def _frases(texto):
    partes = re.split(r"(?<=\.)\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", texto.strip())
    return [p.strip() for p in partes if p.strip()]


def limpar_resposta(texto_gerado):
    try:
        resposta = texto_gerado.split("Resposta:")[1]
    except IndexError:
        return ""
    if "[FIM]" not in resposta:
        return ""
    return resposta.split("[FIM]")[0].strip()


def _numeros(texto):
    return {float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", texto)}


class _Fixo:
    def __init__(self, indice):
        self.indice = indice

    def randrange(self, quantidade):
        return self.indice % quantidade


def frases_permitidas(tarefa, dados):
    permitidas = set()
    for indice in (0, 1):
        permitidas.update(_frases(RESPOSTAS[tarefa](dados, _Fixo(indice))))
    return permitidas


def validar(tarefa, dados, pergunta, texto):
    motivos = []
    if len(texto) < 20:
        motivos.append("texto vazio ou curto")
    inventados = _numeros(texto) - (_numeros(pergunta) | NUMEROS_FIXOS)
    if inventados:
        motivos.append(f"números que não estavam nos dados: {sorted(inventados)}")
    minusculo = texto.lower()
    if tarefa == "dia":
        alertas = principais(gerar_alertas(dados))
        for alerta in alertas:
            if not any(re.search(r"\b" + re.escape(p), minusculo) for p in PALAVRAS_CHAVE[alerta["tipo"]]):
                motivos.append(f"alerta {alerta['tipo']} não foi explicado")
        if not alertas and "alerta" not in minusculo:
            motivos.append("não informou que não há alertas")
        if "dica do dia" not in minusculo:
            motivos.append("sem dica do dia")
    else:
        if dados["nome"].lower() not in minusculo:
            motivos.append("compromisso não citado")
        if mudou(dados) and "não mudou" in minusculo:
            motivos.append("disse que não mudou, mas mudou")
        if mudou(dados) and "mudou" not in minusculo:
            motivos.append("não avisou a mudança")
        if not mudou(dados) and "não mudou" not in minusculo:
            motivos.append("não informou que a previsão se manteve")
    permitidas = frases_permitidas(tarefa, dados)
    frases = _frases(texto)
    for frase in frases:
        if frase not in permitidas:
            motivos.append(f"frase fora do esperado: {frase}")
    esperadas = {len(_frases(RESPOSTAS[tarefa](dados, _Fixo(i)))) for i in (0, 1)}
    if len(frases) not in esperadas:
        motivos.append(f"quantidade de frases diferente do esperado: {len(frases)}")
    return len(motivos) == 0, motivos


def explicar(tarefa, dados, gerar):
    try:
        pergunta = PERGUNTAS[tarefa](dados)
    except (KeyError, TypeError, ValueError) as erro:
        return {"texto": MSG_INDISPONIVEL, "origem": "indisponivel", "motivos": [str(erro)]}
    texto = gerar(pergunta)
    valido, motivos = validar(tarefa, dados, pergunta, texto)
    if valido:
        return {"texto": texto, "origem": "ia", "motivos": []}
    return {"texto": RESPOSTAS[tarefa](dados), "origem": "regra", "motivos": motivos}

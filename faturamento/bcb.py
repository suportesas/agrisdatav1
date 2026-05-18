"""
Integração com a API PTAX do Banco Central do Brasil (BCB).
Documentação: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/swagger-ui3

Regra de negócio: para faturamento de exportação, utilizar a cotação
de FECHAMENTO (PTAX) do último dia útil anterior à emissão do documento.
"""
import requests
from datetime import date, timedelta
from decimal import Decimal

BCB_BASE = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
TIMEOUT = 12  # segundos


def _recuar_para_dia_util(d: date) -> date:
    """Recua 'd' até o dia útil mais próximo (pula sábado e domingo)."""
    while d.weekday() >= 5:  # 5=sáb, 6=dom
        d -= timedelta(days=1)
    return d


def _dia_util_anterior(referencia: date | None = None) -> date:
    """Retorna o último dia útil ANTES de 'referencia' (padrão: hoje)."""
    base = (referencia or date.today()) - timedelta(days=1)
    return _recuar_para_dia_util(base)


def _buscar_dolar(d: date) -> dict | None:
    """Busca cotação PTAX do Dólar (USD) para a data 'd'."""
    data_str = d.strftime('%m-%d-%Y')  # BCB usa MM-DD-YYYY
    url = (
        f"{BCB_BASE}/CotacaoDolarDia(dataCotacao=@dataCotacao)"
        f"?@dataCotacao='{data_str}'"
        f"&$top=1&$orderby=dataHoraCotacao%20desc"
        f"&$format=json&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao"
    )
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    values = resp.json().get('value', [])
    if not values:
        return None
    v = values[0]
    return {
        'compra': Decimal(str(v['cotacaoCompra'])).quantize(Decimal('0.0001')),
        'venda': Decimal(str(v['cotacaoVenda'])).quantize(Decimal('0.0001')),
        'dataHora': v.get('dataHoraCotacao', ''),
    }


def _buscar_moeda(moeda: str, d: date) -> dict | None:
    """Busca cotação PTAX de qualquer moeda (EUR, GBP…) para a data 'd'."""
    data_str = d.strftime('%m-%d-%Y')
    url = (
        f"{BCB_BASE}/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
        f"?@moeda='{moeda}'&@dataCotacao='{data_str}'"
        f"&$top=1&$orderby=dataHoraCotacao%20desc"
        f"&$format=json&$select=cotacaoCompra,cotacaoVenda,dataHoraCotacao"
    )
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    values = resp.json().get('value', [])
    if not values:
        return None
    v = values[0]
    return {
        'compra': Decimal(str(v['cotacaoCompra'])).quantize(Decimal('0.0001')),
        'venda': Decimal(str(v['cotacaoVenda'])).quantize(Decimal('0.0001')),
        'dataHora': v.get('dataHoraCotacao', ''),
    }


def buscar_cotacoes(moedas: list[str] | None = None, referencia: date | None = None) -> dict:
    """
    Busca as cotações PTAX do BCB para o último dia útil anterior.

    Parâmetros:
        moedas    — lista de códigos ISO (padrão: ['USD', 'EUR', 'GBP'])
        referencia — data base (padrão: hoje); o resultado será do dia útil ANTERIOR

    Retorno:
        {
            'data': '16/05/2026',
            'data_iso': '2026-05-16',
            'cotacoes': {
                'USD': {'compra': Decimal('5.1234'), 'venda': Decimal('5.1456'), 'dataHora': '...'},
                'EUR': {...},
            }
        }

    Tenta até 5 dias consecutivos para cobrir feriados brasileiros.
    """
    if moedas is None:
        moedas = ['USD', 'EUR', 'GBP']

    # Começa do dia útil anterior e tenta até 5 dias atrás (para feriados)
    d = _dia_util_anterior(referencia)
    data_ref = None
    cotacoes = {}

    for _ in range(5):
        try:
            if 'USD' in moedas:
                usd = _buscar_dolar(d)
                if usd:
                    data_ref = d
                    cotacoes['USD'] = usd
                    break
            else:
                # usa outra moeda como âncora
                primeira = moedas[0]
                c = _buscar_moeda(primeira, d)
                if c:
                    data_ref = d
                    cotacoes[primeira] = c
                    break
        except requests.RequestException:
            pass
        d -= timedelta(days=1)
        d = _recuar_para_dia_util(d)

    if not data_ref:
        raise RuntimeError("Não foi possível obter cotações do BCB para os últimos 5 dias úteis.")

    # Busca as demais moedas para a data encontrada
    for moeda in moedas:
        if moeda in cotacoes:
            continue
        try:
            if moeda == 'USD':
                c = _buscar_dolar(data_ref)
            else:
                c = _buscar_moeda(moeda, data_ref)
            if c:
                cotacoes[moeda] = c
        except requests.RequestException:
            pass  # moeda indisponível — continua sem ela

    return {
        'data': data_ref.strftime('%d/%m/%Y'),
        'data_iso': data_ref.isoformat(),
        'cotacoes': cotacoes,
    }

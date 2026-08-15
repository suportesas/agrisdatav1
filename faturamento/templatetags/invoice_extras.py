from decimal import Decimal, ROUND_DOWN

from django import template

register = template.Library()

_ONES = [
    '', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE',
    'TEN', 'ELEVEN', 'TWELVE', 'THIRTEEN', 'FOURTEEN', 'FIFTEEN', 'SIXTEEN',
    'SEVENTEEN', 'EIGHTEEN', 'NINETEEN',
]
_TENS = [
    '', '', 'TWENTY', 'THIRTY', 'FORTY', 'FIFTY', 'SIXTY', 'SEVENTY', 'EIGHTY', 'NINETY',
]
_SCALES = ['', 'THOUSAND', 'MILLION', 'BILLION', 'TRILLION']

_CURRENCY_UNITS = {
    'USD': ('DOLLAR', 'DOLLARS', 'CENT', 'CENTS'),
    'EUR': ('EURO', 'EUROS', 'CENT', 'CENTS'),
    'GBP': ('POUND', 'POUNDS', 'PENNY', 'PENCE'),
    'BRL': ('BRAZILIAN REAL', 'BRAZILIAN REAIS', 'CENTAVO', 'CENTAVOS'),
}


def _three_digits_to_words(n):
    words = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        words.append(f'{_ONES[hundreds]} HUNDRED')
    if rest:
        if words:
            words.append('AND')
        if rest < 20:
            words.append(_ONES[rest])
        else:
            tens, ones = divmod(rest, 10)
            word = _TENS[tens]
            if ones:
                word += f'-{_ONES[ones]}'
            words.append(word)
    return ' '.join(words)


def _integer_to_words(n):
    if n == 0:
        return 'ZERO'
    groups = []
    while n > 0:
        n, rem = divmod(n, 1000)
        groups.append(rem)
    parts = []
    for i in range(len(groups) - 1, -1, -1):
        if groups[i] == 0:
            continue
        chunk = _three_digits_to_words(groups[i])
        if _SCALES[i]:
            chunk += f' {_SCALES[i]}'
        parts.append(chunk)
    return ' '.join(parts)


@register.filter
def amount_in_words(value, currency='USD'):
    """Spells out a decimal monetary value in English, e.g. 'TEN THOUSAND NINE
    HUNDRED AND SEVEN EUROS AND FORTY CENTS ONLY.' Presentation-only helper —
    does not affect any stored/calculated invoice value."""
    if value is None:
        return ''
    value = Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    unit_sg, unit_pl, cent_sg, cent_pl = _CURRENCY_UNITS.get(currency, _CURRENCY_UNITS['USD'])

    whole = int(value)
    cents = int((value - whole) * 100)

    whole_words = _integer_to_words(whole)
    whole_unit = unit_sg if whole == 1 else unit_pl
    result = f'{whole_words} {whole_unit}'

    if cents:
        cents_words = _integer_to_words(cents)
        cents_unit = cent_sg if cents == 1 else cent_pl
        result += f' AND {cents_words} {cents_unit}'

    return f'{result} ONLY.'

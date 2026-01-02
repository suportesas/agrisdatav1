import re
from django.core.exceptions import ValidationError

# Simplified IE regex per UF. Real-world rules are complex; extend as needed.
IE_REGEX_BY_UF = {
    'SP': r'^\d{12}$',    # São Paulo (12 dígitos, simplificado)
    'MG': r'^\d{13}$',    # Minas Gerais (13 dígitos, simplificado)
    'RJ': r'^\d{8}$',     # Rio de Janeiro (8 dígitos, simplificado)
    'BA': r'^\d{8,9}$',   # Bahia (8 ou 9 dígitos)
    'PR': r'^\d{10}$',    # Paraná (10 dígitos)
    # Adicione mais estados conforme necessário
}

GENERIC_IE_REGEX = r'^\d{3,14}$'  # fallback: entre 3 e 14 dígitos


def validate_inscricao_estadual(inscricao, uf=None, is_contribuinte=False, tipo_pessoa='PJ'):
    """Valida a Inscrição Estadual.

    - Aceita 'ISENTO' (case-insensitive) para não contribuintes.
    - Se for contribuinte_icms=True, 'ISENTO' NÃO é aceito e deve haver um número válido.
    - Se houver UF (sigla), aplica regex específico; caso contrário usa regex genérico.
    """
    if not inscricao:
        return True

    inscricao_raw = (inscricao or '').strip()
    if not inscricao_raw:
        return True

    if inscricao_raw.upper() == 'ISENTO':
        if is_contribuinte:
            raise ValidationError('Inscrição Estadual inválida: contribuinte ICMS não pode ser ISENTO.')
        return True

    # Remove pontos/traços e espaços
    inscr = re.sub(r'\D', '', inscricao_raw)
    # Skip Brazilian IE checks for exterior
    if uf and uf.upper() == 'EX':
        return True

    if uf and uf.upper() in IE_REGEX_BY_UF:
        pattern = IE_REGEX_BY_UF[uf.upper()]
    else:
        pattern = GENERIC_IE_REGEX

    if not re.match(pattern, inscr):
        if uf:
            raise ValidationError(f'Inscrição Estadual inválida para UF {uf}.')
        else:
            raise ValidationError('Inscrição Estadual inválida.')

    return True

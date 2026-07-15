"""Helpers compartilhados entre o backfill de login e a tela de definir PIN do motorista."""
import re

USERNAME_MAX_LENGTH = 150


def normalizar_matricula(matricula):
    normalizado = matricula.strip().lower()
    normalizado = re.sub(r'[^a-z0-9_-]+', '-', normalizado)
    normalizado = re.sub(r'-{2,}', '-', normalizado).strip('-')
    return normalizado


def gerar_username_motorista(empresa_id, matricula):
    """Gera um username namespaced por empresa para evitar colisão entre matrículas
    iguais em empresas diferentes (Motorista.matricula não é único globalmente)."""
    prefixo = f'mot{empresa_id}.'
    matricula_normalizada = normalizar_matricula(matricula)
    limite = USERNAME_MAX_LENGTH - len(prefixo)
    return f'{prefixo}{matricula_normalizada[:limite]}'

"""Helpers compartilhados entre o backfill de login e a tela de definir PIN do funcionário."""
import re

USERNAME_MAX_LENGTH = 150


def gerar_username_funcionario(empresa_id, cpf):
    """Gera um username namespaced por empresa a partir do CPF.
    Funcionario.cpf já é único globalmente, mas mantemos o prefixo por empresa
    para seguir a mesma convenção usada em gerar_username_motorista()."""
    prefixo = f'func{empresa_id}.'
    digitos = re.sub(r'\D', '', cpf or '')
    limite = USERNAME_MAX_LENGTH - len(prefixo)
    return f'{prefixo}{digitos[:limite]}'

# coding: utf-8
"""
Seed de Categorias de Produto padrão para novas empresas.
"""
from produtos.models import Categoria

DEFAULT_CATEGORIAS = [
    {"codigo": "DEF", "nome": "Defensivo Agrícola", "descricao": "Produtos defensivos para uso agrícola."},
    {"codigo": "FERT", "nome": "Fertilizante", "descricao": "Fertilizantes e adubos."},
    {"codigo": "SEM", "nome": "Semente", "descricao": "Sementes para plantio."},
    {"codigo": "ADUBO", "nome": "Adubo", "descricao": "Adubos em geral."},
    {"codigo": "CORR", "nome": "Corretivo de Solo", "descricao": "Produtos para correção de solo."},
    {"codigo": "INOC", "nome": "Inoculante", "descricao": "Inoculantes agrícolas."},
    {"codigo": "ADJ", "nome": "Adjuvante", "descricao": "Adjuvantes para defensivos."},
]

def seed_categorias_for_empresa(empresa):
    criados = 0
    ignorados = 0
    for cat in DEFAULT_CATEGORIAS:
        obj, created = Categoria.objects.get_or_create(
            empresa=empresa,
            codigo=cat["codigo"],
            defaults={"nome": cat["nome"], "descricao": cat["descricao"], "ativo": True}
        )
        if created:
            criados += 1
        else:
            ignorados += 1
    return criados, ignorados

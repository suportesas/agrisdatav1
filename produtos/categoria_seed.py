# coding: utf-8
"""
Seed de Categorias de Produto padrão para novas empresas.
"""
from produtos.models import Categoria

DEFAULT_CATEGORIAS = [
    {
        "codigo": "DEF",
        "nome": "Defensivo Agrícola",
        "descricao": "Produtos defensivos para uso agrícola.",
        "condiciona_campos": True,
    },
    {
        "codigo": "FERT",
        "nome": "Fertilizante",
        "descricao": "Fertilizantes e adubos.",
        "condiciona_campos": True,
    },
    {
        "codigo": "SEM",
        "nome": "Semente",
        "descricao": "Sementes para plantio.",
        "condiciona_campos": False,
    },
    {
        "codigo": "ADUBO",
        "nome": "Adubo",
        "descricao": "Adubos em geral.",
        "condiciona_campos": False,
    },
    {
        "codigo": "CORR",
        "nome": "Corretivo de Solo",
        "descricao": "Produtos para correção de solo.",
        "condiciona_campos": False,
    },
    {
        "codigo": "INOC",
        "nome": "Inoculante",
        "descricao": "Inoculantes agrícolas.",
        "condiciona_campos": False,
    },
    {
        "codigo": "ADJ",
        "nome": "Adjuvante",
        "descricao": "Adjuvantes para defensivos.",
        "condiciona_campos": False,
    },
]

def seed_categorias_for_empresa(empresa):
    criados = 0
    ignorados = 0
    for cat in DEFAULT_CATEGORIAS:
        obj, created = Categoria.objects.get_or_create(
            empresa=empresa,
            codigo=cat["codigo"],
            defaults={
                "nome": cat["nome"],
                "descricao": cat["descricao"],
                "ativo": True,
                "condiciona_campos": cat.get("condiciona_campos", False),
            }
        )
        if created:
            criados += 1
        else:
            ignorados += 1
    return criados, ignorados

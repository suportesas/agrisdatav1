from produtos.models import TipoProduto

def seed_tipos_produto_for_empresa(empresa):
    tipos_padrao = [
        {'nome': 'Revenda', 'codigo': 'REV'},
        {'nome': 'Consumo', 'codigo': 'CON'},
        {'nome': 'Defensivo', 'codigo': 'DEF'},
        {'nome': 'Fertilizante', 'codigo': 'FERT'},
        {'nome': 'Semente', 'codigo': 'SEM'},
        {'nome': 'Outros', 'codigo': 'OUT'},
    ]
    criados = []
    ignorados = []
    for tipo in tipos_padrao:
        obj, created = TipoProduto.objects.get_or_create(
            empresa=empresa,
            codigo=tipo['codigo'],
            defaults={'nome': tipo['nome'], 'ativo': True}
        )
        if created:
            criados.append(obj)
        else:
            ignorados.append(obj)
    return criados, ignorados

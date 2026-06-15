from django.core.management.base import BaseCommand

from operacoes_campo.models import SubcategoriaItemCusto

SUBCATEGORIAS = {
    'MO': [
        'Funcionário Próprio',
        'Contratado',
        'Empreitada',
        'Diarista',
        'Técnico Agrícola',
    ],
    'MAQUINARIO': [
        'Próprio',
        'Alugado / Arrendado',
        'Terceirizado',
    ],
    'INSUMO': [
        'Fertilizante Fundação',
        'Fertilizante Cobertura',
        'Fertirrigação',
        'Herbicida',
        'Fungicida',
        'Inseticida',
        'Acaricida',
        'Nematicida',
        'Semente / Muda',
        'Inoculante',
        'Adjuvante',
    ],
    'SERVICO_EXTERNO': [
        'Análise de Solo',
        'Análise Foliar',
        'Consultoria Técnica',
        'Pulverização Aérea',
        'Serviço de Colheita',
    ],
    'ESTUFA': [
        'Produção de Mudas',
        'Substrato',
        'Bandejas',
        'Fertirrigação Estufa',
        'Mão de Obra Estufa',
    ],
}


class Command(BaseCommand):
    help = 'Popula subcategorias padrão para itens de custo de campo'

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for categoria, nomes in SUBCATEGORIAS.items():
            for nome in nomes:
                _, was_created = SubcategoriaItemCusto.objects.get_or_create(
                    categoria=categoria, nome=nome,
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1
        self.stdout.write(self.style.SUCCESS(
            f'Seed concluído: {created} criadas, {skipped} já existiam.'
        ))

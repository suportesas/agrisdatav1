from django.core.management.base import BaseCommand
from produtos.models import Categoria
from empresas.models import Empresa

CATEGORIAS_AGRICOLAS = [
    {"codigo": "DEF", "nome": "Defensivo Agrícola", "condiciona_campos": True},
    {"codigo": "FERT", "nome": "Fertilizante", "condiciona_campos": True},
    {"codigo": "SEM", "nome": "Semente", "condiciona_campos": True},
    {"codigo": "ADUB", "nome": "Adubo", "condiciona_campos": True},
    {"codigo": "CORR", "nome": "Corretivo de Solo", "condiciona_campos": True},
    {"codigo": "INOC", "nome": "Inoculante", "condiciona_campos": True},
    {"codigo": "ADJV", "nome": "Adjuvante", "condiciona_campos": True},
    {"codigo": "MAQ", "nome": "Máquina Agrícola", "condiciona_campos": False},
    {"codigo": "VEIC", "nome": "Veículo", "condiciona_campos": False},
    {"codigo": "FERR", "nome": "Ferramenta", "condiciona_campos": False},
    {"codigo": "EQUIP", "nome": "Equipamento", "condiciona_campos": False},
    {"codigo": "MOB", "nome": "Mobiliário", "condiciona_campos": False},
    {"codigo": "IMOV", "nome": "Imóvel", "condiciona_campos": False},
    {"codigo": "ATIV", "nome": "Ativo Imobilizado", "condiciona_campos": False, "patrimonial": True},
    {"codigo": "OUT", "nome": "Outros", "condiciona_campos": False}
]

class Command(BaseCommand):
    help = 'Popula categorias agrícolas padrão para todas as empresas.'

    def handle(self, *args, **options):
        empresas = Empresa.objects.all()
        total_empresas = 0
        total_categorias = 0
        for empresa in empresas:
            for cat in CATEGORIAS_AGRICOLAS:
                obj, created = Categoria.objects.get_or_create(
                    codigo=cat["codigo"],
                    empresa=empresa,
                    defaults={
                        "nome": cat["nome"],
                        "condiciona_campos": cat.get("condiciona_campos", False),
                        "patrimonial": cat.get("patrimonial", False),
                        "ativo": True
                    }
                )
                if created:
                    total_categorias += 1
            total_empresas += 1
        self.stdout.write(self.style.SUCCESS(f'Categorias padrão criadas para {total_empresas} empresas. Novas categorias: {total_categorias}'))

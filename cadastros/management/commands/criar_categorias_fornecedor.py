"""
Management command para criar categorias padrão de fornecedores
Arquivo: cadastros/management/commands/criar_categorias_fornecedor.py
"""

from django.core.management.base import BaseCommand
from cadastros.models import CategoriaFornecedor, SubcategoriaFornecedor


class Command(BaseCommand):
    help = 'Cria categorias padrão de fornecedores (globais para todas as empresas)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n🌱 Criando categorias padrão de fornecedores...\n'))

        # Categorias padrão do sistema (empresa=None = globais)
        categorias_padrao = [
            {
                'nome': 'Sementes',
                'icone': '🌱',
                'ordem': 1,
                'descricao': 'Fornecedores de sementes e mudas',
                'subcategorias': ['Milho', 'Soja', 'Feijão', 'Arroz', 'Trigo', 'Hortaliças']
            },
            {
                'nome': 'Fertilizantes',
                'icone': '🧪',
                'ordem': 2,
                'descricao': 'Fertilizantes e adubos agrícolas',
                'subcategorias': ['NPK', 'Orgânicos', 'Foliares', 'Corretivos']
            },
            {
                'nome': 'Defensivos Agrícolas',
                'icone': '🛡️',
                'ordem': 3,
                'descricao': 'Defensivos e produtos fitossanitários',
                'subcategorias': ['Herbicidas', 'Inseticidas', 'Fungicidas', 'Adjuvantes']
            },
            {
                'nome': 'Máquinas e Equipamentos',
                'icone': '🚜',
                'ordem': 4,
                'descricao': 'Máquinas agrícolas e equipamentos',
                'subcategorias': ['Tratores', 'Colheitadeiras', 'Pulverizadores', 'Implementos']
            },
            {
                'nome': 'Serviços',
                'icone': '🛠️',
                'ordem': 5,
                'descricao': 'Serviços agrícolas diversos',
                'subcategorias': ['Análise de Solo', 'Consultoria', 'Manutenção', 'Transporte']
            },
            {
                'nome': 'Embalagens',
                'icone': '📦',
                'ordem': 6,
                'descricao': 'Embalagens e materiais de acondicionamento',
                'subcategorias': ['Big Bags', 'Sacos', 'Caixas', 'Pallets']
            },
            {
                'nome': 'Transporte e Logística',
                'icone': '🚛',
                'ordem': 7,
                'descricao': 'Serviços de transporte e logística',
                'subcategorias': ['Transporte Rodoviário', 'Armazenagem', 'Frete']
            },
        ]

        categorias_criadas = 0
        subcategorias_criadas = 0

        for dados_cat in categorias_padrao:
            # Extrai subcategorias
            subcats = dados_cat.pop('subcategorias', [])
            
            # Cria ou atualiza categoria
            categoria, created = CategoriaFornecedor.objects.update_or_create(
                nome=dados_cat['nome'],
                empresa=None,  # Categorias globais
                defaults={
                    'icone': dados_cat['icone'],
                    'ordem': dados_cat['ordem'],
                    'descricao': dados_cat['descricao'],
                    'ativa': True
                }
            )

            if created:
                categorias_criadas += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Categoria criada: {categoria}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'  ⟳ Categoria atualizada: {categoria}')
                )

            # Cria subcategorias
            for subcat_nome in subcats:
                subcat, sub_created = SubcategoriaFornecedor.objects.get_or_create(
                    categoria=categoria,
                    nome=subcat_nome,
                    defaults={'ativa': True}
                )
                
                if sub_created:
                    subcategorias_criadas += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'    → Subcategoria criada: {subcat_nome}')
                    )

        # Resumo final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Pronto! {categorias_criadas} categoria(s) criada(s)!'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ {subcategorias_criadas} subcategoria(s) criada(s)!'
            )
        )
        
        # Mostra totais
        total_categorias = CategoriaFornecedor.objects.filter(empresa=None).count()
        total_subcategorias = SubcategoriaFornecedor.objects.count()
        
        self.stdout.write(
            self.style.WARNING(
                f'\n📊 Total no sistema: {total_categorias} categorias e {total_subcategorias} subcategorias'
            )
        )
        self.stdout.write('='*60 + '\n')
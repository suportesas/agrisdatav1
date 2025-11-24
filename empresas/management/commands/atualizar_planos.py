"""
Management command para atualizar planos de todas as empresas
Uso: python manage.py atualizar_planos
"""
from django.core.management.base import BaseCommand
from empresas.models import Empresa


class Command(BaseCommand):
    help = 'Atualiza os planos e limites de todas as empresas do sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--plano',
            type=str,
            help='Define o plano para todas as empresas (PEQUENO, MEDIO, GRANDE)',
            choices=['PEQUENO', 'MEDIO', 'GRANDE'],
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔄 Iniciando atualização de planos...'))
        
        empresas = Empresa.objects.all()
        total = empresas.count()
        
        if total == 0:
            self.stdout.write(self.style.ERROR('❌ Nenhuma empresa encontrada!'))
            return
        
        self.stdout.write(f'\n📊 Total de empresas: {total}\n')
        
        plano_especifico = options.get('plano')
        
        for i, empresa in enumerate(empresas, 1):
            # Se passou plano específico via argumento, usa ele
            if plano_especifico:
                empresa.plano = plano_especifico
            
            # Aplica os limites baseados no plano atual
            empresa.aplicar_limites_plano()
            empresa.save()
            
            # Mostra informações da empresa
            self.stdout.write(
                f'[{i}/{total}] ✅ {empresa.nome}\n'
                f'    📦 Plano: {empresa.get_plano_display()}\n'
                f'    🏞️  Limite Fazendas: {empresa.limite_fazendas}\n'
                f'    👥 Limite Usuários: {empresa.limite_usuarios}\n'
                f'    📐 Limite Talhões: {empresa.limite_talhoes}\n'
                f'    📦 Limite Produtos: {empresa.limite_produtos}\n'
                f'    💰 Mensalidade: R$ {empresa.valor_mensalidade}\n'
                f'    📊 Relatórios Avançados: {"✅" if empresa.acesso_relatorios_avancados else "❌"}\n'
                f'    🔌 API: {"✅" if empresa.acesso_api else "❌"}\n'
                f'    📱 App Mobile: {"✅" if empresa.acesso_app_mobile else "❌"}\n'
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ {total} empresa(s) atualizada(s) com sucesso!')
        )
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from empresas.models import Empresa


class Command(BaseCommand):
    help = 'Cria/atualiza empresa interna SaaS e vincula ao superadmin sem cobranca.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='Username do superadmin alvo')
        parser.add_argument('--empresa-nome', type=str, default='Matriz SaaS', help='Nome da empresa interna')

    def handle(self, *args, **options):
        username = options['username']
        empresa_nome = options['empresa_nome']

        User = get_user_model()
        admin = User.objects.filter(username=username, is_superuser=True).first()
        if not admin:
            raise CommandError(f'Superadmin nao encontrado para username={username}.')

        empresa, created = Empresa.objects.get_or_create(
            nome=empresa_nome,
            defaults={
                'plano': None,
                'is_interna_saas': True,
                'auto_seed_ncm': False,
                'ativa': True,
                'bloqueada': False,
                'valor_mensalidade': Decimal('0.00'),
                'dia_vencimento': 1,
            },
        )

        if not created:
            empresa.is_interna_saas = True
            empresa.plano = None
            empresa.auto_seed_ncm = False
            empresa.ativa = True
            empresa.bloqueada = False
            empresa.valor_mensalidade = Decimal('0.00')
            empresa.save()

        admin.empresa = empresa
        admin.save(update_fields=['empresa'])

        self.stdout.write(self.style.SUCCESS('[OK] Empresa interna SaaS configurada com sucesso.'))
        self.stdout.write(f'- Superadmin: {admin.username}')
        self.stdout.write(f'- Empresa: {empresa.nome}')
        self.stdout.write(f'- Interna SaaS: {empresa.is_interna_saas}')
        self.stdout.write(f'- Plano: {empresa.plano}')

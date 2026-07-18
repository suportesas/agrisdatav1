"""
Configuração única: transforma as 6 Funções padrão (antes só uma lista de
nomes soltos, criados vazios por empresa — ver DEFAULT_ROLES em
empresas/management/commands/seed_roles.py) em Funções Globais de verdade,
geridas pelo superuser no painel SaaS.

1. Cria (se não existir) uma Função Global (empresa=None, builtin=True)
   pra cada nome em DEFAULT_ROLES.
2. Para cada empresa que já existe, liga (origem_global) as cópias que ela
   já tem dessas 6 Funções à Global correspondente — sem mexer em nada que
   já esteja configurado (Programas concedidos, usuários vinculados).

Idempotente — pode rodar de novo sem duplicar nada.
"""

from django.core.management.base import BaseCommand

from empresas.management.commands.seed_roles import DEFAULT_ROLES


class Command(BaseCommand):
    help = 'Cria as 6 Funções padrão como Funções Globais e liga as cópias já existentes de cada empresa a elas'

    def handle(self, *args, **options):
        from empresas.models import Role

        criadas = 0
        for nome in DEFAULT_ROLES:
            _, created = Role.objects.get_or_create(
                empresa=None, name=nome, defaults={'builtin': True}
            )
            if created:
                criadas += 1
        self.stdout.write(self.style.SUCCESS(f'{criadas} Funções Globais criadas ({len(DEFAULT_ROLES)} no total).'))

        globais = {r.name: r for r in Role.objects.filter(empresa__isnull=True, name__in=DEFAULT_ROLES)}

        ligadas = 0
        candidatas = Role.objects.filter(
            empresa__isnull=False, name__in=DEFAULT_ROLES, origem_global__isnull=True
        )
        for role in candidatas:
            role_global = globais.get(role.name)
            if not role_global:
                continue
            role.origem_global = role_global
            role.save()
            ligadas += 1

        self.stdout.write(self.style.SUCCESS(f'{ligadas} Funções já existentes ligadas às Globais correspondentes.'))

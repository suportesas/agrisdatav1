"""
Configuração única (segunda etapa, depois de `criar_funcoes_globais_padrao`):
promove o conteúdo real que qualquer empresa já tiver configurado nas 6
Funções padrão pra dentro da Função Global correspondente, e remove as
cópias por empresa que só existiam por causa da ligação retroativa — elas
não foram criadas de verdade pela empresa, então voltam a ser só a Global
(ao vivo), até que a empresa personalize de propósito.

1. Para cada cópia por empresa ligada a uma Global (`origem_global`), copia
   os Programas que ela tiver e a Global ainda não tiver, pra dentro da
   Global (não perde nada — só passa a valer pra todas as empresas).
2. Reaponta os usuários que estiverem nessas cópias direto pra Global.
3. Apaga a cópia por empresa (e o Group Django associado).

Depois de rodar, as 6 Funções deixam de aparecer como "(<empresa>)" em
qualquer tela — voltam a aparecer como "(Global)" pra toda empresa que não
tiver clicado em "Personalizar".
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Promove Programas das cópias por-empresa das Funções padrão pra dentro das Globais, e remove as cópias'

    def handle(self, *args, **options):
        from empresas.models import Role
        from usuarios.models import Usuario

        globais_padrao = list(Role.objects.filter(empresa__isnull=True, builtin=True))
        ids_globais = [g.id for g in globais_padrao]

        candidatas = list(Role.objects.filter(origem_global_id__in=ids_globais, empresa__isnull=False))
        self.stdout.write(f'{len(candidatas)} cópias por-empresa encontradas.')

        programas_promovidos = 0
        for role in candidatas:
            role_global = role.origem_global
            programas_role = set(role.programas.values_list('id', flat=True))
            programas_global = set(role_global.programas.values_list('id', flat=True))
            extras = programas_role - programas_global
            if extras:
                role_global.programas.add(*extras)
                programas_promovidos += len(extras)

        usuarios_reapontados = 0
        for role in candidatas:
            role_global = role.origem_global
            for usuario in list(Usuario.objects.filter(roles=role)):
                usuario.roles.remove(role)
                usuario.roles.add(role_global)
                usuarios_reapontados += 1

        removidas = 0
        for role in candidatas:
            group = role.group
            nome = role.name
            empresa_nome = role.empresa.nome
            role.delete()
            if group:
                group.delete()
            removidas += 1
            self.stdout.write(f'  removida: {nome} ({empresa_nome})')

        self.stdout.write(self.style.SUCCESS(
            f'{programas_promovidos} Programas promovidos pra Globais, '
            f'{usuarios_reapontados} usuários reapontados, '
            f'{removidas} cópias por-empresa removidas.'
        ))

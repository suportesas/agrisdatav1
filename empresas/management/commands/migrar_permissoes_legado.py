"""
Migração única: mapeia as permissões Django (Group/Permission) que cada Role
já tem hoje para os Programas equivalentes (best-effort por app+model+ação),
preservando o acesso atual o máximo possível antes do novo middleware de
enforcement por Programa entrar em vigor (ver core/middleware/programa_enforcement.py).

Estratégia de matching, em ordem de prioridade:
1. Mesmo app_label da permissão + grupo_tela igual ao nome do model.
2. Qualquer app_label + grupo_tela igual ao nome do model — cobre o caso de
   ContentTypes órfãos (ex.: `cadastros.abastecimentoveiculo`, que ficou para
   trás quando o model foi movido para o app `frota`; ver
   `cadastros/migrations/0112_remove_rh_models.py` e refatorações similares).
3. Comparação por conjunto de palavras entre o `grupo_tela` (derivado do nome
   da URL) e o nome da classe do model — cobre casos em que a ordem das
   palavras diverge entre o nome da URL e o nome do model
   (ex.: URL `fazenda_contato_create` vs model `ContatoFazenda`).

Permissões sem Programa correspondente mesmo após as 3 tentativas (ex.:
permissões customizadas como `compras.criar_pedido_direto_fornecedor_unico`,
que não mapeiam 1:1 para uma tela) são listadas no relatório final para
revisão manual — não travam a migração das demais.
"""

import re

from django.apps import apps as django_apps
from django.core.management.base import BaseCommand

ACAO_LEGADO_PARA_TIPO = {
    'add': 'criar',
    'change': 'editar',
    'delete': 'excluir',
    'view': 'abrir',
}


def _palavras_model(model_cls):
    return set(w.lower() for w in re.findall(r'[A-Z][a-z0-9]*', model_cls._meta.object_name))


def _palavras_grupo(grupo_tela):
    return set(w for w in grupo_tela.split('_') if w)


def _buscar_model_class(app_label, model_name):
    try:
        return django_apps.get_model(app_label, model_name)
    except LookupError:
        pass
    for app_config in django_apps.get_app_configs():
        for model in app_config.get_models():
            if model._meta.model_name == model_name:
                return model
    return None


class Command(BaseCommand):
    help = 'Mapeia as permissões legadas (Group/Permission) de cada Role para os Programas equivalentes'

    def handle(self, *args, **options):
        from empresas.models import Role, Programa

        total_mapeadas = 0
        total_sem_correspondencia = 0
        sem_correspondencia_detalhe = []
        roles_afetadas = 0

        # Cache: (app_label ou None para "qualquer", tipo_acao) -> lista de Programas ativos
        programas_por_app_tipo = {}
        programas_por_tipo = {}

        def _programas(app_label, tipo_acao):
            chave = (app_label, tipo_acao)
            if chave not in programas_por_app_tipo:
                programas_por_app_tipo[chave] = list(
                    Programa.objects.filter(app_label=app_label, tipo_acao=tipo_acao, ativo=True)
                )
            return programas_por_app_tipo[chave]

        def _programas_qualquer_app(tipo_acao):
            if tipo_acao not in programas_por_tipo:
                programas_por_tipo[tipo_acao] = list(Programa.objects.filter(tipo_acao=tipo_acao, ativo=True))
            return programas_por_tipo[tipo_acao]

        def _encontrar_candidato(app_label, model_name, tipo_acao):
            if not tipo_acao:
                return None

            for c in _programas(app_label, tipo_acao):
                if c.grupo_tela.replace('_', '') == model_name:
                    return c

            for c in _programas_qualquer_app(tipo_acao):
                if c.grupo_tela.replace('_', '') == model_name:
                    return c

            model_cls = _buscar_model_class(app_label, model_name)
            if model_cls is not None:
                palavras_model = _palavras_model(model_cls)
                if palavras_model:
                    for c in _programas_qualquer_app(tipo_acao):
                        if _palavras_grupo(c.grupo_tela) == palavras_model:
                            return c

            return None

        roles = Role.objects.select_related('empresa', 'group').all()
        for role in roles:
            if not role.group:
                continue
            permissoes = list(role.group.permissions.select_related('content_type').all())
            if not permissoes:
                continue

            programa_ids = set()
            for perm in permissoes:
                acao = perm.codename.split('_', 1)[0]
                tipo_acao = ACAO_LEGADO_PARA_TIPO.get(acao)
                model_name = perm.content_type.model
                app_label = perm.content_type.app_label

                candidato = _encontrar_candidato(app_label, model_name, tipo_acao)

                if candidato:
                    programa_ids.add(candidato.id)
                    total_mapeadas += 1
                else:
                    total_sem_correspondencia += 1
                    sem_correspondencia_detalhe.append(
                        f"{role.empresa.nome} / {role.name}: {app_label}.{perm.codename}"
                    )

            if programa_ids:
                role.programas.add(*Programa.objects.filter(id__in=programa_ids))
                roles_afetadas += 1

        self.stdout.write(self.style.SUCCESS(
            f"Migração concluída: {roles_afetadas} Funções atualizadas, "
            f"{total_mapeadas} permissões mapeadas, "
            f"{total_sem_correspondencia} sem correspondência automática."
        ))

        if sem_correspondencia_detalhe:
            self.stdout.write(self.style.WARNING(
                "\nPermissões SEM correspondência automática "
                "(revisar manualmente na tela de Funções e Permissões):"
            ))
            for linha in sem_correspondencia_detalhe:
                self.stdout.write(f"  - {linha}")

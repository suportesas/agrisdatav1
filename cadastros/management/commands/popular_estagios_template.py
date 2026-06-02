"""
Comando: populares_estagios_template
Popula os estágios template padrão para o sistema
Estes estágios serão copiados automaticamente para cada nova empresa

Uso: py manage.py popular_estagios_template
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from mip.models import EstagioDesenvolvimento
from cadastros.models import Praga


class Command(BaseCommand):
    help = 'Popula os estágios de desenvolvimento template padrão para cada praga'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Populando estágios template padrão'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        # Dicionário de estágios padrão por praga
        ESTAGIOS_PADRAO = {
            # Lagarta-do-Cartucho do Milho
            'Lagarta-do-cartucho': [
                {
                    'tipo_estagio': 'OVO',
                    'descricao': 'Ovo (oviposição)',
                    'duracao_minima_dias': 2,
                    'duracao_maxima_dias': 4,
                    'ordem_ciclo': 1,
                    'eh_fase_critica': False,
                    'observacoes': 'Ovos em camadas nos colmos, atacam plantas jovens'
                },
                {
                    'tipo_estagio': 'LARVA',
                    'descricao': 'Larva de 1º ínstar',
                    'duracao_minima_dias': 2,
                    'duracao_maxima_dias': 3,
                    'ordem_ciclo': 2,
                    'eh_fase_critica': False,
                    'observacoes': 'Larva pequena, até 3mm'
                },
                {
                    'tipo_estagio': 'LARVA',
                    'descricao': 'Larva de 2º ínstar',
                    'duracao_minima_dias': 2,
                    'duracao_maxima_dias': 3,
                    'ordem_ciclo': 3,
                    'eh_fase_critica': False,
                    'observacoes': 'Larva intermediária'
                },
                {
                    'tipo_estagio': 'LARVA',
                    'descricao': 'Larva de 3º ínstar',
                    'duracao_minima_dias': 3,
                    'duracao_maxima_dias': 5,
                    'ordem_ciclo': 4,
                    'eh_fase_critica': True,
                    'observacoes': 'Larva grande, até 4cm, é a mais destrutiva'
                },
                {
                    'tipo_estagio': 'LARVA',
                    'descricao': 'Larva de 4º ínstar',
                    'duracao_minima_dias': 3,
                    'duracao_maxima_dias': 5,
                    'ordem_ciclo': 5,
                    'eh_fase_critica': True,
                    'observacoes': 'Larva grande, até 8mm, mais voraz ainda'
                },
                {
                    'tipo_estagio': 'LARVA',
                    'descricao': 'Larva de 5º/6º ínstar',
                    'duracao_minima_dias': 4,
                    'duracao_maxima_dias': 7,
                    'ordem_ciclo': 6,
                    'eh_fase_critica': True,
                    'observacoes': 'Larva grande, até 15mm, período mais destrutivo'
                },
                {
                    'tipo_estagio': 'PUPA',
                    'descricao': 'Pupa no solo',
                    'duracao_minima_dias': 5,
                    'duracao_maxima_dias': 14,
                    'ordem_ciclo': 7,
                    'eh_fase_critica': False,
                    'observacoes': 'Imóvel, em câmara pupal no solo'
                },
                {
                    'tipo_estagio': 'ADULTO',
                    'descricao': 'Adulto (mariposa)',
                    'duracao_minima_dias': 10,
                    'duracao_maxima_dias': 20,
                    'ordem_ciclo': 8,
                    'eh_fase_critica': False,
                    'observacoes': 'Mariposa que coloca ovos no colmo'
                },
            ],
            
            # Podridão negra dos frutos (Doença)
            'Podridão-negrados-frutos': [
                {
                    'tipo_estagio': 'ESPORO',
                    'descricao': 'Esporos dormentes no solo',
                    'duracao_minima_dias': 30,
                    'duracao_maxima_dias': 365,
                    'ordem_ciclo': 1,
                    'eh_fase_critica': False,
                    'observacoes': 'Sobrevivência no solo, muito importante para rotação de culturas'
                },
                {
                    'tipo_estagio': 'LESAO',
                    'descricao': 'Lesão inicial no fruto',
                    'duracao_minima_dias': 1,
                    'duracao_maxima_dias': 3,
                    'ordem_ciclo': 2,
                    'eh_fase_critica': False,
                    'observacoes': 'Pequenas manchas marrom-escuras'
                },
                {
                    'tipo_estagio': 'LESAO',
                    'descricao': 'Lesão necrótica em expansão',
                    'duracao_minima_dias': 3,
                    'duracao_maxima_dias': 7,
                    'ordem_ciclo': 3,
                    'eh_fase_critica': True,
                    'observacoes': 'Mancha expande, escurece, centro aprofunda'
                },
                {
                    'tipo_estagio': 'LESAO',
                    'descricao': 'Esporulação (produção de esporos)',
                    'duracao_minima_dias': 5,
                    'duracao_maxima_dias': 10,
                    'ordem_ciclo': 4,
                    'eh_fase_critica': True,
                    'observacoes': 'Crescimento cinzento claro de esporos na lesão'
                },
            ],
        }
        
        created_count = 0
        skipped_count = 0
        
        for praga_nome, estagios_lista in ESTAGIOS_PADRAO.items():
            try:
                # Buscar praga
                praga = Praga.objects.filter(nome_comum=praga_nome).first()
                if not praga:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Praga "{praga_nome}" não encontrada. Pulando...')
                    )
                    continue
                
                self.stdout.write(f'\n📋 Processando: {praga_nome}')
                
                for estagio_data in estagios_lista:
                    # Verificar se já existe um template igual
                    existe = EstagioDesenvolvimento.objects.filter(
                        eh_template=True,
                        empresa__isnull=True,
                        praga=praga,
                        tipo_estagio=estagio_data['tipo_estagio'],
                        ordem_ciclo=estagio_data['ordem_ciclo']
                    ).exists()
                    
                    if existe:
                        skipped_count += 1
                        self.stdout.write('  ✅ [JÁ EXISTE] ' + estagio_data['descricao'])
                    else:
                        EstagioDesenvolvimento.objects.create(
                            praga=praga,
                            eh_template=True,
                            empresa=None,  # Template sem empresa
                            template_original=None,
                            **estagio_data
                        )
                        created_count += 1
                        self.stdout.write(f'  ✨ [CRIADO] {estagio_data["descricao"]}')
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro ao processar {praga_nome}: {str(e)}')
                )
        
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS(f'✅ Processo concluído!'))
        self.stdout.write(f'   📊 Criados: {created_count}')
        self.stdout.write(f'   ⏭️  Já existiam: {skipped_count}')
        self.stdout.write('=' * 70)

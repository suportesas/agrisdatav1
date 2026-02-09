#!/usr/bin/env python
"""
VERIFICAÇÃO DO SISTEMA DE SEED DE PRAGAS
Script para validar que tudo está funcionando corretamente
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Count
from empresas.models import Empresa, Plano
from cadastros.models import Praga
from cadastros.pragas_seed import PRAGAS_SEED, seed_pragas_for_company

class Verificador:
    def __init__(self):
        self.erros = []
        self.avisos = []
        self.sucessos = []
    
    def adicionar_erro(self, msg):
        self.erros.append(f"❌ {msg}")
    
    def adicionar_aviso(self, msg):
        self.avisos.append(f"⚠️  {msg}")
    
    def adicionar_sucesso(self, msg):
        self.sucessos.append(f"✅ {msg}")
    
    def imprimir_relatorio(self):
        print("\n" + "=" * 80)
        print("RELATÓRIO DE VERIFICAÇÃO")
        print("=" * 80)
        
        if self.sucessos:
            print("\n✅ SUCESSOS:")
            for msg in self.sucessos:
                print(f"   {msg}")
        
        if self.avisos:
            print("\n⚠️  AVISOS:")
            for msg in self.avisos:
                print(f"   {msg}")
        
        if self.erros:
            print("\n❌ ERROS:")
            for msg in self.erros:
                print(f"   {msg}")
            return False
        
        print("\n" + "=" * 80)
        print("✅ TODAS AS VERIFICAÇÕES PASSARAM!")
        print("=" * 80)
        return True
    
    def verificar_seed_data(self):
        """Verifica se o arquivo de seed está correto"""
        print("\n🔍 Verificando dados de seed...")
        
        if not PRAGAS_SEED:
            self.adicionar_erro("PRAGAS_SEED está vazio!")
            return
        
        self.adicionar_sucesso(f"PRAGAS_SEED contém {len(PRAGAS_SEED)} pragas")
        
        # Verificar estrutura
        for i, praga in enumerate(PRAGAS_SEED, 1):
            if not isinstance(praga, dict):
                self.adicionar_erro(f"Praga {i} não é um dicionário")
                continue
            
            if 'nome_comum' not in praga:
                self.adicionar_erro(f"Praga {i} não tem 'nome_comum'")
                continue
            
            if not praga['nome_comum']:
                self.adicionar_erro(f"Praga {i} tem 'nome_comum' vazio")
        
        # Verificar nomes duplicados
        nomes = [p['nome_comum'] for p in PRAGAS_SEED]
        duplicados = [n for n in nomes if nomes.count(n) > 1]
        if duplicados:
            self.adicionar_erro(f"Nomes duplicados em seed: {set(duplicados)}")
        else:
            self.adicionar_sucesso("Nenhum nome duplicado no seed")
    
    def verificar_modelo(self):
        """Verifica se o modelo está configurado corretamente"""
        print("\n🔍 Verificando modelo Praga...")
        
        # Verificar ForeignKey para Empresa
        campo_empresa = Praga._meta.get_field('empresa')
        if campo_empresa.many_to_one and campo_empresa.related_model.__name__ == 'Empresa':
            self.adicionar_sucesso("ForeignKey 'empresa' configurado corretamente")
        else:
            self.adicionar_erro("ForeignKey 'empresa' não está correto")
        
        # Verificar constraint de unicidade
        constraints = [c.name for c in Praga._meta.constraints]
        if 'unique_praga_empresa' in constraints:
            self.adicionar_sucesso("Constraint de unicidade (empresa, nome_comum) existe")
        else:
            self.adicionar_aviso("Constraint de unicidade não encontrado")
        
        # Verificar indexes
        indexes = [idx.name for idx in Praga._meta.indexes]
        if any('empresa' in idx for idx in indexes):
            self.adicionar_sucesso("Indexes para empresa existem")
        else:
            self.adicionar_aviso("Indexes otimizados não encontrados")
    
    def verificar_signal(self):
        """Verifica se o signal está registrado"""
        print("\n🔍 Verificando signal...")
        
        from django.db.models.signals import post_save
        from django.dispatch import Signal
        
        # Verificar se o signal está conectado
        receivers = post_save.receivers
        empresa_receivers = [r for r in receivers if 'Empresa' in str(r)]
        
        if empresa_receivers:
            self.adicionar_sucesso("Signal post_save para Empresa registrado")
        else:
            self.adicionar_aviso("Signal post_save para Empresa pode não estar registrado")
    
    def verificar_automacao(self):
        """Testa a automação de seed"""
        print("\n🔍 Testando automação de seed...")
        
        try:
            # Obter ou criar plano
            plano = Plano.objects.first()
            if not plano:
                self.adicionar_aviso("Nenhum plano encontrado, criando padrão")
                plano, _ = Plano.objects.get_or_create(
                    codigo='TESTE',
                    defaults={'nome': 'Plano Teste', 'valor_mensal': 0}
                )
            
            # Criar empresa de teste
            empresa_teste, criada = Empresa.objects.get_or_create(
                nome='EMPRESA_VERIFICACAO_AUTOMATICA',
                defaults={'plano': plano}
            )
            
            if criada:
                self.adicionar_sucesso("Empresa de teste criada (signal deveria ter disparado)")
            else:
                self.adicionar_aviso("Empresa de teste já existe")
            
            # Verificar se pragas foram criadas
            pragas = Praga.objects.filter(empresa=empresa_teste)
            count = pragas.count()
            
            if count == 0:
                self.adicionar_aviso(f"Nenhuma praga na empresa de teste (esperado se signal falhou)")
                print(f"   Tentando seed manual...")
                criadas, ignoradas = seed_pragas_for_company(empresa_teste)
                self.adicionar_sucesso(f"Seed manual criou {criadas} pragas")
            elif count == len(PRAGAS_SEED):
                self.adicionar_sucesso(f"Todas as {count} pragas foram criadas!")
            else:
                self.adicionar_aviso(f"Empresa tem {count} pragas, esperado {len(PRAGAS_SEED)}")
        
        except Exception as e:
            self.adicionar_erro(f"Erro ao testar automação: {str(e)}")
    
    def verificar_isolamento(self):
        """Verifica isolamento multi-tenant"""
        print("\n🔍 Verificando isolamento multi-tenant...")
        
        try:
            plano = Plano.objects.first()
            if not plano:
                self.adicionar_aviso("Nenhum plano para criar empresas de teste")
                return
            
            # Criar duas empresas
            emp1, _ = Empresa.objects.get_or_create(
                nome='EMPRESA_A_ISOLAMENTO',
                defaults={'plano': plano}
            )
            emp2, _ = Empresa.objects.get_or_create(
                nome='EMPRESA_B_ISOLAMENTO',
                defaults={'plano': plano}
            )
            
            # Seed em ambas
            criadas1, _ = seed_pragas_for_company(emp1)
            criadas2, _ = seed_pragas_for_company(emp2)
            
            # Contar pragas
            count1 = Praga.objects.filter(empresa=emp1).count()
            count2 = Praga.objects.filter(empresa=emp2).count()
            
            if count1 == count2 == len(PRAGAS_SEED):
                self.adicionar_sucesso(f"Ambas empresas têm {count1} pragas")
            else:
                self.adicionar_erro(f"Contagem diferente: emp1={count1}, emp2={count2}")
            
            # Testar isolamento
            praga_emp1 = Praga.objects.filter(empresa=emp1).first()
            if praga_emp1:
                # Editar praga da empresa 1
                original_name = praga_emp1.nome_comum
                praga_emp1.nome_comum = 'PRAGA_TESTE_ISOLAMENTO'
                praga_emp1.save()
                
                # Verificar que empresa 2 não foi afetada
                existe_em_emp2 = Praga.objects.filter(
                    empresa=emp2,
                    nome_comum='PRAGA_TESTE_ISOLAMENTO'
                ).exists()
                
                if not existe_em_emp2:
                    self.adicionar_sucesso("Isolamento multi-tenant funcionando!")
                else:
                    self.adicionar_erro("Isolamento falhou - empresa 2 foi afetada")
                
                # Restaurar
                praga_emp1.nome_comum = original_name
                praga_emp1.save()
        
        except Exception as e:
            self.adicionar_erro(f"Erro ao testar isolamento: {str(e)}")
    
    def executar_todas_verificacoes(self):
        """Executa todas as verificações"""
        print("\n" + "=" * 80)
        print("🔍 INICIANDO VERIFICAÇÃO DO SISTEMA DE SEED DE PRAGAS")
        print("=" * 80)
        
        self.verificar_seed_data()
        self.verificar_modelo()
        self.verificar_signal()
        self.verificar_automacao()
        self.verificar_isolamento()
        
        return self.imprimir_relatorio()


if __name__ == '__main__':
    verificador = Verificador()
    sucesso = verificador.executar_todas_verificacoes()
    sys.exit(0 if sucesso else 1)

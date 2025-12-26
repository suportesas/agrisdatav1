"""
🔧 SCRIPT DE CORREÇÃO AUTOMÁTICA - MÓDULO VENDEDOR
==================================================

Este script corrige automaticamente os erros no módulo de vendedores.

COMO USAR:
1. Salve este arquivo como: fix_vendedor_automatico.py
2. Coloque na raiz do projeto (mesma pasta do manage.py)
3. Execute: python fix_vendedor_automatico.py
4. Execute: python manage.py makemigrations
5. Execute: python manage.py migrate
6. Execute: python manage.py runserver

O script fará backup automático dos arquivos antes de modificá-los.
"""

import os
import re
from datetime import datetime
import shutil


def fazer_backup(filepath):
    """Cria backup do arquivo original"""
    if not os.path.exists(filepath):
        print(f"❌ Arquivo não encontrado: {filepath}")
        return False
    
    backup_path = f"{filepath}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backup criado: {backup_path}")
    return True


def corrigir_views():
    """Corrige o arquivo views.py"""
    filepath = 'cadastros/views.py'
    
    print("\n" + "="*70)
    print("🔧 CORRIGINDO VIEWS.PY")
    print("="*70)
    
    if not os.path.exists(filepath):
        print(f"❌ Arquivo não encontrado: {filepath}")
        return False
    
    # Faz backup
    if not fazer_backup(filepath):
        return False
    
    # Lê o arquivo
    with open(filepath, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Contador de correções
    correcoes = 0
    
    # Correção 1: Adicionar imports se não existirem
    imports_necessarios = [
        "from django.db.models import Q, Sum",
        "from django.utils import timezone",
    ]
    
    for import_line in imports_necessarios:
        if import_line not in conteudo:
            # Encontra a última linha de import
            linhas = conteudo.split('\n')
            ultima_import = 0
            for i, linha in enumerate(linhas):
                if linha.strip().startswith('import ') or linha.strip().startswith('from '):
                    ultima_import = i
            
            # Insere o import
            linhas.insert(ultima_import + 1, import_line)
            conteudo = '\n'.join(linhas)
            correcoes += 1
            print(f"✅ Import adicionado: {import_line}")
    
    # Correção 2: Trocar user= por usuario= nos formulários de vendedor
    # Padrões a substituir
    padroes = [
        (r'VendedorForm\([^)]*user=request\.user', 
         lambda m: m.group(0).replace('user=request.user', 'usuario=request.user')),
    ]
    
    for padrao, substituicao in padroes:
        if callable(substituicao):
            novo_conteudo = re.sub(padrao, substituicao, conteudo)
            if novo_conteudo != conteudo:
                correcoes += 1
                print("✅ Corrigido: user= → usuario= em VendedorForm")
                conteudo = novo_conteudo
    
    # Salva o arquivo corrigido
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print(f"\n✅ Total de correções aplicadas: {correcoes}")
    return True


def corrigir_forms():
    """Corrige o arquivo forms.py"""
    filepath = 'cadastros/forms.py'
    
    print("\n" + "="*70)
    print("🔧 CORRIGINDO FORMS.PY")
    print("="*70)
    
    if not os.path.exists(filepath):
        print(f"❌ Arquivo não encontrado: {filepath}")
        return False
    
    # Faz backup
    if not fazer_backup(filepath):
        return False
    
    # Lê o arquivo
    with open(filepath, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Comentar classes problemáticas
    classes_para_comentar = [
        'VendedorFiltroForm',
        'VendedorForm',
        'ComissaoVendedorForm',
    ]
    
    linhas = conteudo.split('\n')
    novas_linhas = []
    dentro_de_classe = None
    nivel_indentacao = 0
    comentado = []
    
    for linha in linhas:
        # Verifica se estamos começando uma das classes problemáticas
        for classe in classes_para_comentar:
            if f'class {classe}' in linha and not linha.strip().startswith('#'):
                dentro_de_classe = classe
                nivel_indentacao = len(linha) - len(linha.lstrip())
                comentado.append(classe)
                
                # Adiciona cabeçalho
                novas_linhas.append('\n# ' + '='*70)
                novas_linhas.append(f'# 🔧 TEMPORARIAMENTE DESABILITADO: {classe}')
                novas_linhas.append('# Será substituído pela versão corrigida')
                novas_linhas.append('# ' + '='*70)
                novas_linhas.append('# ' + linha)
                continue
        
        # Se estamos dentro de uma classe sendo comentada
        if dentro_de_classe:
            indentacao_atual = len(linha) - len(linha.lstrip())
            
            # Linha vazia ou comentário, mantém
            if not linha.strip() or linha.strip().startswith('#'):
                novas_linhas.append(linha)
                continue
            
            # Saiu da classe
            if indentacao_atual <= nivel_indentacao and linha.strip():
                dentro_de_classe = None
                novas_linhas.append('# ' + '='*70 + '\n')
                novas_linhas.append(linha)
                continue
            
            # Comenta a linha
            novas_linhas.append('# ' + linha)
        else:
            novas_linhas.append(linha)
    
    # Salva
    novo_conteudo = '\n'.join(novas_linhas)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(novo_conteudo)
    
    if comentado:
        print(f"✅ Classes comentadas: {', '.join(comentado)}")
    else:
        print("ℹ️  Nenhuma classe problemática encontrada (já deve estar corrigida)")
    
    # Adiciona o código correto no final
    codigo_correto = '''

# =============================================================================
# 📝 FORMULÁRIOS DE VENDEDOR (VERSÃO CORRIGIDA)
# =============================================================================
# Adicionado automaticamente pelo script de correção

from .models import Vendedor, ComissaoVendedor
from decimal import Decimal
import re

class VendedorFiltroForm(forms.Form):
    """Formulário de filtros para listagem de vendedores"""
    
    busca = forms.CharField(
        label='Buscar',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome, CPF, e-mail...'
        })
    )
    
    status = forms.ChoiceField(
        label='Status',
        required=False,
        choices=[
            ('', '-- Todos os Status --'),
            ('ATIVO', 'Ativo'),
            ('INATIVO', 'Inativo'),
            ('FERIAS', 'Férias'),
            ('AFASTADO', 'Afastado'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tipo_mercado = forms.ChoiceField(
        label='Tipo de Mercado',
        required=False,
        choices=[
            ('', '-- Todos os Tipos --'),
            ('INTERNO', 'Mercado Interno'),
            ('EXTERNO', 'Exportação'),
            ('AMBOS', 'Interno + Exportação'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class VendedorForm(forms.ModelForm):
    """Formulário para cadastro/edição de vendedores"""
    
    class Meta:
        model = Vendedor
        fields = [
            'nome_completo', 'cpf', 'rg', 'data_nascimento', 'foto',
            'tipo_mercado', 'tipo_vinculo',
            'telefone_principal', 'email_corporativo',
            'comissao_mercado_interno', 'comissao_exportacao',
            'status', 'data_admissao',
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'cpf': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 14}),
            'rg': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'foto': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo_mercado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_vinculo': forms.Select(attrs={'class': 'form-select'}),
            'telefone_principal': forms.TextInput(attrs={'class': 'form-control'}),
            'email_corporativo': forms.EmailInput(attrs={'class': 'form-control'}),
            'comissao_mercado_interno': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'comissao_exportacao': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'data_admissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        vendedor = super().save(commit=False)
        if self.empresa:
            vendedor.empresa = self.empresa
        if self.usuario and not vendedor.pk:
            vendedor.criado_por = self.usuario
        if commit:
            vendedor.save()
        return vendedor


class ComissaoVendedorForm(forms.ModelForm):
    """Formulário para comissões"""
    
    class Meta:
        model = ComissaoVendedor
        fields = ['vendedor', 'referencia_mes', 'valor_base', 'percentual', 'status']
        widgets = {
            'vendedor': forms.Select(attrs={'class': 'form-select'}),
            'referencia_mes': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

# FIM DOS FORMULÁRIOS DE VENDEDOR
'''
    
    # Verifica se já existe código correto
    if '# FORMULÁRIOS DE VENDEDOR (VERSÃO CORRIGIDA)' not in novo_conteudo:
        novo_conteudo += codigo_correto
        print("✅ Código correto adicionado ao final do arquivo")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(novo_conteudo)
    
    return True


def main():
    """Função principal"""
    print("\n" + "="*70)
    print("🚀 SCRIPT DE CORREÇÃO AUTOMÁTICA - MÓDULO VENDEDOR")
    print("="*70)
    print("\nEste script irá:")
    print("1. Fazer backup dos arquivos originais")
    print("2. Corrigir forms.py")
    print("3. Corrigir views.py")
    print("\n" + "="*70)
    
    input("\nPressione ENTER para continuar...")
    
    # Verifica se estamos na raiz do projeto
    if not os.path.exists('manage.py'):
        print("\n❌ ERRO: Execute este script na raiz do projeto Django!")
        print("   (mesma pasta onde está o manage.py)")
        return
    
    # Executa correções
    sucesso_forms = corrigir_forms()
    sucesso_views = corrigir_views()
    
    # Resultado final
    print("\n" + "="*70)
    print("📊 RESULTADO FINAL")
    print("="*70)
    
    if sucesso_forms and sucesso_views:
        print("\n✅ CORREÇÕES APLICADAS COM SUCESSO!")
        print("\n📋 PRÓXIMOS PASSOS:")
        print("1. Execute: python manage.py makemigrations")
        print("2. Execute: python manage.py migrate")
        print("3. Execute: python manage.py runserver")
        print("4. Acesse: http://localhost:8000/cadastros/vendedores/")
        print("\n🎉 Pronto! O módulo de vendedores deve estar funcionando!")
    else:
        print("\n⚠️  Algumas correções falharam.")
        print("   Verifique os erros acima e tente corrigir manualmente.")
    
    print("\n💾 Backups criados com sucesso!")
    print("   Para restaurar, renomeie os arquivos .backup_*")
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
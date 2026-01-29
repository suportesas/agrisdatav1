"""
Script para verificar todos os campos da tabela ProdutoTributacao
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import ProdutoTributacao
from produtos.forms import ProdutoTributacaoForm

def verificar_campos():
    print("=" * 80)
    print("VERIFICAÇÃO DE CAMPOS - PRODUTO TRIBUTAÇÃO")
    print("=" * 80)
    
    # Campos do Model
    print("\n📋 CAMPOS NO MODEL (ProdutoTributacao):")
    print("-" * 80)
    model_fields = []
    for field in ProdutoTributacao._meta.get_fields():
        if hasattr(field, 'name'):
            field_type = type(field).__name__
            is_required = ''
            
            # Verificar se é obrigatório
            if hasattr(field, 'blank'):
                is_required = '⚠️ OPCIONAL' if field.blank else '✅ OBRIGATÓRIO'
            elif hasattr(field, 'null'):
                is_required = '⚠️ OPCIONAL' if field.null else '✅ OBRIGATÓRIO'
            else:
                is_required = '🔄 AUTO'
                
            model_fields.append(field.name)
            print(f"  {field.name:35} {field_type:25} {is_required}")
    
    # Campos no Form
    print("\n📝 CAMPOS NO FORM (ProdutoTributacaoForm):")
    print("-" * 80)
    form = ProdutoTributacaoForm()
    form_fields = list(form.fields.keys())
    for field_name in form_fields:
        field = form.fields[field_name]
        is_required = '✅ OBRIGATÓRIO' if field.required else '⚠️ OPCIONAL'
        widget_type = type(field.widget).__name__
        print(f"  {field_name:35} {widget_type:25} {is_required}")
    
    # Comparação
    print("\n🔍 ANÁLISE DE DIFERENÇAS:")
    print("-" * 80)
    
    # Campos no Model mas não no Form
    model_only = set(model_fields) - set(form_fields)
    if model_only:
        print("\n❌ Campos no MODEL mas NÃO no FORM:")
        for field in sorted(model_only):
            print(f"  • {field}")
    
    # Campos no Form mas não no Model
    form_only = set(form_fields) - set(model_fields)
    if form_only:
        print("\n⚠️  Campos no FORM mas NÃO no MODEL:")
        for field in sorted(form_only):
            print(f"  • {field}")
    
    # Campos em ambos
    both = set(model_fields) & set(form_fields)
    print(f"\n✅ Campos presentes em AMBOS: {len(both)}")
    
    # Campos obrigatórios
    print("\n🎯 CAMPOS OBRIGATÓRIOS NO MODEL:")
    print("-" * 80)
    for field in ProdutoTributacao._meta.get_fields():
        if hasattr(field, 'blank') and not field.blank and hasattr(field, 'name'):
            if field.name not in ['id', 'created_at', 'updated_at']:
                print(f"  • {field.name}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    verificar_campos()

#!/usr/bin/env python
"""
Script para testar upload de arquivos no Supabase Storage
Simula: Empresa faz upload de logo, documento, imagem de produto
Executa: python test_storage_upload.py
"""

import os
from io import BytesIO
from datetime import datetime
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

# Setup Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from core.supabase_config import supabase_auth
from core.storage import SupabaseStorageHelper


def create_test_image():
    """Cria uma imagem PNG de teste"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    img_file = InMemoryUploadedFile(
        img_io, 'ImageField', 'test_logo.png',
        'image/png', img_io.getbuffer().nbytes, None
    )
    return img_file


def create_test_pdf():
    """Cria um documento PDF de teste"""
    from reportlab.pdfgen import canvas
    
    pdf_io = BytesIO()
    c = canvas.Canvas(pdf_io)
    c.drawString(100, 750, "Documento de Teste - ERP Agrícola")
    c.drawString(100, 735, f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    c.save()
    
    pdf_io.seek(0)
    pdf_file = InMemoryUploadedFile(
        pdf_io, 'FileField', 'test_documento.pdf',
        'application/pdf', pdf_io.getbuffer().nbytes, None
    )
    return pdf_file


def test_empresa_logo_upload():
    """Testa upload de logo da empresa"""
    print("\n📸 Testando upload de logo da empresa...")
    
    try:
        storage = SupabaseStorageHelper()
        img_file = create_test_image()
        
        # Simula o caminho que o signal vai gerar
        now = datetime.now()
        file_path = f"empresa1/{now.year}/{now.month:02d}/test_logo.png"
        
        # Upload
        url = storage.upload_file(img_file, 'empresas-logos', file_path)
        
        print(f"  ✅ Logo enviado com sucesso!")
        print(f"  📍 Caminho: {file_path}")
        print(f"  🔗 URL: {url}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao enviar logo: {str(e)}")
        return False


def test_documento_upload():
    """Testa upload de documento"""
    print("\n📄 Testando upload de documento...")
    
    try:
        storage = SupabaseStorageHelper()
        pdf_file = create_test_pdf()
        
        # Simula o caminho
        now = datetime.now()
        file_path = f"documentos/{now.year}/{now.month:02d}/test_documento.pdf"
        
        # Upload
        url = storage.upload_file(pdf_file, 'documentos', file_path)
        
        print(f"  ✅ Documento enviado com sucesso!")
        print(f"  📍 Caminho: {file_path}")
        print(f"  🔗 URL: {url}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao enviar documento: {str(e)}")
        return False


def test_get_public_url():
    """Testa obtenção de URL pública"""
    print("\n🔗 Testando obtenção de URL pública...")
    
    try:
        storage = SupabaseStorageHelper()
        now = datetime.now()
        file_path = f"empresa1/{now.year}/{now.month:02d}/test_logo.png"
        
        # Busca URL
        url = storage.get_public_url('empresas-logos', file_path)
        
        print(f"  ✅ URL obtida com sucesso!")
        print(f"  🔗 URL: {url}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao obter URL: {str(e)}")
        return False


def test_delete_file():
    """Testa deleção de arquivo"""
    print("\n🗑️  Testando deleção de arquivo...")
    
    try:
        storage = SupabaseStorageHelper()
        now = datetime.now()
        file_path = f"empresa1/{now.year}/{now.month:02d}/test_logo.png"
        
        # Deleta arquivo
        storage.delete_file('empresas-logos', file_path)
        
        print(f"  ✅ Arquivo deletado com sucesso!")
        print(f"  📍 Caminho: {file_path}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erro ao deletar arquivo: {str(e)}")
        return False


def main():
    """Executa todos os testes"""
    print("="*60)
    print("🧪 TESTES DO SUPABASE STORAGE")
    print("="*60)
    
    resultados = {
        'Logo da Empresa': test_empresa_logo_upload(),
        'Documento': test_documento_upload(),
        'URL Pública': test_get_public_url(),
        'Deleção de Arquivo': test_delete_file(),
    }
    
    print("\n" + "="*60)
    print("📊 RESUMO DOS TESTES")
    print("="*60)
    
    sucesso = sum(1 for v in resultados.values() if v)
    total = len(resultados)
    
    for teste, resultado in resultados.items():
        status = "✅ OK" if resultado else "❌ FALHOU"
        print(f"  {status}: {teste}")
    
    print(f"\nResultado: {sucesso}/{total} testes passaram\n")
    
    if sucesso == total:
        print("🎉 Todos os testes passaram! Supabase Storage está pronto!\n")
        return 0
    else:
        print("⚠️  Alguns testes falharam. Verifique a configuração.\n")
        return 1


if __name__ == '__main__':
    exit(main())

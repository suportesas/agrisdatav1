#!/usr/bin/env python
"""
Script para acessar o Django do celular/tablet via WiFi
Permite compartilhar a aplicação Django local com outros dispositivos

Uso: python run_lan_server.py
"""

import os
import socket
import subprocess
import sys
from pathlib import Path

def get_local_ip():
    """Obtém o IP local da máquina (do WiFi/rede)"""
    try:
        # Conecta a um servidor externo sem realmente enviar dados
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_hostname():
    """Obtém o nome do computador"""
    return socket.gethostname()


def main():
    """Inicia o servidor Django acessível na rede local"""
    
    # Detectar IP local
    local_ip = get_local_ip()
    hostname = get_hostname()
    port = 8000
    
    print("="*70)
    print("🚀 SERVIDOR DJANGO - ACESSO VIA CELULAR/TABLET")
    print("="*70)
    print()
    
    print("📱 COMO ACESSAR DO SEU CELULAR:")
    print()
    print(f"  1. Certifique-se que o celular está NO MESMO WiFi do PC")
    print()
    print(f"  2. No celular, abra o navegador e acesse:")
    print()
    print(f"     ✅ http://{local_ip}:8000")
    print()
    print(f"     ou")
    print()
    print(f"     ✅ http://{hostname}.local:8000")
    print()
    print("="*70)
    print()
    print("📊 DETALHES DA REDE:")
    print(f"  • IP do PC:      {local_ip}")
    print(f"  • Nome do PC:    {hostname}")
    print(f"  • Porta:         {port}")
    print(f"  • Banco de Dados: Supabase (PostgreSQL na nuvem)")
    print()
    print("="*70)
    print()
    print("⚠️  IMPORTANTE:")
    print("  • O celular DEVE estar no mesmo WiFi do PC")
    print("  • Se usar rede móvel 4G/5G, NÃO vai funcionar")
    print("  • Para acessar de fora, você vai precisar fazer deploy")
    print("    em um servidor (Heroku, Railway, AWS, etc)")
    print()
    print("🔧 INICIANDO SERVIDOR...")
    print("="*70)
    print()
    
    # Iniciar servidor Django
    try:
        # runserver 0.0.0.0:8000 faz o Django escutar em todos os IPs
        cmd = [
            sys.executable,
            "manage.py",
            "runserver",
            f"0.0.0.0:{port}"
        ]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n⏹️  Servidor parado pelo usuário")
        exit(0)
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        exit(1)


if __name__ == '__main__':
    # Verificar se estamos no diretório certo
    if not Path('manage.py').exists():
        print("❌ Erro: manage.py não encontrado")
        print("Execute este script a partir da raiz do projeto Django")
        exit(1)
    
    main()

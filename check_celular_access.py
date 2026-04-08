#!/usr/bin/env python
"""
Script para mostrar informações de acesso remoto do Django
Mostra IP local para acessar do celular/tablet
"""

import socket
import subprocess
import platform

def get_local_ip():
    """Obtém o IP local da máquina"""
    try:
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


def get_mac_address():
    """Obtém o endereço MAC (Windows)"""
    try:
        result = subprocess.run(
            ['getmac'],
            capture_output=True,
            text=True,
            timeout=5
        )
        mac = result.stdout.split()[0] if result.stdout else "N/A"
        return mac
    except Exception:
        return "N/A"


def main():
    """Mostra informações de acesso remoto"""
    
    local_ip = get_local_ip()
    hostname = get_hostname()
    system = platform.system()
    mac = get_mac_address()
    port = 8000
    
    print("\n" + "="*80)
    print("📱 ACESSO AO DJANGO DO CELULAR/TABLET VIA WIFI".center(80))
    print("="*80)
    print()
    
    print("✅ SIM! Agora que seu banco está no Supabase, você pode acessar do celular!")
    print()
    
    print("🌐 COMO ACESSAR:")
    print()
    print(f"  1️⃣  No seu PC, execute:")
    print(f"      python run_lan_server.py")
    print()
    print(f"  2️⃣  No seu CELULAR (mesmo WiFi), abra o navegador:")
    print()
    print(f"      🔗 http://{local_ip}:8000")
    print()
    print(f"      ou")
    print()
    print(f"      🔗 http://{hostname}.local:8000")
    print()
    
    print("="*80)
    print("🖥️  INFORMAÇÕES DA SUA REDE:")
    print("="*80)
    print()
    print(f"  IP do PC:          {local_ip}")
    print(f"  Nome do PC:        {hostname}")
    print(f"  Sistema:           {system}")
    print(f"  Endereço MAC:      {mac}")
    print(f"  Porta Django:      {port}")
    print()
    
    print("="*80)
    print("🔐 BANCO DE DADOS:")
    print("="*80)
    print()
    print(f"  ✅ Localização: Supabase (NUVEM)")
    print(f"  ✅ Acessível de: Qualquer lugar")
    print(f"  ✅ Banco: PostgreSQL 17.6")
    print()
    
    print("="*80)
    print("⚠️  REQUISITOS:")
    print("="*80)
    print()
    print("  ✓ Celular DEVE estar no MESMO WiFi do PC")
    print("  ✓ Coloque-se na mesma rede WiFi")
    print("  ✓ Não funciona com dados móveis 4G/5G")
    print()
    
    print("="*80)
    print("🚀 PARA ACESSAR DE QUALQUER LUGAR:")
    print("="*80)
    print()
    print("  Se quiser acessar de fora do WiFi (de 4G/5G, mobiledata, etc):")
    print()
    print("  1. Faça DEPLOY on-line em:")
    print("     • Heroku")
    print("     • Railway.app (recomendado)")
    print("     • Render.com")
    print("     • AWS")
    print("     • Digital Ocean")
    print()
    print("  2. Configure variáveis de ambiente no servidor")
    print("  3. Django rodará en uma URL pública (ex: https://seu-app.railway.app)")
    print()
    print("="*80)
    print()
    print("👉 PRÓXIMOS PASSOS:")
    print()
    print("  1. Execute: python run_lan_server.py")
    print("  2. Pegue o IP: " + local_ip)
    print("  3. No celular: Abra http://" + local_ip + ":8000")
    print()
    print("="*80 + "\n")


if __name__ == '__main__':
    main()

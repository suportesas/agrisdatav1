"""
Script para criar migrações multi-tenant de forma automática
Fornece respostas padrão para os prompts do Django
"""
import subprocess
import sys

# Respostas automáticas:
# 1 = Provide a one-off default now
# 1 = Valor padrão (ID da empresa 1)
responses = "1\n1\n1\n1\n1\n1\n"

process = subprocess.Popen(
    [sys.executable, "manage.py", "makemigrations", "produtos"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

stdout, stderr = process.communicate(input=responses)

print(stdout)
if stderr:
    print("STDERR:", stderr)

sys.exit(process.returncode)

from cadastros.models import EmpresaCFOP, CFOP
from empresas.models import Empresa

emp = Empresa.objects.first()
empresa_cfop_codigos = set(EmpresaCFOP.objects.filter(empresa=emp, ativo=True).values_list('codigo', flat=True))
global_cfop_codigos = set(CFOP.objects.filter(ativo=True).values_list('codigo', flat=True))

nao_encontrados = empresa_cfop_codigos - global_cfop_codigos

print(f"Empresa: {emp}")
print(f"CFOPs em EmpresaCFOP que NÃO existem na tabela global CFOP:")
for codigo in sorted(nao_encontrados):
    print(f"  - {codigo}")

if not nao_encontrados:
    print("Todos os CFOPs da empresa existem na tabela global.")

import importlib, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
m = importlib.import_module('cadastros.models')
print('DocumentoFazenda' in dir(m))
if 'DocumentoFazenda' in dir(m):
    cls = getattr(m, 'DocumentoFazenda')
    try:
        fields = [f.name for f in cls._meta.get_fields()]
        print('fields:', fields)
    except Exception as e:
        print('Error introspecting _meta:', e)
    print('attrs present:', [a for a in dir(cls) if a in ('data_validade','numero_documento','arquivo','gerar_alerta_vencimento','data_emissao')])

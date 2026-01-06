import os
import re

fields = [
    'empresa','codigo','tipo_cliente','tipo_pessoa','razao_social','nome_comercial','cnpj_cpf','status',
    'inscricao_estadual','inscricao_municipal','eori','vat','regime_tributario','contribuinte_icms','indicador_ie',
    'inscricao_suframa','limite_credito','prazo_pagamento','prazo_pagamento_padrao','forma_pagamento_padrao',
    'desconto_padrao','vendedor_responsavel','observacoes_comerciais','pais','moeda_padrao','porto_destino',
    'incoterm_padrao','idioma_preferido','certificacoes_exigidas','contato_principal_nome','contato_principal_telefone',
    'contato_principal_email','acesso_portal','usuario_vinculado','cadastrado_por','data_cadastro','data_atualizacao'
]

templates = [
    'cadastros/templates/cadastros/cliente/cliente_form.html',
    'cadastros/templates/cadastros/cliente/cliente_detail.html',
    'cadastros/templates/cadastros/cliente/cliente_list.html'
]

results = {t: {} for t in templates}

for t in templates:
    if not os.path.exists(t):
        continue
    text = open(t, encoding='utf-8').read()
    for f in fields:
        results[t][f] = bool(re.search(r"\b" + re.escape(f) + r"\b", text))

print('Field presence in templates (True = present)')
print('Field, form, detail, list')
for f in fields:
    vals = [results.get(templates[0],{}).get(f, False), results.get(templates[1],{}).get(f, False), results.get(templates[2],{}).get(f, False)]
    print(f + ',', ','.join(['Y' if v else 'N' for v in vals]))

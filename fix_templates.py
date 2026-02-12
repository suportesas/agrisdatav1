#!/usr/bin/env python
import os

templates = [
    'cadastros/templates/cadastros/armador/list.html',
    'cadastros/templates/cadastros/armador/detail.html',
    'cadastros/templates/cadastros/armador/form.html',
    'cadastros/templates/cadastros/armador/confirm_delete.html',
    'cadastros/templates/cadastros/armador/endereco_form.html',
    'cadastros/templates/cadastros/armador/contato_form.html',
    'cadastros/templates/cadastros/armador/banco_form.html',
    'cadastros/templates/cadastros/navio/list.html',
    'cadastros/templates/cadastros/navio/detail.html',
    'cadastros/templates/cadastros/navio/form.html',
    'cadastros/templates/cadastros/navio/confirm_delete.html'
]

replacements = [
    ("{% url 'armador_list' %}", "{% url 'cadastros:armador_list' %}"),
    ("{% url 'armador_create' %}", "{% url 'cadastros:armador_create' %}"),
    ("{% url 'armador_detail' ", "{% url 'cadastros:armador_detail' "),
    ("{% url 'armador_update' ", "{% url 'cadastros:armador_update' "),
    ("{% url 'armador_delete' ", "{% url 'cadastros:armador_delete' "),
    ("{% url 'armador_endereco_create' ", "{% url 'cadastros:armador_endereco_create' "),
    ("{% url 'armador_endereco_update' ", "{% url 'cadastros:armador_endereco_update' "),
    ("{% url 'armador_endereco_delete' ", "{% url 'cadastros:armador_endereco_delete' "),
    ("{% url 'armador_contato_create' ", "{% url 'cadastros:armador_contato_create' "),
    ("{% url 'armador_contato_update' ", "{% url 'cadastros:armador_contato_update' "),
    ("{% url 'armador_contato_delete' ", "{% url 'cadastros:armador_contato_delete' "),
    ("{% url 'armador_banco_create' ", "{% url 'cadastros:armador_banco_create' "),
    ("{% url 'armador_banco_update' ", "{% url 'cadastros:armador_banco_update' "),
    ("{% url 'armador_banco_delete' ", "{% url 'cadastros:armador_banco_delete' "),
    ("{% url 'navio_list' %}", "{% url 'cadastros:navio_list' %}"),
    ("{% url 'navio_create' %}", "{% url 'cadastros:navio_create' %}"),
    ("{% url 'navio_detail' ", "{% url 'cadastros:navio_detail' "),
    ("{% url 'navio_update' ", "{% url 'cadastros:navio_update' "),
    ("{% url 'navio_delete' ", "{% url 'cadastros:navio_delete' "),
]

for template in templates:
    if os.path.exists(template):
        with open(template, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        with open(template, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f'✓ {template}')

print('\n✓ Todos os templates foram corrigidos!')

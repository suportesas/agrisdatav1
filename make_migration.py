#!/usr/bin/env python
"""Script para criar a migração do Armador"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

try:
    call_command('makemigrations', 'cadastros', verbosity=2)
    print("\n✓ Migração criada com sucesso!")
except Exception as e:
    print(f"\n✗ Erro ao criar migração: {e}")
    sys.exit(1)

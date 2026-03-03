#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.apps import apps

financeiro_app = apps.get_app_config('financeiro')
print(f"App: {financeiro_app.name}")
models_list = [m.__name__ for m in financeiro_app.get_models()]
print(f"Models found: {models_list}")
print(f"Total models: {len(models_list)}")

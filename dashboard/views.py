from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def index(request):
    context = {
        'profissionais_cadastrados': 5,
        'profissionais_ativos': 5,
        'mrr': '0,00',
        'arr': '0,00',
        'churn': '0%',
        'consultas_mes': 12,
    }
    return render(request, 'dashboard.html', context)

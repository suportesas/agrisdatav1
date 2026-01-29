from django.shortcuts import render
from django.http import HttpResponse

def template_teste(request):
    return render(request, 'compras/cotacao/cotacao_form.html', {'title': 'Teste Template'})

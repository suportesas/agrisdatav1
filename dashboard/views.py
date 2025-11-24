from django.contrib.auth.decorators import login_required
from django.shortcuts import render

#@login_required
#def index(request):
    #return render(request, 'dashboard/index.html')


# Em dashboard/views.py
@login_required
def index(request):
    empresa = request.user.empresa
    
    context = {
        'total_fazendas': empresa.fazendas.filter(ativa=True).count() if empresa else 0,
        'total_usuarios': empresa.usuarios.filter(is_active=True).count() if empresa else 0,
        # ... outros dados
    }
    return render(request, 'dashboard/index.html', context)



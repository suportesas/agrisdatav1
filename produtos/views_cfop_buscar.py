from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from cadastros.models import CFOP

@login_required
def cfop_buscar_ajax(request):
    """
    View AJAX para buscar CFOP por código
    """
    if request.method == 'GET':
        codigo = request.GET.get('codigo', '').strip()
        
        if not codigo:
            return JsonResponse({
                'success': False,
                'error': 'Código CFOP não fornecido'
            }, status=400)
        
        try:
            # Buscar CFOP
            cfop = CFOP.objects.filter(codigo=codigo, ativo=True).first()
            
            if cfop:
                return JsonResponse({
                    'success': True,
                    'id': cfop.id,
                    'codigo': cfop.codigo,
                    'descricao': cfop.descricao
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'CFOP não encontrado'
                }, status=404)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)

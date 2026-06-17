from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Transportadora, Viagem
from django.forms.models import model_to_dict

@login_required
def api_transportadoras(request):
    """JSON list of transportadoras with filters and pagination"""
    qs = Transportadora.objects.filter(empresa=request.user.empresa)

    q = request.GET.get('q','').strip()
    if q:
        qs = qs.filter(razao_social__icontains=q)

    tipo = request.GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    uf = request.GET.get('uf')
    if uf:
        qs = qs.filter(uf=uf)

    page = int(request.GET.get('page', 1))
    per = int(request.GET.get('per', 20))

    paginator = Paginator(qs, per)
    page_obj = paginator.get_page(page)

    items = []
    for t in page_obj.object_list:
        items.append({
            'id': t.pk,
            'razao_social': t.razao_social,
            'nome_fantasia': t.nome_fantasia,
            'cnpj': t.cnpj,
            'tipo': t.tipo,
            'cidade': t.cidade,
            'uf': t.uf,
            'frete_padrao': str(t.frete_padrao) if t.frete_padrao is not None else None,
            'rntc': t.rntc or '',
            'total_viagens': t.viagens.count(),
        })

    return JsonResponse({
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'page': page_obj.number,
        'items': items
    })

@login_required
def api_transportadora_detail(request, pk):
    """Retorna dados completos de uma transportadora para auto-preenchimento."""
    t = Transportadora.objects.filter(pk=pk, empresa=request.user.empresa).first()
    if not t:
        return JsonResponse({'error': 'não encontrada'}, status=404)
    endereco = ' '.join(filter(None, [t.logradouro, t.numero, t.complemento])).strip()
    return JsonResponse({
        'cnpj':       t.cnpj or '',
        'nome':       t.razao_social or '',
        'ie':         t.inscricao_estadual or '',
        'endereco':   endereco,
        'municipio':  t.cidade or '',
        'uf':         t.uf or '',
        'rntc':       t.rntc or '',
    })

@login_required
def api_transportadora_viagens(request, pk):
    """JSON list of viagens for a transportadora with pagination/filters"""
    t = Transportadora.objects.filter(pk=pk, empresa=request.user.empresa).first()
    if not t:
        return JsonResponse({'erro': 'Transportadora não encontrada'}, status=404)

    qs = t.viagens.order_by('-data')
    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    page = int(request.GET.get('page', 1))
    per = int(request.GET.get('per', 20))
    paginator = Paginator(qs, per)
    page_obj = paginator.get_page(page)

    items = []
    for v in page_obj.object_list:
        items.append({
            'id': v.pk,
            'origem': v.origem,
            'destino': v.destino,
            'data': v.data.isoformat(),
            'valor_frete': str(v.valor_frete) if v.valor_frete is not None else None,
            'status': v.status,
        })

    return JsonResponse({
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'page': page_obj.number,
        'items': items
    })
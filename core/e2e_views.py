from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def e2e_log(request):
    """Recebe POSTs JSON com mensagens do console do navegador durante E2E e registra no servidor."""
    if not settings.DEBUG:
        return JsonResponse({'ok': False}, status=404)

    try:
        import json
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'ok': False}, status=400)

    msg = data.get('msg')
    url = data.get('url')
    extra = data.get('extra')
    logger.error('E2E CONSOLE [%s]: %s %s', url, msg, extra)
    return JsonResponse({'ok': True})
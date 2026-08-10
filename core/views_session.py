from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@require_POST
def session_heartbeat(request):
    """Endpoint chamado pelo heartbeat client-side (static/js/session-heartbeat.js).

    Não precisa de lógica própria: passar pela InactivityLogoutMiddleware já
    renova o `last_activity` da sessão. Existe só para dar ao JS um alvo leve
    para chamar sem navegar de página.
    """
    return JsonResponse({'ok': True})

from django.http import JsonResponse


def select2_response(request, queryset, serializer, page_size=10):
    """Builds a Select2-compatible paginated JSON response.

    `queryset` must already be filtered/searched/ordered by the caller — an
    empty `q` should mean "no filter" (first page of the default ordering),
    not an empty result, so the combobox has something to show on open.

    `serializer(obj)` returns the result dict for one row (must include at
    least 'id' and 'text').

    Fetches one row past the requested page to detect `pagination.more`
    without an extra COUNT query.
    """
    try:
        page = int(request.GET.get('page') or 1)
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    start = (page - 1) * page_size
    rows = list(queryset[start:start + page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    return JsonResponse({
        'results': [serializer(obj) for obj in rows],
        'pagination': {'more': has_more},
    })

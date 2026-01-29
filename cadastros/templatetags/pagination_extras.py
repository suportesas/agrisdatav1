from django import template

register = template.Library()

@register.simple_tag
def compact_page_range(page_obj, window=2):
    """Return a compact list of pages for pagination display.

    Example output: [1, '...', 4, 5, 6, '...', 10]
    """
    total = page_obj.paginator.num_pages
    current = page_obj.number
    pages = []

    start = max(1, current - window)
    end = min(total, current + window)

    if start > 1:
        pages.append(1)
        if start > 2:
            pages.append('...')

    for i in range(start, end + 1):
        pages.append(i)

    if end < total:
        if end < total - 1:
            pages.append('...')
        pages.append(total)

    return pages

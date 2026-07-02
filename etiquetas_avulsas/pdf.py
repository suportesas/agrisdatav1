import io

from django.template.loader import render_to_string
from xhtml2pdf import pisa

from core.barcode_utils import barcode_b64


def render_etiqueta_avulsa_pdf(etiquetas):
    """Gera PDF com uma etiqueta por página para cada EtiquetaAvulsa informada."""
    etiquetas_ctx = [{
        'etiqueta': e,
        'lote': e.lote,
        'barcode_b64': barcode_b64(e.codigo_pallet),
    } for e in etiquetas]

    html = render_to_string('etiquetas_avulsas/etiqueta_pdf.html', {
        'etiquetas_ctx': etiquetas_ctx,
    })
    buffer = io.BytesIO()
    pisa.CreatePDF(html, dest=buffer)
    buffer.seek(0)
    return buffer.read()

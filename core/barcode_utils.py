import base64
import io


def barcode_b64(codigo):
    """Gera um Code128 em base64 (PNG) para embutir em PDFs de etiqueta."""
    try:
        import barcode as pybarcode
        cls = pybarcode.get_barcode_class('code128')
        buf = io.BytesIO()
        cls(codigo, writer=pybarcode.writer.ImageWriter()).write(buf, options={
            'module_height': 10, 'module_width': 0.4, 'quiet_zone': 2,
            'text_distance': 1, 'font_size': 7, 'write_text': False,
        })
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
    except Exception:
        return None

# Módulo movido para emprestimos/views.py
# Este arquivo existe apenas para compatibilidade de importações legadas.
from emprestimos.views import (  # noqa: F401
    atualizar_promessas_vencidas,
    emprestimo_assinar_liberacao,
    emprestimo_detalhe,
    emprestimo_devolucao_create,
    emprestimo_exportar_excel,
    emprestimo_exportar_pdf,
    emprestimo_extrato,
    emprestimo_extrato_imprimir,
    emprestimo_imprimir,
    emprestimo_mensagem_anexo_download,
    emprestimo_mensagem_create,
    emprestimo_reenviar_whatsapp,
    registrar_alerta_visual_exibido,
)

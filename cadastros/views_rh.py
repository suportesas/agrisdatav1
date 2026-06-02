# Módulo movido para rh/views.py
# Este arquivo existe apenas para compatibilidade de importações legadas.
from rh.views import (  # noqa: F401
    rh_dashboard,
    ferias_list, ferias_previsao_pdf, ferias_create, ferias_detail, ferias_update, ferias_delete,
    afastamento_list, afastamento_create, afastamento_detail, afastamento_update, afastamento_delete,
    vinculo_list, vinculo_create, vinculo_detail, vinculo_update,
    laudo_list, laudo_create, laudo_detail, laudo_update,
    tipo_exame_aso_list, tipo_exame_aso_create, tipo_exame_aso_update, tipo_exame_aso_toggle_ativo,
    aso_solicitacao_list, aso_solicitacao_create, aso_funcionario_riscos, aso_buscar_laboratorio,
    aso_solicitacao_detail, aso_solicitacao_update, aso_solicitacao_assinar,
    aso_solicitacao_pdf, aso_solicitacao_enviar_email, aso_solicitacao_enviar_whatsapp,
    rescisao_list, rescisao_create, vinculos_por_funcionario, rescisao_calcular,
    rescisao_detail, rescisao_update, rescisao_delete,
    relatorio_rh, relatorio_rh_pdf,
)

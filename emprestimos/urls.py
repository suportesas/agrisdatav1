from django.urls import path
from . import views

app_name = 'emprestimos'

urlpatterns = [
    path('ajax/registrar-alerta-visual/', views.registrar_alerta_visual_exibido, name='registrar_alerta_visual_exibido'),
    path('extrato/', views.emprestimo_extrato, name='emprestimo_extrato'),
    path('extrato/imprimir/', views.emprestimo_extrato_imprimir, name='emprestimo_extrato_imprimir'),
    path('extrato/pdf/', views.emprestimo_exportar_pdf, name='emprestimo_exportar_pdf'),
    path('extrato/excel/', views.emprestimo_exportar_excel, name='emprestimo_exportar_excel'),
    path('devolucao/nova/', views.emprestimo_devolucao_create, name='emprestimo_devolucao_create'),
    path('mensagens/anexos/<int:anexo_id>/download/', views.emprestimo_mensagem_anexo_download, name='emprestimo_mensagem_anexo_download'),
    path('<int:pk>/', views.emprestimo_detalhe, name='emprestimo_detalhe'),
    path('<int:pk>/imprimir/', views.emprestimo_imprimir, name='emprestimo_imprimir'),
    path('<int:pk>/assinar-liberacao/', views.emprestimo_assinar_liberacao, name='emprestimo_assinar_liberacao'),
    path('<int:pk>/reenviar-whatsapp/', views.emprestimo_reenviar_whatsapp, name='emprestimo_reenviar_whatsapp'),
    path('<int:pk>/mensagens/nova/', views.emprestimo_mensagem_create, name='emprestimo_mensagem_create'),
]

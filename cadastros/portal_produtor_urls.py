
from django.urls import path

from . import portal_produtor_views as views

app_name = 'portal_produtor'

urlpatterns = [
    path('login/', views.portal_login, name='login'),
    path('devolucoes/', views.devolucoes_programadas, name='devolucoes_programadas'),
    path('', views.dashboard, name='dashboard'),
    path('emprestimos/', views.emprestimos_list, name='emprestimos_list'),
    path('emprestimos/<int:pk>/', views.emprestimo_detail, name='emprestimo_detail'),
    path('emprestimos/<int:pk>/assinar/', views.emprestimo_assinar, name='emprestimo_assinar'),
    path('emprestimos/<int:pk>/mensagens/nova/', views.emprestimo_mensagem_create, name='emprestimo_mensagem_create'),
    path('mensagens/anexos/<int:anexo_id>/download/', views.emprestimo_mensagem_anexo_download, name='emprestimo_mensagem_anexo_download'),
    path('perfil/', views.perfil_produtor, name='perfil'),
    path('trocar-senha/', views.trocar_senha_produtor, name='trocar_senha'),
    path('emprestimos/ajax/aceite/', views.emprestimo_aceite_ajax, name='emprestimo_aceite_ajax'),
]
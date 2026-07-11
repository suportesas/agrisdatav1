from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsuarioComEmpresaBackend(ModelBackend):
    """ModelBackend padrão, mas carrega request.user já com select_related('empresa').

    Elimina a query lazy de user.empresa disparada em
    core/middleware/empresa_bloqueada.py e em qualquer outro ponto que acesse
    request.user.empresa pela primeira vez na request.
    """

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel._default_manager.select_related('empresa').get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

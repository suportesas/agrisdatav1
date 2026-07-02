from rest_framework.routers import DefaultRouter

from .views import LoteEtiquetaAvulsaViewSet

app_name = 'etiquetas_avulsas_api'

router = DefaultRouter()
router.register('lotes', LoteEtiquetaAvulsaViewSet, basename='lote')

urlpatterns = router.urls

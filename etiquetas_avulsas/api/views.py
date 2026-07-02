from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from core.feature_flags import is_feature_enabled

from ..models import EtiquetaAvulsa
from ..pdf import render_etiqueta_avulsa_pdf
from .authentication import APIKeyAuthentication
from .serializers import LoteEtiquetaAvulsaCreateSerializer, LoteEtiquetaAvulsaSerializer


class FeatureFlagEnabledPermission(IsAuthenticated):
    """Bloqueia o acesso quando a feature flag ETIQUETA_AVULSA_API estiver desligada."""

    def has_permission(self, request, view):
        if not is_feature_enabled('ETIQUETA_AVULSA_API'):
            raise PermissionDenied('Recurso não disponível.')
        return super().has_permission(request, view)


class LoteEtiquetaAvulsaViewSet(mixins.CreateModelMixin, mixins.ListModelMixin,
                                 mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [FeatureFlagEnabledPermission]
    serializer_class = LoteEtiquetaAvulsaSerializer

    def get_queryset(self):
        return self.request.user.empresa.lotes_etiqueta_avulsa.all().prefetch_related('etiquetas')

    def get_serializer_class(self):
        if self.action == 'create':
            return LoteEtiquetaAvulsaCreateSerializer
        return LoteEtiquetaAvulsaSerializer

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa, origem='API', api_key=self.request.auth)

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        lote = self.get_object()
        etiquetas = list(lote.etiquetas.filter(ativo=True).order_by('numero_sequencial'))
        pdf_bytes = render_etiqueta_avulsa_pdf(etiquetas)
        EtiquetaAvulsa.objects.filter(pk__in=[e.pk for e in etiquetas]).update(
            status='IMPRESSA', impressa_em=timezone.now())
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'inline; filename="{lote.numero_lote}.pdf"'
        return resp

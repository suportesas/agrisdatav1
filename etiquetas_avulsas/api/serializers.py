from rest_framework import serializers

from ..models import EtiquetaAvulsa, LoteEtiquetaAvulsa
from ..services import criar_lote_com_etiquetas


class EtiquetaAvulsaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtiquetaAvulsa
        fields = ['id', 'codigo_pallet', 'numero_sequencial', 'caixas', 'status']


class LoteEtiquetaAvulsaSerializer(serializers.ModelSerializer):
    etiquetas = EtiquetaAvulsaSerializer(many=True, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = LoteEtiquetaAvulsa
        fields = [
            'id', 'numero_lote', 'origem',
            'safra_texto', 'fazenda_texto', 'cliente_texto', 'cliente_final_texto',
            'porto_origem_texto', 'porto_destino_texto', 'navio_texto',
            'produto_texto', 'variedade', 'embalagem', 'marca', 'cultivares',
            'tipo_size', 'temperatura', 'carimbo',
            'caixas_por_pallet', 'peso_liquido_cx', 'peso_bruto_cx',
            'total_pallets', 'comentarios', 'criado_em',
            'etiquetas', 'pdf_url',
        ]
        read_only_fields = ['id', 'numero_lote', 'origem', 'criado_em']

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        from django.urls import reverse
        url = reverse('etiquetas_avulsas_api:lote-pdf', kwargs={'pk': obj.pk})
        return request.build_absolute_uri(url) if request else url


class LoteEtiquetaAvulsaCreateSerializer(serializers.ModelSerializer):
    """Serializer de criação para clientes externos: só campos texto livre,
    sem IDs de FK, já que clientes via API não têm os cadastros do ERP."""

    class Meta:
        model = LoteEtiquetaAvulsa
        fields = [
            'safra_texto', 'fazenda_texto', 'cliente_texto', 'cliente_final_texto',
            'porto_origem_texto', 'porto_destino_texto', 'navio_texto',
            'produto_texto', 'variedade', 'embalagem', 'marca', 'cultivares',
            'tipo_size', 'temperatura', 'carimbo',
            'caixas_por_pallet', 'peso_liquido_cx', 'peso_bruto_cx',
            'total_pallets', 'comentarios',
        ]

    def validate_total_pallets(self, value):
        if value < 1:
            raise serializers.ValidationError('Informe pelo menos 1 pallet.')
        return value

    def validate_caixas_por_pallet(self, value):
        if value < 1:
            raise serializers.ValidationError('Deve haver pelo menos 1 caixa por pallet.')
        return value

    def create(self, validated_data):
        empresa = validated_data['empresa']
        lote = LoteEtiquetaAvulsa(**validated_data)
        return criar_lote_com_etiquetas(lote, empresa)

    def to_representation(self, instance):
        return LoteEtiquetaAvulsaSerializer(instance, context=self.context).data

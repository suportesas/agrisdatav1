from rest_framework import serializers

from ..models import EtiquetaAvulsa, LoteEtiquetaAvulsa
from ..services import criar_lote_com_etiquetas


class EtiquetaAvulsaSerializer(serializers.ModelSerializer):
    produto_nome = serializers.ReadOnlyField()
    marca_nome = serializers.ReadOnlyField()

    class Meta:
        model = EtiquetaAvulsa
        fields = [
            'id', 'codigo_pallet', 'numero_sequencial', 'caixas', 'status',
            'produto_texto', 'produto_nome', 'variedade', 'embalagem',
            'marca_texto', 'marca_nome',
            'cultivares', 'tipo_size', 'temperatura', 'carimbo',
            'peso_liquido_cx', 'peso_bruto_cx',
        ]


class LoteEtiquetaAvulsaSerializer(serializers.ModelSerializer):
    etiquetas = EtiquetaAvulsaSerializer(many=True, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = LoteEtiquetaAvulsa
        fields = [
            'id', 'numero_lote', 'origem', 'status',
            'safra_texto', 'fazenda_texto', 'cliente_texto', 'cliente_final_texto',
            'porto_origem_texto', 'porto_destino_texto', 'navio_texto',
            'total_pallets', 'comentarios', 'criado_em',
            'etiquetas', 'pdf_url',
        ]
        read_only_fields = ['id', 'numero_lote', 'origem', 'status', 'total_pallets', 'criado_em']

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        from django.urls import reverse
        url = reverse('etiquetas_avulsas_api:lote-pdf', kwargs={'pk': obj.pk})
        return request.build_absolute_uri(url) if request else url


class LoteEtiquetaAvulsaCreateSerializer(serializers.Serializer):
    """Serializer de criação para clientes externos: só campos texto livre,
    sem IDs de FK, já que clientes via API não têm os cadastros do ERP.

    Cria o lote (carga) e sua primeira leva de pallets — `total_pallets`
    aqui é a quantidade dessa primeira leva. Adicionar mais levas (de outro
    produto, por exemplo) a um lote existente não está disponível nesta
    API nesta fase."""

    # Carga — fixo para o lote inteiro
    safra_texto = serializers.CharField(required=False, allow_blank=True, max_length=10, default='')
    fazenda_texto = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    cliente_texto = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    cliente_final_texto = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    porto_origem_texto = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    porto_destino_texto = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    navio_texto = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    comentarios = serializers.CharField(required=False, allow_blank=True, default='')

    # Produto — desta primeira leva de pallets
    produto_texto = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    variedade = serializers.CharField(required=False, allow_blank=True, max_length=100, default='')
    embalagem = serializers.CharField(required=False, allow_blank=True, max_length=100, default='')
    marca_texto = serializers.CharField(required=False, allow_blank=True, max_length=100, default='')
    cultivares = serializers.CharField(required=False, allow_blank=True, max_length=150, default='')
    tipo_size = serializers.CharField(required=False, allow_blank=True, max_length=30, default='')
    temperatura = serializers.CharField(required=False, allow_blank=True, max_length=20, default='')
    carimbo = serializers.CharField(required=False, allow_blank=True, max_length=50, default='')
    peso_liquido_cx = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True, default=None)
    peso_bruto_cx = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True, default=None)
    caixas_por_pallet = serializers.IntegerField(min_value=1)
    total_pallets = serializers.IntegerField(min_value=1)

    LOTE_FIELDS = (
        'safra_texto', 'fazenda_texto', 'cliente_texto', 'cliente_final_texto',
        'porto_origem_texto', 'porto_destino_texto', 'navio_texto', 'comentarios',
    )
    ITEM_FIELDS = (
        'produto_texto', 'variedade', 'embalagem', 'marca_texto', 'cultivares',
        'tipo_size', 'temperatura', 'carimbo', 'peso_liquido_cx', 'peso_bruto_cx',
    )

    def create(self, validated_data):
        empresa = validated_data['empresa']
        lote = LoteEtiquetaAvulsa(
            origem=validated_data['origem'],
            api_key=validated_data.get('api_key'),
            **{campo: validated_data.get(campo, '') for campo in self.LOTE_FIELDS},
        )
        item_data = {campo: validated_data.get(campo) for campo in self.ITEM_FIELDS}
        item_data['caixas_por_pallet'] = validated_data['caixas_por_pallet']
        quantidade = validated_data['total_pallets']
        return criar_lote_com_etiquetas(lote, empresa, quantidade, item_data)

    def to_representation(self, instance):
        return LoteEtiquetaAvulsaSerializer(instance, context=self.context).data

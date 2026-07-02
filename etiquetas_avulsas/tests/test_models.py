from django.test import TestCase

from empresas.models import Empresa, Plano
from etiquetas_avulsas.models import EtiquetaAvulsa, LoteEtiquetaAvulsa
from etiquetas_avulsas.services import criar_lote_com_etiquetas


class LoteEtiquetaAvulsaModelTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQUENO', nome='Pequeno', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=plano)
        self.outra_empresa = Empresa.objects.create(nome='Outra Empresa', plano=plano)

    def _novo_lote(self, empresa, total_pallets=5, caixas_por_pallet=98):
        lote = LoteEtiquetaAvulsa(
            origem='UI',
            fazenda_texto='Fazenda Teste',
            cliente_texto='Cliente Teste',
            produto_texto='Melão',
            caixas_por_pallet=caixas_por_pallet,
            total_pallets=total_pallets,
        )
        return criar_lote_com_etiquetas(lote, empresa)

    def test_gera_numero_lote_sequencial(self):
        lote1 = self._novo_lote(self.empresa, total_pallets=2)
        lote2 = self._novo_lote(self.empresa, total_pallets=2)
        self.assertNotEqual(lote1.numero_lote, lote2.numero_lote)
        self.assertTrue(lote1.numero_lote.startswith('LTA-'))

    def test_gera_etiquetas_sequenciais_com_mesmas_especificacoes(self):
        lote = self._novo_lote(self.empresa, total_pallets=5, caixas_por_pallet=98)
        etiquetas = list(lote.etiquetas.order_by('numero_sequencial'))
        self.assertEqual(len(etiquetas), 5)
        for i, etiqueta in enumerate(etiquetas, start=1):
            self.assertEqual(etiqueta.numero_sequencial, i)
            self.assertEqual(etiqueta.caixas, 98)
            self.assertEqual(etiqueta.status, 'GERADA')

    def test_codigos_pallet_sao_unicos_entre_lotes(self):
        lote1 = self._novo_lote(self.empresa, total_pallets=3)
        lote2 = self._novo_lote(self.empresa, total_pallets=3)
        codigos1 = set(lote1.etiquetas.values_list('codigo_pallet', flat=True))
        codigos2 = set(lote2.etiquetas.values_list('codigo_pallet', flat=True))
        self.assertEqual(len(codigos1 & codigos2), 0)

    def test_fallback_texto_quando_sem_fk(self):
        lote = self._novo_lote(self.empresa, total_pallets=1)
        self.assertEqual(lote.fazenda_nome, 'Fazenda Teste')
        self.assertEqual(lote.cliente_nome, 'Cliente Teste')
        self.assertEqual(lote.produto_nome, 'Melão')

    def test_empresas_diferentes_podem_repetir_numero_lote_e_codigo_pallet(self):
        """Regressão: numero_lote/codigo_pallet devem ser únicos por empresa, não globalmente
        — cada empresa reinicia sua própria sequência (ex: ambas geram 'LTA-2026-0001')."""
        lote_empresa1 = self._novo_lote(self.empresa, total_pallets=1)
        lote_empresa2 = self._novo_lote(self.outra_empresa, total_pallets=1)
        self.assertEqual(lote_empresa1.numero_lote, lote_empresa2.numero_lote)
        etiqueta1 = lote_empresa1.etiquetas.first()
        etiqueta2 = lote_empresa2.etiquetas.first()
        self.assertEqual(etiqueta1.codigo_pallet, etiqueta2.codigo_pallet)

    def _novo_lote_com_safra(self, empresa, safra_texto, total_pallets=3, caixas_por_pallet=10):
        lote = LoteEtiquetaAvulsa(
            origem='UI', safra_texto=safra_texto, fazenda_texto='Fazenda Teste',
            caixas_por_pallet=caixas_por_pallet, total_pallets=total_pallets,
        )
        return criar_lote_com_etiquetas(lote, empresa)

    def test_codigo_pallet_usa_prefixo_da_safra_e_continua_entre_lotes(self):
        lote1 = self._novo_lote_com_safra(self.empresa, '202627', total_pallets=5)
        codigos1 = list(lote1.etiquetas.order_by('numero_sequencial').values_list('codigo_pallet', flat=True))
        self.assertEqual(codigos1, [f'202627-{i}' for i in range(1, 6)])

        # Segundo lote da MESMA safra continua a sequência (não reinicia)
        lote2 = self._novo_lote_com_safra(self.empresa, '202627', total_pallets=2)
        codigos2 = list(lote2.etiquetas.order_by('numero_sequencial').values_list('codigo_pallet', flat=True))
        self.assertEqual(codigos2, ['202627-6', '202627-7'])

    def test_codigo_pallet_reinicia_ao_trocar_de_safra(self):
        self._novo_lote_com_safra(self.empresa, '202627', total_pallets=3)
        lote_outra_safra = self._novo_lote_com_safra(self.empresa, '202728', total_pallets=2)
        codigos = list(lote_outra_safra.etiquetas.order_by('numero_sequencial').values_list('codigo_pallet', flat=True))
        self.assertEqual(codigos, ['202728-1', '202728-2'])

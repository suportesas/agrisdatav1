from django.test import TestCase

from empresas.models import Empresa, Plano
from etiquetas_avulsas.models import EtiquetaAvulsa, LoteEtiquetaAvulsa
from etiquetas_avulsas.services import (
    LoteConcluidoError, adicionar_pallets, concluir_lote, criar_lote_com_etiquetas,
)


def item_data(produto_texto='Melão', caixas_por_pallet=98, **overrides):
    data = {
        'produto': None, 'produto_texto': produto_texto, 'cultura': None,
        'variedade': '', 'embalagem': '', 'marca': None, 'marca_texto': '', 'cultivares': '',
        'tipo_size': '', 'temperatura': '', 'carimbo': '',
        'peso_liquido_cx': None, 'peso_bruto_cx': None,
        'caixas_por_pallet': caixas_por_pallet,
    }
    data.update(overrides)
    return data


class LoteEtiquetaAvulsaModelTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQUENO', nome='Pequeno', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=plano)
        self.outra_empresa = Empresa.objects.create(nome='Outra Empresa', plano=plano)

    def _novo_lote(self, empresa, total_pallets=5, caixas_por_pallet=98):
        lote = LoteEtiquetaAvulsa(
            origem='UI', fazenda_texto='Fazenda Teste', cliente_texto='Cliente Teste',
        )
        return criar_lote_com_etiquetas(
            lote, empresa, total_pallets, item_data(caixas_por_pallet=caixas_por_pallet))

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
            self.assertEqual(etiqueta.produto_texto, 'Melão')

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
        self.assertEqual(lote.etiquetas.first().produto_nome, 'Melão')

    def test_marca_fk_tem_prioridade_sobre_marca_texto(self):
        from produtos.models import Marca
        marca = Marca.objects.create(empresa=self.empresa, nome='Terra Brasilis')
        lote = self._novo_lote(self.empresa, total_pallets=1)
        etiqueta = lote.etiquetas.first()
        etiqueta.marca = marca
        etiqueta.marca_texto = 'Ignorada'
        etiqueta.save()
        self.assertEqual(etiqueta.marca_nome, 'Terra Brasilis')

    def test_marca_texto_como_fallback_sem_cadastro(self):
        lote = self._novo_lote(self.empresa, total_pallets=1)
        etiqueta = lote.etiquetas.first()
        etiqueta.marca_texto = 'Marca Sem Cadastro'
        etiqueta.save()
        self.assertEqual(etiqueta.marca_nome, 'Marca Sem Cadastro')

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
        lote = LoteEtiquetaAvulsa(origem='UI', safra_texto=safra_texto, fazenda_texto='Fazenda Teste')
        return criar_lote_com_etiquetas(
            lote, empresa, total_pallets, item_data(caixas_por_pallet=caixas_por_pallet))

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


class AdicionarPalletsServiceTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQUENO', nome='Pequeno', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=plano)

    def _novo_lote(self, total_pallets=2, safra_texto='', produto_texto='Melão'):
        lote = LoteEtiquetaAvulsa(origem='UI', safra_texto=safra_texto, fazenda_texto='Fazenda Teste')
        return criar_lote_com_etiquetas(
            lote, self.empresa, total_pallets, item_data(produto_texto=produto_texto, caixas_por_pallet=10))

    def test_lote_nasce_aberta(self):
        lote = self._novo_lote()
        self.assertEqual(lote.status, 'ABERTA')

    def test_adicionar_pallets_sem_safra_reaproveita_base_do_lote(self):
        lote = self._novo_lote(total_pallets=2)
        base_original = lote.etiquetas.first().codigo_pallet.rsplit('-', 1)[0]

        lote = adicionar_pallets(lote, self.empresa, 3, item_data(caixas_por_pallet=10))

        etiquetas = list(lote.etiquetas.order_by('numero_sequencial'))
        self.assertEqual(len(etiquetas), 5)
        self.assertEqual([e.numero_sequencial for e in etiquetas], [1, 2, 3, 4, 5])
        bases = {e.codigo_pallet.rsplit('-', 1)[0] for e in etiquetas}
        self.assertEqual(bases, {base_original})
        self.assertEqual(lote.total_pallets, 5)

    def test_adicionar_pallets_pode_usar_produto_diferente(self):
        """Uma carga pode misturar mais de um produto entre levas."""
        lote = self._novo_lote(total_pallets=2, produto_texto='Melão')
        lote = adicionar_pallets(lote, self.empresa, 3, item_data(produto_texto='Melancia', caixas_por_pallet=15))

        etiquetas = list(lote.etiquetas.order_by('numero_sequencial'))
        self.assertEqual([e.produto_texto for e in etiquetas[:2]], ['Melão', 'Melão'])
        self.assertEqual([e.produto_texto for e in etiquetas[2:]], ['Melancia'] * 3)
        self.assertEqual([e.caixas for e in etiquetas[2:]], [15, 15, 15])
        self.assertIn('Melão', lote.produtos_resumo)
        self.assertIn('Melancia', lote.produtos_resumo)

    def test_adicionar_pallets_com_safra_continua_contador_global_mas_sequencial_por_lote(self):
        lote_a = self._novo_lote(total_pallets=3, safra_texto='202627')
        self._novo_lote(total_pallets=2, safra_texto='202627')  # lote B, intercala 202627-4/5

        lote_a = adicionar_pallets(lote_a, self.empresa, 2, item_data(caixas_por_pallet=10))

        etiquetas_a = list(lote_a.etiquetas.order_by('numero_sequencial'))
        self.assertEqual([e.numero_sequencial for e in etiquetas_a], [1, 2, 3, 4, 5])
        self.assertEqual(
            [e.codigo_pallet for e in etiquetas_a],
            ['202627-1', '202627-2', '202627-3', '202627-6', '202627-7'])

    def test_adicionar_pallets_duas_vezes_sem_furos(self):
        lote = self._novo_lote(total_pallets=2)
        lote = adicionar_pallets(lote, self.empresa, 2, item_data(caixas_por_pallet=10))
        lote = adicionar_pallets(lote, self.empresa, 3, item_data(caixas_por_pallet=10))
        sequenciais = list(lote.etiquetas.order_by('numero_sequencial').values_list('numero_sequencial', flat=True))
        self.assertEqual(sequenciais, [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(lote.total_pallets, 7)

    def test_adicionar_pallets_rejeitado_quando_lote_concluido(self):
        lote = self._novo_lote(total_pallets=2)
        lote = concluir_lote(lote)
        with self.assertRaises(LoteConcluidoError):
            adicionar_pallets(lote, self.empresa, 1, item_data(caixas_por_pallet=10))
        lote.refresh_from_db()
        self.assertEqual(lote.etiquetas.count(), 2)
        self.assertEqual(lote.total_pallets, 2)

    def test_adicionar_pallets_quantidade_invalida(self):
        lote = self._novo_lote(total_pallets=1)
        with self.assertRaises(ValueError):
            adicionar_pallets(lote, self.empresa, 0, item_data(caixas_por_pallet=10))

    def test_concluir_lote_e_idempotente(self):
        lote = self._novo_lote(total_pallets=1)
        lote = concluir_lote(lote)
        self.assertEqual(lote.status, 'CONCLUIDA')
        lote = concluir_lote(lote)
        self.assertEqual(lote.status, 'CONCLUIDA')

    def test_total_pallets_permanece_sincronizado_com_contagem_real(self):
        lote = self._novo_lote(total_pallets=2)
        lote = adicionar_pallets(lote, self.empresa, 3, item_data(caixas_por_pallet=10))
        lote = adicionar_pallets(lote, self.empresa, 1, item_data(caixas_por_pallet=10))
        self.assertEqual(lote.total_pallets, lote.etiquetas.count())

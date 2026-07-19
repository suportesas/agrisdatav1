from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.db.models.signals import post_save

from cadastros.models import NCM
from empresas.models import Empresa, Plano
from empresas import signals as empresa_signals
from produtos.models import Categoria, Marca, Produto, SubCategoria, TipoProduto, UnidadeMedida


class ProdutoValidationTests(TestCase):
	def setUp(self):
		self.plano = Plano.objects.create(
			codigo='PEQUENO',
			nome='Plano Teste',
			valor_mensal=Decimal('100'),
		)
		self.empresa = self._criar_empresa_sem_seeds()
		self.ncm = NCM.objects.create(codigo='01012100', nome='NCM teste')
		self.tipo_produto, _ = TipoProduto.objects.get_or_create(
			empresa=self.empresa,
			codigo='REV',
			defaults={'nome': 'Revenda'},
		)
		self.unidade_kg, _ = UnidadeMedida.objects.get_or_create(
			empresa=self.empresa,
			sigla='KG',
			defaults={'nome': 'Quilograma', 'tipo': 'PESO'},
		)
		self.unidade_sc, _ = UnidadeMedida.objects.get_or_create(
			empresa=self.empresa,
			sigla='SC',
			defaults={'nome': 'Saca', 'tipo': 'PESO'},
		)
		self.unidade_l, _ = UnidadeMedida.objects.get_or_create(
			empresa=self.empresa,
			sigla='L',
			defaults={'nome': 'Litro', 'tipo': 'VOLUME'},
		)
		self.categoria_def, _ = Categoria.objects.get_or_create(
			empresa=self.empresa,
			codigo='DEF',
			defaults={'nome': 'Defensivos', 'condiciona_campos': True},
		)
		self.categoria_fert, _ = Categoria.objects.get_or_create(
			empresa=self.empresa,
			codigo='FERT',
			defaults={'nome': 'Fertilizantes', 'condiciona_campos': True},
		)
		self.categoria_geral, _ = Categoria.objects.get_or_create(
			empresa=self.empresa,
			codigo='GER',
			defaults={'nome': 'Geral', 'condiciona_campos': False},
		)
		self.subcategoria_def = SubCategoria.objects.create(
			categoria=self.categoria_def,
			codigo='HERB',
			nome='Herbicidas',
		)
		self.subcategoria_fert = SubCategoria.objects.create(
			categoria=self.categoria_fert,
			codigo='NPK',
			nome='NPK',
		)

	def _criar_empresa_sem_seeds(self):
		receivers = [
			empresa_signals.create_default_roles,
			empresa_signals.seed_ncms_on_create,
			empresa_signals.seed_cfops_on_create,
			empresa_signals.seed_pragas_on_create,
			empresa_signals.seed_defensivos_on_create,
			empresa_signals.seed_categorias_on_create,
		]

		for receiver in receivers:
			post_save.disconnect(receiver, sender=Empresa)

		try:
			return Empresa.objects.create(
				nome='Empresa Teste LTDA',
				cnpj='12.345.678/0001-99',
				plano=self.plano,
			)
		finally:
			for receiver in receivers:
				post_save.connect(receiver, sender=Empresa)

	def _build_produto(self, **overrides):
		data = {
			'nome': 'Produto Teste',
			'categoria': self.categoria_geral,
			'subcategoria': None,
			'tipo_produto': self.tipo_produto,
			'unidade_medida': self.unidade_kg,
			'unidade_compra': self.unidade_sc,
			'unidade_venda': self.unidade_kg,
			'fator_conversao': Decimal('1'),
			'ncm': self.ncm,
			'tipo_item': '00',
			'preco_custo': Decimal('10'),
			'preco_venda': Decimal('12'),
			'preco_minimo': Decimal('9'),
			'margem_lucro': Decimal('20'),
		}
		data.update(overrides)
		return Produto(**data)

	def test_subcategoria_precisa_pertencer_a_categoria(self):
		produto = self._build_produto(
			categoria=self.categoria_def,
			subcategoria=self.subcategoria_fert,
		)

		with self.assertRaises(ValidationError) as exc:
			produto.full_clean()

		self.assertIn('subcategoria', exc.exception.message_dict)

	def test_unidades_precisam_ter_mesmo_tipo(self):
		produto = self._build_produto(unidade_venda=self.unidade_l)

		with self.assertRaises(ValidationError) as exc:
			produto.full_clean()

		self.assertIn('unidade_venda', exc.exception.message_dict)

	def test_defensivo_exige_campos_obrigatorios(self):
		produto = self._build_produto(
			categoria=self.categoria_def,
			subcategoria=self.subcategoria_def,
			categoria_agricola='DEFENSIVO',
		)

		with self.assertRaises(ValidationError) as exc:
			produto.full_clean()

		self.assertIn('classe_agronomica', exc.exception.message_dict)
		self.assertIn('ingrediente_ativo', exc.exception.message_dict)
		self.assertIn('registro_mapa', exc.exception.message_dict)

	def test_fertilizante_exige_formula_ou_teor(self):
		produto = self._build_produto(
			categoria=self.categoria_fert,
			subcategoria=self.subcategoria_fert,
			categoria_agricola='FERTILIZANTE',
			tipo_fertilizante='SIMPLES',
		)

		with self.assertRaises(ValidationError) as exc:
			produto.full_clean()

		self.assertIn('formula_npk', exc.exception.message_dict)

	def test_campos_agricolas_sao_limpos_quando_nao_ha_categoria_agricola(self):
		produto = self._build_produto(
			categoria_agricola='',
			classe_agronomica='HERBICIDA',
			ingrediente_ativo='Glifosato',
			registro_mapa='12345',
			tipo_fertilizante='SIMPLES',
			formula_npk='20-05-20',
		)

		produto.full_clean()

		self.assertEqual(produto.classe_agronomica, '')
		self.assertEqual(produto.ingrediente_ativo, '')
		self.assertEqual(produto.registro_mapa, '')
		self.assertEqual(produto.tipo_fertilizante, '')


class MarcaModelTests(TestCase):
	def setUp(self):
		plano = Plano.objects.create(codigo='PEQUENO', nome='Plano Teste', valor_mensal=Decimal('100'))
		self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=plano)
		self.outra_empresa = Empresa.objects.create(nome='Outra Empresa', plano=plano)

	def test_marca_nasce_ativa(self):
		marca = Marca.objects.create(empresa=self.empresa, nome='Terra Brasilis')
		self.assertTrue(marca.ativo)

	def test_nome_unico_por_empresa_mas_repetivel_entre_empresas(self):
		Marca.objects.create(empresa=self.empresa, nome='Terra Brasilis')
		# mesma empresa, mesmo nome -> deve falhar
		with self.assertRaises(Exception):
			Marca.objects.create(empresa=self.empresa, nome='Terra Brasilis')
		# empresa diferente, mesmo nome -> deve funcionar
		Marca.objects.create(empresa=self.outra_empresa, nome='Terra Brasilis')
		self.assertEqual(Marca.objects.filter(nome='Terra Brasilis').count(), 2)

"""
Testes para o ciclo de vida do status do PedidoVenda (Fase 1.2 do plano de
completar o processo venda -> exportação).

`sincronizar_status_pedido` só deve marcar o pedido como CONCLUIDO quando o
documento fiscal vinculado (NF-e/Invoice) estiver EMITIDA, e só deve reverter
de CONCLUIDO para CONFIRMADO quando esse documento for cancelado depois.
"""
import pytest

from cadastros.models import Cliente
from empresas.models import Empresa
from faturamento.models import InvoiceExportacao
from usuarios.models import Usuario
from vendas.models import PedidoVenda
from vendas.services import sincronizar_status_pedido


@pytest.fixture
def setup_dados(db):
    empresa = Empresa.objects.create(
        nome='Empresa Teste Ltda',
        cnpj='12.345.678/0001-90',
        email='test@empresateste.com',
    )
    usuario = Usuario.objects.create_user(
        username='testuser_vendas',
        email='vendas@test.com',
        password='testpass123',
        empresa=empresa,
    )
    cliente = Cliente.objects.create(empresa=empresa, razao_social='Cliente Teste')
    return {'empresa': empresa, 'usuario': usuario, 'cliente': cliente}


def _criar_pedido(dados, status, tipo_venda='EXPORTACAO', **extra):
    return PedidoVenda.objects.create(
        empresa=dados['empresa'],
        numero=extra.pop('numero', 'PV-TESTE-0001'),
        cliente=dados['cliente'],
        status=status,
        tipo_venda=tipo_venda,
        **extra,
    )


@pytest.mark.django_db
class TestSincronizarStatusPedido:
    def test_sem_documento_nao_altera_status(self, setup_dados):
        pedido = _criar_pedido(setup_dados, status='CONFIRMADO')
        sincronizar_status_pedido(pedido)
        pedido.refresh_from_db()
        assert pedido.status == 'CONFIRMADO'

    def test_documento_rascunho_nao_conclui_pedido(self, setup_dados):
        invoice = InvoiceExportacao.objects.create(
            empresa=setup_dados['empresa'], cliente=setup_dados['cliente'], status='RASCUNHO',
        )
        pedido = _criar_pedido(setup_dados, status='CONFIRMADO', invoice=invoice)
        sincronizar_status_pedido(pedido)
        pedido.refresh_from_db()
        assert pedido.status == 'CONFIRMADO'

    def test_documento_emitida_conclui_pedido(self, setup_dados):
        invoice = InvoiceExportacao.objects.create(
            empresa=setup_dados['empresa'], cliente=setup_dados['cliente'], status='EMITIDA',
        )
        pedido = _criar_pedido(setup_dados, status='CONFIRMADO', invoice=invoice)
        sincronizar_status_pedido(pedido)
        pedido.refresh_from_db()
        assert pedido.status == 'CONCLUIDO'

    def test_cancelamento_do_documento_reverte_pedido_concluido(self, setup_dados):
        invoice = InvoiceExportacao.objects.create(
            empresa=setup_dados['empresa'], cliente=setup_dados['cliente'], status='CANCELADA',
        )
        pedido = _criar_pedido(setup_dados, status='CONCLUIDO', invoice=invoice)
        sincronizar_status_pedido(pedido)
        pedido.refresh_from_db()
        assert pedido.status == 'CONFIRMADO'

    def test_cancelamento_do_documento_nao_mexe_em_pedido_nao_concluido(self, setup_dados):
        invoice = InvoiceExportacao.objects.create(
            empresa=setup_dados['empresa'], cliente=setup_dados['cliente'], status='CANCELADA',
        )
        pedido = _criar_pedido(setup_dados, status='APROVADO', invoice=invoice)
        sincronizar_status_pedido(pedido)
        pedido.refresh_from_db()
        assert pedido.status == 'APROVADO'

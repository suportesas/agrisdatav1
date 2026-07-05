from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
def configuracoes_hub(request):
    empresa = request.user.empresa
    usuario = request.user

    is_admin = (
        usuario.is_superuser
        or getattr(usuario, 'tipo', '') == 'ADMIN'
        or (hasattr(usuario, 'is_empresa_admin') and usuario.is_empresa_admin())
    )

    # ConfiguracaoSistema
    config_sistema = None
    try:
        from core.models import ConfiguracaoSistema
        config_sistema = ConfiguracaoSistema.get_config(empresa)
    except Exception:
        pass

    # ConfiguracaoFiscal
    config_fiscal = None
    cert_validade = None
    cert_status = 'nao_configurado'  # 'valido', 'vencido', 'nao_configurado'
    tem_token = False
    ambiente_nfe = None

    try:
        config_fiscal = empresa.configuracao_fiscal
        cert_validade = config_fiscal.certificado_validade
        ambiente_nfe = config_fiscal.ambiente_nfe
        # Token: verifica se tem conteúdo armazenado
        tem_token = bool(config_fiscal.token_integranotas)

        if cert_validade:
            hoje = timezone.now().date()
            cert_status = 'valido' if cert_validade >= hoje else 'vencido'
        elif config_fiscal.certificado_pfx:
            cert_status = 'vencido'
    except Exception:
        pass

    # Contagens de cadastros auxiliares
    counts = {}
    if empresa:
        try:
            from produtos.models import TipoProduto, Categoria, Subcategoria, UnidadeMedida, NaturezaOperacao
            from cadastros.models import NCM, CFOP, Cliente, Fornecedor, Transportadora
            from estoque.models import Armazem
            counts['tipos_produto'] = TipoProduto.objects.filter(empresa=empresa).count()
            counts['categorias'] = Categoria.objects.filter(empresa=empresa).count()
            counts['unidades'] = UnidadeMedida.objects.filter(empresa=empresa).count()
            counts['naturezas'] = NaturezaOperacao.objects.filter(empresa=empresa).count()
            counts['ncm'] = NCM.objects.filter(empresa=empresa).count()
            counts['cfop'] = CFOP.objects.filter(empresa=empresa).count()
            counts['clientes'] = Cliente.objects.filter(empresa=empresa, status='ATIVO').count()
            counts['fornecedores'] = Fornecedor.objects.filter(empresa=empresa, ativa=True).count()
            counts['transportadoras'] = Transportadora.objects.filter(empresa=empresa, ativa=True).count()
            counts['armazens'] = Armazem.objects.filter(empresa=empresa).count()
        except Exception:
            pass

        try:
            from usuarios.models import Usuario
            counts['usuarios'] = Usuario.objects.filter(empresa=empresa, is_active=True).count()
        except Exception:
            pass

        try:
            from empresas.models import Role
            counts['roles'] = Role.objects.filter(empresa=empresa).count()
        except Exception:
            pass

        try:
            from plano_contas.models import ContaContabil
            counts['plano_contas'] = ContaContabil.objects.filter(empresa=empresa).count()
        except Exception:
            pass

        try:
            from financeiro.models import ContaBancaria
            counts['contas_bancarias'] = ContaBancaria.objects.filter(empresa=empresa, ativo=True).count()
        except Exception:
            pass

    # Form de preferências inline
    from empresas.forms import EmpresaPreferenciasForm
    form_preferencias = EmpresaPreferenciasForm(instance=empresa)

    return render(request, 'core/configuracoes_hub.html', {
        'empresa': empresa,
        'usuario': usuario,
        'is_admin': is_admin,
        'config_sistema': config_sistema,
        'config_fiscal': config_fiscal,
        'cert_validade': cert_validade,
        'cert_status': cert_status,
        'tem_token': tem_token,
        'ambiente_nfe': ambiente_nfe,
        'form_preferencias': form_preferencias,
        'counts': counts,
    })

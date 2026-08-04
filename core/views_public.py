"""
Views públicas do site (Landing Page, etc)
"""
from django.conf import settings
from django.shortcuts import render, redirect


def landing_page(request):
    """Página inicial de divulgação do Agrisdata"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    # Imagem hero - trator em operação no campo
    imagem_hero = 'https://images.unsplash.com/photo-1574943320219-553eb213f72d?w=1000&h=800&fit=crop&q=80'

    context = {
        'imagem_hero': imagem_hero,
        'app_login_url': settings.APP_LOGIN_URL,
    }

    return render(request, 'landing_page.html', context)


def recursos_page(request):
    """Página de Funcionalidades/Recursos"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    recursos = [
        {
            'icon': 'bi-graph-up',
            'titulo': 'Análise de Dados',
            'descricao': 'Dashboard completo com gráficos e análises em tempo real'
        },
        {
            'icon': 'bi-boxes',
            'titulo': 'Gestão de Estoque',
            'descricao': 'Controle total de inventário com rastreamento automático'
        },
        {
            'icon': 'bi-people-fill',
            'titulo': 'Gestão de Recursos Humanos',
            'descricao': 'Administre sua equipe, funções e contratações'
        },
        {
            'icon': 'bi-receipt',
            'titulo': 'Gestão Financeira',
            'descricao': 'Controle de contas a pagar e receber integrado'
        },
        {
            'icon': 'bi-leaf',
            'titulo': 'Monitoramento Agrícola',
            'descricao': 'Acompanhe pragas, defensivos e desenvolvimento das culturas'
        },
        {
            'icon': 'bi-shield-check',
            'titulo': 'Segurança Multi-Tenant',
            'descricao': 'Isolamento completo de dados por empresa'
        },
    ]
    
    context = {'recursos': recursos}
    return render(request, 'recursos_page.html', context)


def sobre_page(request):
    """Página Sobre Nós"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    context = {}
    return render(request, 'sobre_page.html', context)


def planos_page(request):
    """Página de Planos e Preços"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    planos = [
        {
            'nome': 'Starter',
            'preco': 'R$ 199',
            'periodo': '/mês',
            'destaque': False,
            'descricao': 'Perfeito para pequenas propriedades',
            'features': [
                'Até 3 funcionários',
                'Gestão básica de estoque',
                'Dashboard simples',
                'Suporte por e-mail',
            ]
        },
        {
            'nome': 'Professional',
            'preco': 'R$ 499',
            'periodo': '/mês',
            'destaque': True,
            'descricao': 'A escolha mais popular',
            'features': [
                'Até 15 funcionários',
                'Gestão completa de estoque',
                'Dashboard avançado',
                'Monitoramento agrícola',
                'Suporte prioritário',
                'Backup automático',
            ]
        },
        {
            'nome': 'Enterprise',
            'preco': 'Customizado',
            'periodo': '',
            'destaque': False,
            'descricao': 'Para grandes operações',
            'features': [
                'Usuários ilimitados',
                'Todas as features',
                'API customizável',
                'Suporte 24/7',
                'Implementação dedicada',
                'Treinamento pessoal',
            ]
        },
    ]
    
    context = {'planos': planos}
    return render(request, 'planos_page.html', context)


def faq_page(request):
    """Página de FAQ"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    faq_items = [
        {
            'pergunta': 'O Agrisdata funciona em dispositivos móveis?',
            'resposta': 'Sim! Nossa plataforma é totalmente responsiva e funciona perfeitamente em tablets e smartphones.'
        },
        {
            'pergunta': 'Como é feita a segurança dos meus dados?',
            'resposta': 'Usamos criptografia de ponta a ponta, backups automáticos diários e isolamento completo de dados por empresa.'
        },
        {
            'pergunta': 'Posso exportar meus dados?',
            'resposta': 'Sim, você pode exportar seus dados em diversos formatos (Excel, PDF, CSV) a qualquer momento.'
        },
        {
            'pergunta': 'Qual é o tempo de implementação?',
            'resposta': 'A maioria das implementações leva de 2 a 4 semanas, dependendo da complexidade.'
        },
        {
            'pergunta': 'Vocês oferecem treinamento?',
            'resposta': 'Sim! Oferecemos treinamento online para toda a equipe, com suporte contínuo.'
        },
        {
            'pergunta': 'Como funciona a integração com outros sistemas?',
            'resposta': 'Possuímos API robusta e integrações nativas com os principais sistemas agrícolas do mercado.'
        },
    ]
    
    context = {'faq_items': faq_items}
    return render(request, 'faq_page.html', context)


def contato_page(request):
    """Página de Contato/Demo"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    context = {}
    return render(request, 'contato_page.html', context)


def recursos_avancados_page(request):
    """Página de Recursos Avançados"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    
    recursos_avancados = [
        {
            'titulo': 'IA & Machine Learning',
            'descricao': 'Previsões automáticas baseadas em dados históricos',
            'icone': 'bi-robot'
        },
        {
            'titulo': 'IoT Integration',
            'descricao': 'Conecte sensores e equipamentos diretamente ao sistema',
            'icone': 'bi-cloud-fill'
        },
        {
            'titulo': 'Análise Preditiva',
            'descricao': 'Identifique padrões e problemas antes que ocorram',
            'icone': 'bi-binoculars'
        },
        {
            'titulo': 'Relatórios Customizados',
            'descricao': 'Crie seus próprios relatórios com dados específicos',
            'icone': 'bi-bar-chart'
        },
        {
            'titulo': 'Integração API',
            'descricao': 'Acesso programático a todos os dados do sistema',
            'icone': 'bi-link-45deg'
        },
        {
            'titulo': 'Automação Workflow',
            'descricao': 'Automatize tarefas repetitivas com workflows inteligentes',
            'icone': 'bi-arrow-repeat'
        },
    ]
    
    context = {'recursos_avancados': recursos_avancados}
    return render(request, 'recursos_avancados_page.html', context)


def page_not_found(request, exception=None, unknown_path=None):
    """Página 404 personalizada"""
    return render(request, '404.html', status=404)

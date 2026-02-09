"""
Seed de Pragas Agrícolas
Lista pré-configurada de pragas comuns para pré-cadastro automático
Sistema multi-tenant: cada empresa recebe sua própria cópia
"""

PRAGAS_SEED = [
    # ===============================================
    # INSETOS - LEPIDÓPTEROS (Borboletas e Traças)
    # ===============================================
    {
        'nome_comum': 'Lagarta-do-cartucho',
        'nome_cientifico': 'Spodoptera frugiperda',
    },
    {
        'nome_comum': 'Lagarta-da-soja',
        'nome_cientifico': 'Anticarsia gemmatalis',
    },
    {
        'nome_comum': 'Lagarta-rosada',
        'nome_cientifico': 'Pectinophora gossypiella',
    },
    {
        'nome_comum': 'Traça-das-crucíferas',
        'nome_cientifico': 'Plutella xylostella',
    },
    {
        'nome_comum': 'Broca-do-tomate',
        'nome_cientifico': 'Neoleucinodes elegantalis',
    },
    {
        'nome_comum': 'Borboleta-da-couve',
        'nome_cientifico': 'Ascia monuste orseis',
    },
    {
        'nome_comum': 'Traça-do-tomateiro',
        'nome_cientifico': 'Tuta absoluta',
    },
    {
        'nome_comum': 'Lagarta-das-vagens',
        'nome_cientifico': 'Etiella zinckenella',
    },
    
    # ===============================================
    # INSETOS - DÍPTEROS (Moscas)
    # ===============================================
    {
        'nome_comum': 'Mosca-da-fruta',
        'nome_cientifico': 'Ceratitis capitata',
    },
    {
        'nome_comum': 'Mosca-do-mediterrâneo',
        'nome_cientifico': 'Ceratitis capitata',
    },
    {
        'nome_comum': 'Mosca-da-carambola',
        'nome_cientifico': 'Bactrocera carambolae',
    },
    {
        'nome_comum': 'Mosca-branca',
        'nome_cientifico': 'Bemisia tabaci',
    },
    {
        'nome_comum': 'Mosca-minadora-da-folha',
        'nome_cientifico': 'Liriomyza trifolii',
    },
    
    # ===============================================
    # INSETOS - HOMÓPTEROS (Pulgões, Cigarrinhas)
    # ===============================================
    {
        'nome_comum': 'Pulgão-do-algodão',
        'nome_cientifico': 'Aphis gossypii',
    },
    {
        'nome_comum': 'Pulgão-verde',
        'nome_cientifico': 'Myzus persicae',
    },
    {
        'nome_comum': 'Pulgão-da-soja',
        'nome_cientifico': 'Aphis glycines',
    },
    {
        'nome_comum': 'Cigarrinha-das-pastagens',
        'nome_cientifico': 'Mahanarva fimbriolata',
    },
    {
        'nome_comum': 'Cigarra-do-milho',
        'nome_cientifico': 'Dalbulus maidis',
    },
    {
        'nome_comum': 'Psilídio-do-tomate',
        'nome_cientifico': 'Bactericera cockerelli',
    },
    
    # ===============================================
    # INSETOS - HEMÍPTEROS (Percevejos)
    # ===============================================
    {
        'nome_comum': 'Percevejo-marrom',
        'nome_cientifico': 'Euschistus heros',
    },
    {
        'nome_comum': 'Percevejo-vermelho',
        'nome_cientifico': 'Atractomorpha psittacus',
    },
    {
        'nome_comum': 'Percevejo-da-soja',
        'nome_cientifico': 'Nezara viridula',
    },
    {
        'nome_comum': 'Percevejo-de-renda',
        'nome_cientifico': 'Corythucha modonensis',
    },
    
    # ===============================================
    # INSETOS - COLEÓPTEROS (Besouros)
    # ===============================================
    {
        'nome_comum': 'Vaquinha-verde',
        'nome_cientifico': 'Diabrotica speciosa',
    },
    {
        'nome_comum': 'Besouro-da-batata',
        'nome_cientifico': 'Leptinotarsa decemlineata',
    },
    {
        'nome_comum': 'Besouro-do-milho',
        'nome_cientifico': 'Diabrotica virgifera',
    },
    {
        'nome_comum': 'Besouro-do-algodão',
        'nome_cientifico': 'Anthonomus grandis',
    },
    {
        'nome_comum': 'Brocador-dos-citros',
        'nome_cientifico': 'Xyleborinus saxesenii',
    },
    
    # ===============================================
    # INSETOS - HIMENÓPTEROS (Vespas, Formigas)
    # ===============================================
    {
        'nome_comum': 'Formiga-saúva',
        'nome_cientifico': 'Atta spp.',
    },
    {
        'nome_comum': 'Formiga-quenquém',
        'nome_cientifico': 'Acromyrmex spp.',
    },
    
    # ===============================================
    # INSETOS - ORTÓPTEROS (Gafanhotos)
    # ===============================================
    {
        'nome_comum': 'Gafanhoto-migrador',
        'nome_cientifico': 'Schistocerca cancellata',
    },
    {
        'nome_comum': 'Gafanhoto-do-mato',
        'nome_cientifico': 'Rhammatocerus schistocercoides',
    },
    
    # ===============================================
    # INSETOS - TISANUROS e OUTROS
    # ===============================================
    {
        'nome_comum': 'Tripes',
        'nome_cientifico': 'Frankliniella schultzei',
    },
    {
        'nome_comum': 'Tripes-da-flor',
        'nome_cientifico': 'Thrips palmi',
    },
    {
        'nome_comum': 'Afídio',
        'nome_cientifico': 'Aphis craccivora',
    },
    
    # ===============================================
    # ÁCAROS
    # ===============================================
    {
        'nome_comum': 'Ácaro-rajado',
        'nome_cientifico': 'Tetranychus urticae',
    },
    {
        'nome_comum': 'Ácaro-vermelho',
        'nome_cientifico': 'Oligonychus ilicis',
    },
    {
        'nome_comum': 'Ácaro-branco',
        'nome_cientifico': 'Polyphagotarsonemus latus',
    },
    {
        'nome_comum': 'Ácaro-do-coco',
        'nome_cientifico': 'Eriophyes guerreronis',
    },
    {
        'nome_comum': 'Ácaro-das-plantas',
        'nome_cientifico': 'Panonychus ulmi',
    },
    
    # ===============================================
    # NEMATOIDES
    # ===============================================
    {
        'nome_comum': 'Nematoide-das-galhas',
        'nome_cientifico': 'Meloidogyne incognita',
    },
    {
        'nome_comum': 'Nematoide-do-cisto',
        'nome_cientifico': 'Heterodera glycines',
    },
    {
        'nome_comum': 'Nematoide-das-lesões-radiculares',
        'nome_cientifico': 'Pratylenchus brachyurus',
    },
    {
        'nome_comum': 'Nematoide-das-galhas (javaia)',
        'nome_cientifico': 'Meloidogyne arenaria',
    },
    
    # ===============================================
    # FUNGOS - PRINCIPAIS
    # ===============================================
    {
        'nome_comum': 'Ferrugem-asiática-da-soja',
        'nome_cientifico': 'Phakopsora phaseoli',
    },
    {
        'nome_comum': 'Ferrugem-do-milho',
        'nome_cientifico': 'Puccinia sorghi',
    },
    {
        'nome_comum': 'Oídio',
        'nome_cientifico': 'Erysiphe cichoracearum',
    },
    {
        'nome_comum': 'Míldio-da-videira',
        'nome_cientifico': 'Plasmopara viticola',
    },
    {
        'nome_comum': 'Mofo-cinzento',
        'nome_cientifico': 'Botrytis cinerea',
    },
    {
        'nome_comum': 'Antracnose',
        'nome_cientifico': 'Colletotrichum lindemuthianum',
    },
    {
        'nome_comum': 'Septoriose',
        'nome_cientifico': 'Septoria lycopersici',
    },
    {
        'nome_comum': 'Mancha-parda',
        'nome_cientifico': 'Alternaria solani',
    },
    {
        'nome_comum': 'Fusariose',
        'nome_cientifico': 'Fusarium oxysporum',
    },
    {
        'nome_comum': 'Podridão-do-pé',
        'nome_cientifico': 'Fusarium graminearum',
    },
    {
        'nome_comum': 'Mal-do-pé-do-milho',
        'nome_cientifico': 'Fusarium verticillioides',
    },
    {
        'nome_comum': 'Mofo-branco',
        'nome_cientifico': 'Sclerotinia sclerotiorum',
    },
    {
        'nome_comum': 'Seca-da-rama',
        'nome_cientifico': 'Macrophomina phaseolina',
    },
    {
        'nome_comum': 'Murcha-verticiliana',
        'nome_cientifico': 'Verticillium dahliae',
    },
    {
        'nome_comum': 'Caspa-do-milho',
        'nome_cientifico': 'Exserohilum turcicum',
    },
    {
        'nome_comum': 'Cercosporiose',
        'nome_cientifico': 'Cercospora arachidicola',
    },
    {
        'nome_comum': 'Mancha-de-Phaeosphaeria',
        'nome_cientifico': 'Phaeosphaeria maydis',
    },
    {
        'nome_comum': 'Mancha-cinzenta-da-folha',
        'nome_cientifico': 'Cercospora sorghi',
    },
    {
        'nome_comum': 'Brusone',
        'nome_cientifico': 'Pyricularia oryzae',
    },
    
    # ===============================================
    # BACTÉRIAS
    # ===============================================
    {
        'nome_comum': 'Murcha-bacteriana',
        'nome_cientifico': 'Ralstonia solanacearum',
    },
    {
        'nome_comum': 'Canela-preta',
        'nome_cientifico': 'Xanthomonas campestris',
    },
    {
        'nome_comum': 'Mancha-angular',
        'nome_cientifico': 'Xanthomonas citri',
    },
    {
        'nome_comum': 'Mancha-bacteriana-do-tomate',
        'nome_cientifico': 'Clavibacter michiganensis',
    },
    {
        'nome_comum': 'Murcha-de-Stewart',
        'nome_cientifico': 'Pantoea stewartii',
    },
    {
        'nome_comum': 'Podridão-mole-bacteriana',
        'nome_cientifico': 'Pectobacterium carotovorum',
    },
    
    # ===============================================
    # VÍRUS
    # ===============================================
    {
        'nome_comum': 'Mosaico-do-tomate',
        'nome_cientifico': 'Tomato mosaic virus (ToMV)',
    },
    {
        'nome_comum': 'Enrolamento-da-folha-da-batata',
        'nome_cientifico': 'Potato leaf roll virus (PLRV)',
    },
    {
        'nome_comum': 'Vira-cabeça-do-tomate',
        'nome_cientifico': 'Tomato spotted wilt virus (TSWV)',
    },
    {
        'nome_comum': 'Mosaico-do-milho',
        'nome_cientifico': 'Maize dwarf mosaic virus (MDMV)',
    },
    {
        'nome_comum': 'Mosaico-amarelo-da-soja',
        'nome_cientifico': 'Soybean mosaic virus (SMV)',
    },
    {
        'nome_comum': 'Nanismo-amarelo-da-cevada',
        'nome_cientifico': 'Barley yellow dwarf virus (BYDV)',
    },
    {
        'nome_comum': 'Mosaico-comum-do-feijão',
        'nome_cientifico': 'Bean common mosaic virus (BCMV)',
    },
    {
        'nome_comum': 'Carvão-da-soja',
        'nome_cientifico': 'Soybean cyst nematode virus',
    },
    
    # ===============================================
    # MOLUSCOS
    # ===============================================
    {
        'nome_comum': 'Lesma-cinzenta',
        'nome_cientifico': 'Limax maximus',
    },
    {
        'nome_comum': 'Caracol-gigante-africano',
        'nome_cientifico': 'Achatina fulica',
    },
    {
        'nome_comum': 'Caracol-marrom',
        'nome_cientifico': 'Cornu aspersum',
    },
    
    # ===============================================
    # OUTROS INSETOS E PRAGAS
    # ===============================================
    {
        'nome_comum': 'Cochonilha-branca',
        'nome_cientifico': 'Planococcus citri',
    },
    {
        'nome_comum': 'Cochonilha-da-soja',
        'nome_cientifico': 'Ceroplastes spp.',
    },
    {
        'nome_comum': 'Escama-de-São-José',
        'nome_cientifico': 'Quadraspidiotus perniciosus',
    },
    {
        'nome_comum': 'Escama-vermelha',
        'nome_cientifico': 'Aonidiella aurantii',
    },
]

def seed_pragas_for_company(empresa):
    """
    Cria pragas pré-definidas para uma empresa
    
    Args:
        empresa: Instância da Empresa onde as pragas serão criadas
    
    Returns:
        tuple: (quantidade_criada, quantidade_ignorada)
    """
    from .models import Praga
    
    criadas = 0
    ignoradas = 0
    
    for praga_data in PRAGAS_SEED:
        nome_comum = praga_data['nome_comum']
        
        # Verifica se já existe
        if Praga.objects.filter(empresa=empresa, nome_comum__iexact=nome_comum).exists():
            ignoradas += 1
            continue
        
        try:
            praga = Praga.objects.create(
                empresa=empresa,
                nome_comum=nome_comum,
                nome_cientifico=praga_data.get('nome_cientifico', ''),
                ativa=True
            )
            criadas += 1
        except Exception as e:
            # Log do erro mas continua
            print(f"Erro ao criar praga '{nome_comum}': {str(e)}")
            ignoradas += 1
    
    return criadas, ignoradas

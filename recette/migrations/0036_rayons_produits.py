"""
Rayons du magasin et produits "placard" (déjà à la maison en principe) pour la liste de courses.

Prévu pour la production : tout se fait par nom (jamais par id), un produit absent est ignoré,
un rayon déjà choisi à la main dans l'admin n'est pas écrasé. Les produits dérivés (ail haché...)
n'ont pas besoin de rayon : la liste de courses utilise celui de leur produit de base.
"""
from django.db import migrations


# nom du rayon, ordre de parcours, produits
RAYONS = [
    ('Fruits & légumes', 10, [
        'ail', 'ananas', 'asperge verte', 'aubergine', 'banane', 'basilic', 'basilic sacré', 'bille de cerfeuil',
        'brocoli', 'carotte', 'carotte jaune', 'céleri', 'céleri blanc', 'champignon', 'chou chinois', 'ciboulette',
        'citron', 'citron vert', 'citronnelle', 'concombre', 'coriandre fraîche', 'courgette', 'courgette ronde',
        'cresson', 'cœur de laitue romaine', 'échalote', 'figue fraîche', 'framboise fraîche', 'germe de radis',
        'germe de soja', 'gingembre', 'haricot vert', 'légumes', 'mangue', 'menthe fraîche', 'navet', 'oignon',
        'oignon jeune', 'oignon rouge', 'orange', 'pak-choï', 'panais', 'patate douce', 'persil', 'persil plat',
        'piment', 'piment vert', 'pleurote', 'poireau', 'poivron', 'poivron jaune', 'poivron rouge', 'poivron vert',
        'pomme', 'pomme de terre', 'pomme de terre à chair ferme', 'pomme de terre grenaille',
        'pomme de terre précuite', 'pomme Jonagold', 'radis', 'roquette', 'shiitake', 'thym', 'tomate',
        'tomate allongée', 'tomate cerise',
    ]),
    ('Boucherie & volaille', 20, [
        'blanc de poulet', 'carbonade de bœuf', 'carpaccio de bœuf', "épaule d'agneau", "gigot d'agneau",
        'haché au fenouil', 'haché de porc', 'haché de veau', 'haché porc et bœuf', 'haché porc et veau',
        'haut de cuisse de poulet', 'jarret de bœuf', 'magret de canard', 'pilon de poulet', 'poulet',
        'poulet kebab', "ragoût d'agneau", 'spiering de porc',
    ]),
    ('Poissonnerie', 30, [
        'calamar', 'crevette rose', 'crevette tigrée jumbo', 'filet de bar', 'langoustine', 'noix de Saint-Jacques',
        'pavé de saumon', 'saumon fumé', 'scampi', 'thon rouge',
    ]),
    ('Charcuterie & traiteur', 40, [
        'bacon', 'chorizo', 'coppa', 'houmous', 'lardon fumé',
    ]),
    ('Crèmerie & œufs', 50, [
        'beurre', 'crème épaisse légère', 'crème fleurette', 'crème fraîche liquide', 'fromage frais', 'lait',
        'lait végétal', 'mascarpone', 'rouleau de pâte feuilletée', 'yaourt', 'yaourt grec', 'yaourt nature', 'œuf',
    ]),
    ('Fromages', 60, [
        'boule de mozzarella', 'burrata', 'emmental', 'feta', 'fromage râpé', 'parmesan', 'reblochon',
    ]),
    ('Boulangerie', 70, [
        'baguette', 'baguette précuite au levain', 'wrap',
    ]),
    ('Pâtes, riz & céréales', 80, [
        'couscous', 'feuille de lasagne', 'macaroni', 'maccheroni', 'nouille de riz', 'nouille instantanée',
        "nouille ramen prête à l'emploi", 'nouille udon', 'orecchiette', 'orzo', 'pâte', 'riz basmati', 'riz jasmin',
        'riz long grain', 'riz pour cuisson à blanc', 'riz pour risotto', 'spaghettis', 'vermicelle de riz',
        'vermicelle transparent',
    ]),
    ('Conserves & bocaux', 90, [
        'câpre', 'concentré de tomate', "filet d'anchois", 'haricot rouge', 'maïs', 'olive noire',
        'olives vertes et noires dénoyautées', 'pois chiche', 'purée de tomate', 'salsa de tomates cerises',
        'sauce tomate', 'tomate concassée au basilic', 'tomate confite', 'tomate pelée', 'tomate pelée en dés',
        'tomate séchée',
    ]),
    ('Épicerie salée & apéritif', 100, [
        'cacahuète', 'cacahuète au miel piquante', 'chapelure', 'chapelure panko', 'chips tortilla',
        'graine de sésame', 'mélange de graines',
    ]),
    ('Épicerie sucrée & pâtisserie', 110, [
        'amande', 'beurre de cacahuète', 'biscuit sec', 'bonbon à la violette', 'cacao en poudre', 'café',
        'cassonade', 'chocolat fondant', 'chocolat noir', 'confit de figues', "extrait d'amande", 'extrait de vanille',
        'farine', 'farine fermentante', 'fécule de pomme de terre', 'lait concentré sucré', 'levure boulangère',
        'levure chimique', 'maïzena', 'miel', "miel d'acacia", 'noix de cajou', 'Oréo', "paquet d'Oréos",
        'pépite de chocolat', 'pignon de pin', 'pistache', 'raisin sec', 'sirop de candi', 'sirop de sucre',
        'sirop de sucre de canne', 'spéculos', 'sucre', 'sucre de canne', 'sucre fin', 'sucre glace', 'sucre roux',
        'vanille', 'volume de sucre',
    ]),
    ('Épices, huiles & condiments', 120, [
        'ail en poudre', 'bouillon de bœuf', 'bouillon de légumes', 'bouillon de poule', 'bouillon de volaille',
        'cannelle', 'clou de girofle', 'coriandre en graines', 'coriandre en poudre', 'cube de bouillon de légumes',
        'cube de bouillon de poule', 'cube de bouillon de viande', 'cumin', 'curcuma', 'curry en poudre',
        'épices italiennes', 'épices pour couscous', 'garam masala', 'graine de cardamome verte', 'harissa',
        'herbes de Provence', "huile d'arachide", "huile d'olive", 'huile de coco', 'huile de noix',
        'huile de tournesol', 'huile de truffe', 'huile neutre', 'ketchup', 'laurier', 'mayonnaise', 'moutarde',
        "moutarde à l'ancienne", 'noix de muscade', 'oignon en poudre', 'origan', 'paprika', 'paprika doux fumé',
        'paprika fumé', "piment d'Espelette", 'piment en poudre', 'piment séché', 'pili-pili', 'poivre',
        'poivre blanc', 'poivre de Cayenne', 'poivre de Sichuan', 'poivre noir', 'ras el hanout', 'safran',
        'sauce Worcestershire', 'sel', 'sel et poivre', 'sel, mélange de baies', 'sumac', 'vinaigre',
        'vinaigre balsamique', 'vinaigre de cidre', 'volumes de vinaigre (de cidre, de vin ou d\'alcool au choix)',
    ]),
    ('Produits du monde', 130, [
        'champignon noir déshydraté', 'crème de coco', 'feuille de nori', 'feuille de wonton', 'gochujang',
        'huile de sésame', 'ketjap manis', 'kombu', 'lait de coco', 'mirin', 'narutomaki', "pâte d'ail",
        'pâte de citronnelle', 'pâte de curry jaune', 'pâte de curry rouge', 'pâte de gingembre',
        'pousse de bambou en tranche', 'saké', 'sambal oelek', 'sauce aigre-douce pimentée', "sauce d'huître",
        'sauce de poisson', 'sauce soja', 'sauce soja noir', 'sriracha', 'tahini', 'vin de shaoxing',
        'vinaigre de riz',
    ]),
    ('Surgelés', 140, [
        'dos de saumon atlantique surgelé', 'épinards en branches', 'glace pilée', 'mix provençal légumes',
        'petit pois', 'petit pois surgelé', 'saumon surgelé',
    ]),
    ('Boissons & alcools', 150, [
        'amaretto', 'eau', 'ginger beer', 'jus de pomme', 'madeira', 'porto blanc', 'riesling', 'rhum brun',
        'rhum brun épicé', 'rhum cubain', 'vin blanc', 'vodka', "volumes d'eau",
    ]),
]

# tout le rayon épices / huiles / condiments est "placard", plus ces produits des autres rayons
RAYONS_PLACARD = {'Épices, huiles & condiments'}
PLACARD = [
    'eau', "volumes d'eau", 'farine', 'maïzena', 'fécule de pomme de terre', 'levure chimique', 'levure boulangère',
    'sucre', 'sucre fin', 'sucre roux', 'sucre glace', 'sucre de canne', 'cassonade', 'volume de sucre',
    'extrait de vanille', 'miel', 'sauce soja', 'huile de sésame', 'vinaigre de riz',
]


def ranger_produits(apps, schema_editor):
    Rayon = apps.get_model('recette', 'Rayon')
    Produit = apps.get_model('recette', 'Produit')
    nb_rayon = nb_placard = 0

    for nom_rayon, no_ordre, produits in RAYONS:
        rayon, _ = Rayon.objects.get_or_create(nom=nom_rayon, defaults={'noOrdre': no_ordre})
        for nom in produits:
            nb_rayon += Produit.objects.filter(nom__iexact=nom, rayon__isnull=True).update(rayon=rayon)
        if nom_rayon in RAYONS_PLACARD:
            nb_placard += Produit.objects.filter(rayon=rayon, placard=False).update(placard=True)

    for nom in PLACARD:
        nb_placard += Produit.objects.filter(nom__iexact=nom, placard=False).update(placard=True)

    sans_rayon = Produit.objects.filter(rayon__isnull=True, produitDeBase__isnull=True).values_list('nom', flat=True)
    print(f"\n  {nb_rayon} produit(s) rangé(s), {nb_placard} placard ; sans rayon : {', '.join(sans_rayon) or 'aucun'}")


class Migration(migrations.Migration):

    dependencies = [
        ('recette', '0035_rayon_placard'),
    ]

    operations = [
        migrations.RunPython(ranger_produits, migrations.RunPython.noop),
    ]

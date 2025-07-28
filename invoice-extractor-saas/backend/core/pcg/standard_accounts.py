"""
Standard French Plan Comptable Général (PCG) Account Definitions

Provides standard French accounting accounts with proper categorization,
keywords for intelligent mapping, and software-specific mappings.

Covers the most common accounts used by expert-comptables for:
- General expenses (Class 6)
- Revenue accounts (Class 7) 
- Third-party accounts (Class 4)
- TVA accounts (Class 445)
- Asset accounts (Class 2)

Ready for production use with zero-decision workflow.
"""

from typing import List, Dict, Any
from decimal import Decimal

# Standard French TVA rates
FRENCH_TVA_RATES = {
    "STANDARD": 20.0,     # Taux normal
    "REDUCED_1": 10.0,    # Taux réduit
    "REDUCED_2": 5.5,     # Taux réduit (alimentaire, livres)
    "SUPER_REDUCED": 2.1, # Taux super réduit (presse, médicaments)
    "EXEMPT": 0.0         # Exonéré
}


def get_standard_pcg_accounts() -> List[Dict[str, Any]]:
    """
    Get comprehensive list of standard French PCG accounts for MVP
    
    Returns:
        List of account dictionaries ready for database insertion
    """
    
    accounts = []
    
    # ==========================================
    # CLASS 1 - COMPTES DE CAPITAUX
    # ==========================================
    
    accounts.extend([
        {
            "account_code": "101000",
            "account_name": "Capital social",
            "account_category": "capitaux",
            "account_subcategory": "capital",
            "vat_applicable": False,
            "keywords": ["capital", "social", "apport", "souscription"],
            "sage_mapping": "101000",
            "ebp_mapping": "101000",
            "ciel_mapping": "101000"
        },
        {
            "account_code": "106000", 
            "account_name": "Réserves",
            "account_category": "capitaux",
            "account_subcategory": "reserves",
            "vat_applicable": False,
            "keywords": ["réserve", "bénéfice", "report"],
            "sage_mapping": "106000",
            "ebp_mapping": "106000", 
            "ciel_mapping": "106000"
        },
        {
            "account_code": "120000",
            "account_name": "Résultat de l'exercice",
            "account_category": "capitaux",
            "account_subcategory": "resultat",
            "vat_applicable": False,
            "keywords": ["résultat", "exercice", "bénéfice", "perte"],
            "sage_mapping": "120000",
            "ebp_mapping": "120000",
            "ciel_mapping": "120000"
        }
    ])
    
    # ==========================================
    # CLASS 2 - COMPTES D'IMMOBILISATIONS
    # ==========================================
    
    accounts.extend([
        {
            "account_code": "218100",
            "account_name": "Installations générales, agencements",
            "account_category": "immobilisations",
            "account_subcategory": "corporelles",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["installation", "agencement", "aménagement", "bureau"],
            "sage_mapping": "218100",
            "ebp_mapping": "2181",
            "ciel_mapping": "218100"
        },
        {
            "account_code": "218300",
            "account_name": "Matériel de bureau et matériel informatique",
            "account_category": "immobilisations", 
            "account_subcategory": "corporelles",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["ordinateur", "informatique", "matériel", "bureau", "hardware", "serveur", "écran", "imprimante"],
            "sage_mapping": "218300",
            "ebp_mapping": "2183",
            "ciel_mapping": "218300"
        },
        {
            "account_code": "218700",
            "account_name": "Agencements et aménagements de terrains",
            "account_category": "immobilisations",
            "account_subcategory": "corporelles", 
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["agencement", "aménagement", "terrain", "extérieur"],
            "sage_mapping": "218700",
            "ebp_mapping": "2187",
            "ciel_mapping": "218700"
        }
    ])
    
    # ==========================================
    # CLASS 4 - COMPTES DE TIERS
    # ==========================================
    
    # Fournisseurs
    accounts.extend([
        {
            "account_code": "401000",
            "account_name": "Fournisseurs",
            "account_category": "tiers",
            "account_subcategory": "fournisseurs",
            "vat_applicable": False,
            "keywords": ["fournisseur", "dettes", "achat"],
            "sage_mapping": "401000",
            "ebp_mapping": "4010",
            "ciel_mapping": "401000"
        },
        {
            "account_code": "403000",
            "account_name": "Fournisseurs - Effets à payer",
            "account_category": "tiers",
            "account_subcategory": "fournisseurs",
            "vat_applicable": False,
            "keywords": ["effet", "payer", "traite", "billet"],
            "sage_mapping": "403000",
            "ebp_mapping": "4030",
            "ciel_mapping": "403000"
        }
    ])
    
    # Clients
    accounts.extend([
        {
            "account_code": "411000",
            "account_name": "Clients",
            "account_category": "tiers", 
            "account_subcategory": "clients",
            "vat_applicable": False,
            "keywords": ["client", "créance", "vente"],
            "sage_mapping": "411000",
            "ebp_mapping": "4110",
            "ciel_mapping": "411000"
        },
        {
            "account_code": "413000",
            "account_name": "Clients - Effets à recevoir",
            "account_category": "tiers",
            "account_subcategory": "clients",
            "vat_applicable": False,
            "keywords": ["effet", "recevoir", "traite", "encaissement"],
            "sage_mapping": "413000",
            "ebp_mapping": "4130",
            "ciel_mapping": "413000"
        }
    ])
    
    # TVA Déductible (445)
    accounts.extend([
        {
            "account_code": "445661",
            "account_name": "TVA déductible sur immobilisations",
            "account_category": "tiers",
            "account_subcategory": "tva_deductible",
            "vat_applicable": False,
            "keywords": ["tva", "déductible", "immobilisation", "investissement"],
            "sage_mapping": "445661",
            "ebp_mapping": "44566",
            "ciel_mapping": "445661"
        },
        {
            "account_code": "445662",
            "account_name": "TVA déductible sur biens et services",
            "account_category": "tiers",
            "account_subcategory": "tva_deductible",
            "vat_applicable": False,
            "keywords": ["tva", "déductible", "bien", "service", "20%"],
            "sage_mapping": "445662",
            "ebp_mapping": "44566",
            "ciel_mapping": "445662"
        },
        {
            "account_code": "445663",
            "account_name": "TVA déductible sur services 10%",
            "account_category": "tiers",
            "account_subcategory": "tva_deductible",
            "vat_applicable": False,
            "keywords": ["tva", "déductible", "service", "10%", "réduit"],
            "sage_mapping": "445663",
            "ebp_mapping": "44566",
            "ciel_mapping": "445663"
        },
        {
            "account_code": "445664",
            "account_name": "TVA déductible autres taux",
            "account_category": "tiers",
            "account_subcategory": "tva_deductible",
            "vat_applicable": False,
            "keywords": ["tva", "déductible", "autre", "5.5%", "2.1%", "exonéré"],
            "sage_mapping": "445664",
            "ebp_mapping": "44566",
            "ciel_mapping": "445664"
        }
    ])
    
    # TVA Collectée (445)
    accounts.extend([
        {
            "account_code": "445711",
            "account_name": "TVA collectée 20%",
            "account_category": "tiers",
            "account_subcategory": "tva_collectee",
            "vat_applicable": False,
            "keywords": ["tva", "collectée", "20%", "normal"],
            "sage_mapping": "445711",
            "ebp_mapping": "44571",
            "ciel_mapping": "445711"
        },
        {
            "account_code": "445712",
            "account_name": "TVA collectée 10%",
            "account_category": "tiers",
            "account_subcategory": "tva_collectee",
            "vat_applicable": False,
            "keywords": ["tva", "collectée", "10%", "réduit"],
            "sage_mapping": "445712",
            "ebp_mapping": "44571",
            "ciel_mapping": "445712"
        },
        {
            "account_code": "445713",
            "account_name": "TVA collectée 5,5%",
            "account_category": "tiers",
            "account_subcategory": "tva_collectee",
            "vat_applicable": False,
            "keywords": ["tva", "collectée", "5.5%", "super", "réduit"],
            "sage_mapping": "445713",
            "ebp_mapping": "44571",
            "ciel_mapping": "445713"
        },
        {
            "account_code": "445714",
            "account_name": "TVA collectée 2,1%",
            "account_category": "tiers",
            "account_subcategory": "tva_collectee",
            "vat_applicable": False,
            "keywords": ["tva", "collectée", "2.1%", "presse", "médicament"],
            "sage_mapping": "445714",
            "ebp_mapping": "44571",
            "ciel_mapping": "445714"
        }
    ])
    
    # ==========================================
    # CLASS 6 - COMPTES DE CHARGES (EXPENSES) 
    # ==========================================
    
    # Achats (60x)
    accounts.extend([
        {
            "account_code": "601000",
            "account_name": "Achats de matières premières",
            "account_category": "charges",
            "account_subcategory": "achats",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["matière", "première", "matériau", "composant", "fourniture"],
            "sage_mapping": "601000",
            "ebp_mapping": "6010",
            "ciel_mapping": "601000"
        },
        {
            "account_code": "606000",
            "account_name": "Achats non stockés de matières et fournitures",
            "account_category": "charges",
            "account_subcategory": "achats",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["fourniture", "consommable", "petit", "matériel"],
            "sage_mapping": "606000",
            "ebp_mapping": "6060",
            "ciel_mapping": "606000"
        },
        {
            "account_code": "607000",
            "account_name": "Achats de marchandises",
            "account_category": "charges",
            "account_subcategory": "achats",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["marchandise", "stock", "produit", "revente"],
            "sage_mapping": "607000",
            "ebp_mapping": "6070",
            "ciel_mapping": "607000"
        }
    ])
    
    # Services extérieurs (61x)
    accounts.extend([
        {
            "account_code": "611000",
            "account_name": "Sous-traitance générale",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["sous-traitance", "prestation", "service", "externe"],
            "sage_mapping": "611000",
            "ebp_mapping": "6110",
            "ciel_mapping": "611000"
        },
        {
            "account_code": "613000",
            "account_name": "Locations",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["location", "loyer", "bail", "immobilier"],
            "sage_mapping": "613000",
            "ebp_mapping": "6130",
            "ciel_mapping": "613000"
        },
        {
            "account_code": "614000",
            "account_name": "Charges locatives et de copropriété",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["charge", "locative", "copropriété", "syndic"],
            "sage_mapping": "614000",
            "ebp_mapping": "6140",
            "ciel_mapping": "614000"
        },
        {
            "account_code": "615000",
            "account_name": "Entretien et réparations",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["entretien", "réparation", "maintenance", "dépannage"],
            "sage_mapping": "615000",
            "ebp_mapping": "6150",
            "ciel_mapping": "615000"
        },
        {
            "account_code": "616000",
            "account_name": "Primes d'assurances",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["assurance", "prime", "garantie", "protection"],
            "sage_mapping": "616000",
            "ebp_mapping": "6160",
            "ciel_mapping": "616000"
        },
        {
            "account_code": "618000",
            "account_name": "Divers",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["divers", "autre", "frais"],
            "sage_mapping": "618000",
            "ebp_mapping": "6180",
            "ciel_mapping": "618000"
        }
    ])
    
    # Autres services extérieurs (62x)
    accounts.extend([
        {
            "account_code": "621000",
            "account_name": "Personnel extérieur à l'entreprise",
            "account_category": "charges",
            "account_subcategory": "personnel_exterieur",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["intérim", "freelance", "consultant", "mission", "externe"],
            "sage_mapping": "621000",
            "ebp_mapping": "6210",
            "ciel_mapping": "621000"
        },
        {
            "account_code": "622000",
            "account_name": "Rémunérations d'intermédiaires et honoraires",
            "account_category": "charges",
            "account_subcategory": "personnel_exterieur",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["honoraire", "avocat", "expert", "comptable", "conseil"],
            "sage_mapping": "622000",
            "ebp_mapping": "6220",
            "ciel_mapping": "622000"
        },
        {
            "account_code": "623000",
            "account_name": "Publicité, publications, relations publiques",
            "account_category": "charges",
            "account_subcategory": "communication",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["publicité", "marketing", "communication", "affichage", "promotion"],
            "sage_mapping": "623000",
            "ebp_mapping": "6230",
            "ciel_mapping": "623000"
        },
        {
            "account_code": "624100",
            "account_name": "Transports sur achats",
            "account_category": "charges",
            "account_subcategory": "transports",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["transport", "livraison", "fret", "acheminement", "logistique"],
            "sage_mapping": "624100",
            "ebp_mapping": "62410",
            "ciel_mapping": "624100"
        },
        {
            "account_code": "624200",
            "account_name": "Transports sur ventes",
            "account_category": "charges",
            "account_subcategory": "transports",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["transport", "livraison", "expédition", "client"],
            "sage_mapping": "624200",
            "ebp_mapping": "62420",
            "ciel_mapping": "624200"
        },
        {
            "account_code": "625100",
            "account_name": "Voyages et déplacements",
            "account_category": "charges",
            "account_subcategory": "transports",
            "vat_applicable": True,
            "default_vat_rate": 10.0,
            "keywords": ["voyage", "déplacement", "mission", "hôtel", "restaurant"],
            "sage_mapping": "625100",
            "ebp_mapping": "62510",
            "ciel_mapping": "625100"
        },
        {
            "account_code": "625500",
            "account_name": "Frais de colloques, séminaires, conférences",
            "account_category": "charges",
            "account_subcategory": "formation",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["colloque", "séminaire", "conférence", "formation"],
            "sage_mapping": "625500",
            "ebp_mapping": "62550",
            "ciel_mapping": "625500"
        },
        {
            "account_code": "626000",
            "account_name": "Frais postaux et télécommunications",
            "account_category": "charges",
            "account_subcategory": "telecommunications",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["téléphone", "internet", "postal", "courrier", "télécommunication"],
            "sage_mapping": "626000",
            "ebp_mapping": "6260",
            "ciel_mapping": "626000"
        },
        {
            "account_code": "627000",
            "account_name": "Services bancaires et assimilés",
            "account_category": "charges",
            "account_subcategory": "services_bancaires",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["banque", "frais", "commission", "agios", "virement"],
            "sage_mapping": "627000",
            "ebp_mapping": "6270",
            "ciel_mapping": "627000"
        },
        {
            "account_code": "628000",
            "account_name": "Divers",
            "account_category": "charges",
            "account_subcategory": "autres",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["divers", "autre", "cotisation"],
            "sage_mapping": "628000",
            "ebp_mapping": "6280",
            "ciel_mapping": "628000"
        }
    ])
    
    # ==========================================
    # CLASS 7 - COMPTES DE PRODUITS (REVENUE)
    # ==========================================
    
    accounts.extend([
        {
            "account_code": "701000",
            "account_name": "Ventes de produits finis",
            "account_category": "produits",
            "account_subcategory": "ventes",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["vente", "produit", "fini", "manufacture"],
            "sage_mapping": "701000",
            "ebp_mapping": "7010",
            "ciel_mapping": "701000"
        },
        {
            "account_code": "706000",
            "account_name": "Prestations de services",
            "account_category": "produits",
            "account_subcategory": "prestations",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["prestation", "service", "consultation", "conseil"],
            "sage_mapping": "706000",
            "ebp_mapping": "7060",
            "ciel_mapping": "706000"
        },
        {
            "account_code": "707000",
            "account_name": "Ventes de marchandises",
            "account_category": "produits",
            "account_subcategory": "ventes",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["vente", "marchandise", "négoce", "commerce"],
            "sage_mapping": "707000",
            "ebp_mapping": "7070",
            "ciel_mapping": "707000"
        },
        {
            "account_code": "708000",
            "account_name": "Produits des activités annexes",
            "account_category": "produits",
            "account_subcategory": "annexes",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["annexe", "accessoire", "autre"],
            "sage_mapping": "708000",
            "ebp_mapping": "7080",
            "ciel_mapping": "708000"
        }
    ])
    
    return accounts


def get_essential_pcg_accounts() -> List[Dict[str, Any]]:
    """
    Get essential PCG accounts for basic MVP functionality
    
    Returns minimal set of accounts covering 80% of use cases
    """
    
    essential_accounts = [
        # Fournisseurs
        {
            "account_code": "401000",
            "account_name": "Fournisseurs",
            "account_category": "tiers",
            "account_subcategory": "fournisseurs",
            "vat_applicable": False,
            "keywords": ["fournisseur"],
            "sage_mapping": "401000",
            "ebp_mapping": "4010",
            "ciel_mapping": "401000"
        },
        
        # TVA Déductible (les plus courantes)
        {
            "account_code": "445662",
            "account_name": "TVA déductible sur biens et services",
            "account_category": "tiers",
            "account_subcategory": "tva_deductible",
            "vat_applicable": False,
            "keywords": ["tva", "déductible"],
            "sage_mapping": "445662",
            "ebp_mapping": "44566",
            "ciel_mapping": "445662"
        },
        
        # Charges essentielles (Class 6)
        {
            "account_code": "611000",
            "account_name": "Sous-traitance générale",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["service", "prestation", "consultation", "assistance"],
            "sage_mapping": "611000",
            "ebp_mapping": "6110",
            "ciel_mapping": "611000"
        },
        {
            "account_code": "613000",
            "account_name": "Locations",
            "account_category": "charges",
            "account_subcategory": "services_exterieurs",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["location", "loyer"],
            "sage_mapping": "613000",
            "ebp_mapping": "6130",
            "ciel_mapping": "613000"
        },
        {
            "account_code": "624100",
            "account_name": "Transports sur achats",
            "account_category": "charges",
            "account_subcategory": "transports",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["transport", "livraison", "fret"],
            "sage_mapping": "624100",
            "ebp_mapping": "62410",
            "ciel_mapping": "624100"
        },
        {
            "account_code": "626000",
            "account_name": "Frais postaux et télécommunications",
            "account_category": "charges",
            "account_subcategory": "telecommunications",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["téléphone", "internet", "télécommunication"],
            "sage_mapping": "626000",
            "ebp_mapping": "6260",
            "ciel_mapping": "626000"
        },
        {
            "account_code": "607000",
            "account_name": "Achats de marchandises",
            "account_category": "charges",
            "account_subcategory": "achats",
            "vat_applicable": True,
            "default_vat_rate": 20.0,
            "keywords": ["achat", "marchandise", "produit"],
            "sage_mapping": "607000",
            "ebp_mapping": "6070",
            "ciel_mapping": "607000"
        }
    ]
    
    return essential_accounts


def get_tva_mapping_by_rate() -> Dict[float, Dict[str, str]]:
    """
    Get TVA account mapping by rate for quick lookup
    
    Returns:
        Dictionary mapping TVA rates to deductible/collectee account codes
    """
    
    return {
        0.0: {
            "deductible": "445664",  # TVA déductible autres taux
            "collectee": "445714"    # TVA collectée exonérée
        },
        2.1: {
            "deductible": "445664",  # TVA déductible autres taux
            "collectee": "445714"    # TVA collectée 2,1%
        },
        5.5: {
            "deductible": "445664",  # TVA déductible autres taux
            "collectee": "445713"    # TVA collectée 5,5%
        },
        10.0: {
            "deductible": "445663",  # TVA déductible sur services 10%
            "collectee": "445712"    # TVA collectée 10%
        },
        20.0: {
            "deductible": "445662",  # TVA déductible sur biens et services
            "collectee": "445711"    # TVA collectée 20%
        }
    }


def get_category_account_mapping() -> Dict[str, List[str]]:
    """
    Get account codes organized by logical categories for UI selection
    
    Returns:
        Dictionary of categories with their account codes
    """
    
    return {
        "Achats et approvisionnements": [
            "601000",  # Achats de matières premières
            "606000",  # Achats non stockés
            "607000"   # Achats de marchandises
        ],
        "Services extérieurs": [
            "611000",  # Sous-traitance générale
            "613000",  # Locations
            "615000",  # Entretien et réparations
            "616000"   # Primes d'assurances
        ],
        "Frais de personnel externe": [
            "621000",  # Personnel extérieur
            "622000"   # Honoraires
        ],
        "Communication et marketing": [
            "623000"   # Publicité, publications
        ],
        "Transports et déplacements": [
            "624100",  # Transports sur achats
            "624200",  # Transports sur ventes
            "625100"   # Voyages et déplacements
        ],
        "Télécommunications": [
            "626000"   # Frais postaux et télécommunications
        ],
        "Services bancaires": [
            "627000"   # Services bancaires
        ],
        "Immobilisations": [
            "218100",  # Installations générales
            "218300"   # Matériel informatique
        ],
        "TVA déductible": [
            "445661",  # Sur immobilisations
            "445662",  # Sur biens et services
            "445663",  # Sur services 10%
            "445664"   # Autres taux
        ],
        "TVA collectée": [
            "445711",  # 20%
            "445712",  # 10%
            "445713",  # 5,5%
            "445714"   # 2,1%
        ]
    }
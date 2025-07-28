"""
French Compliance Error Taxonomy System

This module provides a comprehensive error taxonomy system for French invoice compliance,
designed specifically for expert-comptables. It provides professional French error messages,
clear fix suggestions, severity assessment, and machine learning capabilities.

Features:
- Professional French error messages with detailed explanations
- Actionable fix suggestions for each error type
- Error severity levels (CRITIQUE, ERREUR, AVERTISSEMENT, INFO)
- Error classification and categorization
- Machine learning from error patterns
- Integration with all validation systems (INSEE, TVA, PCG, etc.)
- Error pattern tracking and analytics
- Context-aware error reporting
"""

import re
import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from models.french_compliance import (
    ValidationErrorPattern,
    ErrorSeverity,
    FRENCH_ERROR_CODES,
    FRENCH_TVA_RATES,
    FRENCH_MANDATORY_FIELDS
)
from core.gdpr_audit import log_audit_event

logger = logging.getLogger(__name__)

class ErrorCategory(str, Enum):
    """Error categories for classification"""
    SIREN_SIRET = "siren_siret"
    TVA_COMPLIANCE = "tva_compliance"
    SEQUENTIAL_NUMBERING = "sequential_numbering"
    MANDATORY_FIELDS = "mandatory_fields"
    BUSINESS_RULES = "business_rules"
    CALCULATION_ERRORS = "calculation_errors"
    LEGAL_REQUIREMENTS = "legal_requirements"
    PCG_MAPPING = "pcg_mapping"
    DOCUMENT_FORMAT = "document_format"
    DATA_QUALITY = "data_quality"

class ErrorContext(str, Enum):
    """Error context for better categorization"""
    INVOICE_CREATION = "invoice_creation"
    INVOICE_VALIDATION = "invoice_validation"
    EXPORT_PREPARATION = "export_preparation"
    ACCOUNTING_INTEGRATION = "accounting_integration"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    DATA_ENTRY = "data_entry"

class FixComplexity(str, Enum):
    """Complexity level for fixing the error"""
    SIMPLE = "simple"          # Can be fixed immediately by user
    MODERATE = "moderate"      # Requires some research or verification
    COMPLEX = "complex"        # May require external validation or documentation
    SYSTEMATIC = "systematic"  # Requires process or system changes

@dataclass
class ErrorDetails:
    """Detailed information about a validation error"""
    code: str
    category: ErrorCategory
    severity: ErrorSeverity
    french_title: str
    french_description: str
    technical_explanation: str
    fix_suggestion: str
    fix_complexity: FixComplexity
    regulatory_reference: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    related_errors: List[str] = field(default_factory=list)
    prevention_tips: List[str] = field(default_factory=list)
    cost_impact: Optional[str] = None

@dataclass
class ValidationError:
    """A specific validation error instance"""
    error_details: ErrorDetails
    context: ErrorContext
    field_name: Optional[str] = None
    field_value: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolution_status: str = "pending"  # pending, resolved, ignored

@dataclass
class ErrorReport:
    """Complete error report for an invoice"""
    invoice_id: str
    validation_timestamp: datetime
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    infos: List[ValidationError] = field(default_factory=list)
    overall_score: float = 100.0
    compliance_status: str = "compliant"
    fix_priority_order: List[str] = field(default_factory=list)
    estimated_fix_time: Optional[str] = None

class FrenchErrorCatalog:
    """Comprehensive catalog of French compliance errors"""
    
    def __init__(self):
        self.error_catalog = self._build_error_catalog()
    
    def _build_error_catalog(self) -> Dict[str, ErrorDetails]:
        """Build comprehensive error catalog with professional French messages"""
        
        catalog = {}
        
        # SIREN/SIRET Errors
        catalog["FR001"] = ErrorDetails(
            code="FR001",
            category=ErrorCategory.SIREN_SIRET,
            severity=ErrorSeverity.ERREUR,
            french_title="Format de numéro SIREN invalide",
            french_description="Le numéro SIREN doit contenir exactement 9 chiffres numériques consécutifs, sans espaces ni caractères spéciaux.",
            technical_explanation="Le SIREN (Système d'Identification du Répertoire des Entreprises) est un identifiant unique à 9 chiffres attribué par l'INSEE à chaque entreprise française.",
            fix_suggestion="Vérifiez la saisie du numéro SIREN. Supprimez tous les espaces, tirets ou autres caractères. Exemple : '123456789' (9 chiffres exactement).",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Article R123-221 du Code de commerce",
            examples=["123456789", "987654321"],
            prevention_tips=[
                "Copiez-collez le SIREN depuis un document officiel (Kbis, etc.)",
                "Utilisez la recherche d'entreprise sur societe.com ou infogreffe.fr",
                "Vérifiez systématiquement les 9 chiffres"
            ]
        )
        
        catalog["FR002"] = ErrorDetails(
            code="FR002",
            category=ErrorCategory.SIREN_SIRET,
            severity=ErrorSeverity.ERREUR,
            french_title="Numéro SIREN incorrect (échec algorithme de Luhn)",
            french_description="Le numéro SIREN ne respecte pas l'algorithme de validation de Luhn. Il contient probablement une erreur de frappe.",
            technical_explanation="L'algorithme de Luhn permet de détecter les erreurs de saisie dans les numéros SIREN en calculant une somme de contrôle.",
            fix_suggestion="Vérifiez chaque chiffre du numéro SIREN en le comparant avec un document officiel. Une erreur de frappe est probablement présente.",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Norme INSEE pour les numéros SIREN",
            examples=["123456782 au lieu de 123456789"],
            prevention_tips=[
                "Double-vérifiez toujours la saisie manuelle",
                "Utilisez la copie-coller depuis des sources fiables",
                "Vérifiez immédiatement après saisie avec un validateur en ligne"
            ]
        )
        
        catalog["FR003"] = ErrorDetails(
            code="FR003",
            category=ErrorCategory.SIREN_SIRET,
            severity=ErrorSeverity.AVERTISSEMENT,
            french_title="Numéro SIREN inexistant dans la base INSEE",
            french_description="Le numéro SIREN, bien que formellement correct, n'existe pas dans le répertoire officiel des entreprises de l'INSEE.",
            technical_explanation="Vérification effectuée auprès de l'API INSEE - base Sirene. L'entreprise peut être fermée ou le numéro peut être erroné.",
            fix_suggestion="Vérifiez l'existence de l'entreprise sur www.insee.fr ou contactez directement le fournisseur pour confirmer son numéro SIREN actuel.",
            fix_complexity=FixComplexity.MODERATE,
            regulatory_reference="Base de données Sirene de l'INSEE",
            related_errors=["FR012"],
            prevention_tips=[
                "Demandez systématiquement un extrait Kbis récent",
                "Vérifiez l'existence de l'entreprise avant facturation",
                "Tenez à jour votre base de données fournisseurs"
            ]
        )
        
        # SIRET Errors
        catalog["FR011"] = ErrorDetails(
            code="FR011",
            category=ErrorCategory.SIREN_SIRET,
            severity=ErrorSeverity.ERREUR,
            french_title="Format de numéro SIRET invalide",
            french_description="Le numéro SIRET doit contenir exactement 14 chiffres : les 9 chiffres du SIREN suivis de 5 chiffres (NIC).",
            technical_explanation="Le SIRET = SIREN (9 chiffres) + NIC (Numéro Interne de Classement, 5 chiffres) identifie un établissement spécifique d'une entreprise.",
            fix_suggestion="Vérifiez que le SIRET contient 14 chiffres consécutifs. Format attendu : SSSSSSSSSXXXXX (S=SIREN, X=NIC).",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Article R123-221 du Code de commerce",
            examples=["12345678901234", "98765432109876"],
            prevention_tips=[
                "Demandez le SIRET de l'établissement exact qui vous facture",
                "Attention : une entreprise peut avoir plusieurs SIRET (plusieurs établissements)",
                "Vérifiez la cohérence SIREN/SIRET"
            ]
        )
        
        catalog["FR012"] = ErrorDetails(
            code="FR012",
            category=ErrorCategory.SIREN_SIRET,
            severity=ErrorSeverity.AVERTISSEMENT,
            french_title="Établissement fermé selon la base INSEE",
            french_description="L'établissement correspondant à ce numéro SIRET apparaît comme fermé dans la base de données INSEE.",
            technical_explanation="L'établissement a été fermé administrativement. Les dates de cessation sont enregistrées dans la base Sirene.",
            fix_suggestion="Contactez le fournisseur pour obtenir le SIRET de son établissement actuel ou vérifiez s'il s'agit d'un transfert d'activité.",
            fix_complexity=FixComplexity.MODERATE,
            regulatory_reference="Base de données Sirene de l'INSEE",
            related_errors=["FR003"],
            prevention_tips=[
                "Vérifiez périodiquement le statut de vos fournisseurs récurrents",
                "Demandez confirmation lors de changements d'adresse",
                "Consultez les avis de modification sur bodacc.fr"
            ]
        )
        
        # TVA Errors
        catalog["FR021"] = ErrorDetails(
            code="FR021",
            category=ErrorCategory.TVA_COMPLIANCE,
            severity=ErrorSeverity.ERREUR,
            french_title="Taux de TVA non conforme à la réglementation française",
            french_description="Le taux de TVA utilisé ne correspond pas aux taux officiels français en vigueur.",
            technical_explanation="En France, les taux de TVA autorisés sont : 20% (normal), 10% (réduit), 5,5% (réduit), 2,1% (super réduit), 0% (exonéré).",
            fix_suggestion="Utilisez uniquement les taux de TVA français autorisés : 20%, 10%, 5,5%, 2,1% ou 0%. Vérifiez la nature du bien/service pour appliquer le bon taux.",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Article 278 et suivants du Code général des impôts",
            examples=["20% pour biens et services standard", "5,5% pour produits alimentaires"],
            related_errors=["FR022", "FR023"],
            prevention_tips=[
                "Consultez le bulletin officiel des impôts pour les taux applicables",
                "Attention aux changements de taux selon la date de facturation",
                "Formez-vous sur les spécificités sectorielles"
            ],
            cost_impact="Risque de redressement fiscal et pénalités"
        )
        
        catalog["FR022"] = ErrorDetails(
            code="FR022",
            category=ErrorCategory.CALCULATION_ERRORS,
            severity=ErrorSeverity.ERREUR,
            french_title="Erreur de calcul de la TVA",
            french_description="Le montant de TVA calculé ne correspond pas à l'application du taux sur la base hors taxes.",
            technical_explanation="Formule de calcul : Montant TVA = Montant HT × (Taux TVA / 100). Le montant TTC = Montant HT + Montant TVA.",
            fix_suggestion="Recalculez : TVA = Montant HT × Taux TVA / 100. Vérifiez les arrondis (règle : arrondi au centime le plus proche).",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Article 266 du Code général des impôts",
            examples=[
                "100€ HT × 20% = 20€ TVA → 120€ TTC",
                "50,25€ HT × 10% = 5,03€ TVA → 55,28€ TTC"
            ],
            prevention_tips=[
                "Utilisez un logiciel de facturation certifié",
                "Vérifiez systématiquement les calculs automatiques",
                "Attention aux arrondis sur les quantités importantes"
            ]
        )
        
        catalog["FR023"] = ErrorDetails(
            code="FR023",
            category=ErrorCategory.TVA_COMPLIANCE,
            severity=ErrorSeverity.AVERTISSEMENT,
            french_title="Taux de TVA inhabituel pour cette catégorie de produit",
            french_description="Le taux de TVA appliqué semble inhabituel pour la catégorie de produit ou service facturé.",
            technical_explanation="Chaque type de bien ou service a un taux de TVA spécifique défini par la réglementation fiscale.",
            fix_suggestion="Vérifiez que le taux correspond bien à la nature du produit/service. Consultez la documentation fiscale spécialisée si nécessaire.",
            fix_complexity=FixComplexity.MODERATE,
            regulatory_reference="Annexe 2 de la directive 2006/112/CE",
            examples=[
                "Livres : 5,5% (et non 20%)",
                "Restauration sur place : 10% (et non 20%)"
            ],
            prevention_tips=[
                "Maintenez une base de données produits avec les taux corrects",
                "Formez les équipes sur les spécificités sectorielles",
                "Consultez régulièrement les bulletins officiels"
            ]
        )
        
        # Sequential Numbering Errors
        catalog["FR031"] = ErrorDetails(
            code="FR031",
            category=ErrorCategory.SEQUENTIAL_NUMBERING,
            severity=ErrorSeverity.CRITIQUE,
            french_title="Rupture dans la numérotation séquentielle des factures",
            french_description="Une interruption a été détectée dans la séquence de numérotation des factures, ce qui est interdit par la réglementation.",
            technical_explanation="La loi française impose une numérotation continue et chronologique des factures sans interruption ni doublon.",
            fix_suggestion="Identifiez et corrigez la cause de la rupture. Émettez les factures manquantes ou justifiez l'interruption (annulation, etc.).",
            fix_complexity=FixComplexity.COMPLEX,
            regulatory_reference="Article 242 nonies A de l'annexe II du CGI",
            examples=[
                "Suite valide : F001, F002, F003...",
                "Rupture détectée : F001, F002, F005 (F003-F004 manquantes)"
            ],
            related_errors=["FR032"],
            prevention_tips=[
                "Utilisez un logiciel de facturation certifié",
                "Ne supprimez jamais de factures, utilisez les avoirs",
                "Contrôlez régulièrement la séquence de numérotation"
            ],
            cost_impact="Amende jusqu'à 5 000€ par exercice"
        )
        
        catalog["FR032"] = ErrorDetails(
            code="FR032",
            category=ErrorCategory.SEQUENTIAL_NUMBERING,
            severity=ErrorSeverity.ERREUR,
            french_title="Format de numérotation non conforme",
            french_description="Le format de numérotation des factures ne respecte pas les exigences réglementaires françaises.",
            technical_explanation="La numérotation doit être basée sur une séquence continue, chronologique, et peut inclure l'année ou une série.",
            fix_suggestion="Adoptez un format standard : AAAANNNNN ou SSSSS-NNNNN où A=année, S=série, N=numéro séquentiel.",
            fix_complexity=FixComplexity.MODERATE,
            regulatory_reference="Article 242 nonies A de l'annexe II du CGI",
            examples=[
                "2024-0001, 2024-0002, etc.",
                "FA-001, FA-002, etc.",
                "20240001, 20240002, etc."
            ],
            prevention_tips=[
                "Définissez un format dès le début d'activité",
                "Documentez votre système de numérotation",
                "Respectez le même format sur tout l'exercice"
            ]
        )
        
        # Mandatory Fields Errors
        catalog["FR041"] = ErrorDetails(
            code="FR041",
            category=ErrorCategory.MANDATORY_FIELDS,
            severity=ErrorSeverity.ERREUR,
            french_title="Champ obligatoire manquant sur la facture",
            french_description="Un ou plusieurs champs obligatoires selon la réglementation française sont absents de la facture.",
            technical_explanation="La réglementation française impose des mentions obligatoires sur toutes les factures émises par les entreprises.",
            fix_suggestion="Complétez tous les champs obligatoires : numéro, date, informations vendeur/client, montants HT/TVA/TTC, etc.",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Article L441-3 du Code de commerce",
            examples=[
                "Date d'émission obligatoire",
                "Adresse complète du vendeur",
                "Numéro SIREN du vendeur"
            ],
            prevention_tips=[
                "Utilisez un modèle de facture conforme",
                "Vérifiez systématiquement avant envoi",
                "Automatisez les contrôles dans votre logiciel"
            ]
        )
        
        catalog["FR042"] = ErrorDetails(
            code="FR042",
            category=ErrorCategory.LEGAL_REQUIREMENTS,
            severity=ErrorSeverity.ERREUR,
            french_title="Mentions légales B2B manquantes",
            french_description="Les mentions légales obligatoires pour les transactions entre entreprises (B2B) sont absentes.",
            technical_explanation="Les factures B2B doivent contenir des clauses spécifiques : pénalités de retard, indemnité forfaitaire de recouvrement.",
            fix_suggestion="Ajoutez les mentions : 'En cas de retard de paiement, indemnité forfaitaire de 40€ + intérêts au taux BCE + 10 points'.",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Articles L441-6 et L441-10 du Code de commerce",
            examples=[
                "Clause de pénalités de retard obligatoire",
                "Indemnité forfaitaire de recouvrement : 40€",
                "Escompte pour paiement anticipé si applicable"
            ],
            prevention_tips=[
                "Intégrez ces clauses dans vos modèles",
                "Distinguez les factures B2B et B2C",
                "Mettez à jour selon la réglementation"
            ]
        )
        
        # Business Rules Errors
        catalog["FR051"] = ErrorDetails(
            code="FR051",
            category=ErrorCategory.BUSINESS_RULES,
            severity=ErrorSeverity.AVERTISSEMENT,
            french_title="Date d'échéance anormalement éloignée",
            french_description="La date d'échéance semble anormalement éloignée de la date d'émission de la facture.",
            technical_explanation="Les délais de paiement entre entreprises sont réglementés : maximum 60 jours ou 45 jours fin de mois.",
            fix_suggestion="Vérifiez le délai de paiement convenu. Maximum légal : 60 jours à compter de la date d'émission.",
            fix_complexity=FixComplexity.SIMPLE,
            regulatory_reference="Article L441-6 du Code de commerce",
            examples=[
                "Maximum 60 jours date à date",
                "Ou 45 jours fin de mois suivant"
            ],
            prevention_tips=[
                "Négociez des délais conformes dès la commande",
                "Paramétrez correctement vos délais dans le logiciel",
                "Surveillez les délais clients dépassant la norme"
            ]
        )
        
        # PCG Mapping Errors
        catalog["FR061"] = ErrorDetails(
            code="FR061",
            category=ErrorCategory.PCG_MAPPING,
            severity=ErrorSeverity.AVERTISSEMENT,
            french_title="Aucun compte PCG identifié pour cet article",
            french_description="Aucun compte du Plan Comptable Général n'a pu être associé automatiquement à cet article.",
            technical_explanation="Le mappage automatique vers les comptes comptables aide à l'intégration dans les logiciels de comptabilité.",
            fix_suggestion="Vérifiez la description de l'article et associez manuellement le compte PCG approprié (classe 6 pour charges, 7 pour produits).",
            fix_complexity=FixComplexity.MODERATE,
            regulatory_reference="Plan Comptable Général (PCG 2014)",
            examples=[
                "Prestations de service → compte 611xxx",
                "Achats marchandises → compte 607xxx"
            ],
            prevention_tips=[
                "Utilisez des descriptions standardisées",
                "Maintenez une table de correspondance produits/comptes",
                "Formez les équipes aux fondamentaux comptables"
            ]
        )
        
        # Data Quality Errors
        catalog["FR071"] = ErrorDetails(
            code="FR071",
            category=ErrorCategory.DATA_QUALITY,
            severity=ErrorSeverity.INFO,
            french_title="Qualité des données perfectible",
            french_description="La qualité des données extraites pourrait être améliorée pour faciliter le traitement automatique.",
            technical_explanation="Des améliorations dans la structure des données facilitent l'automatisation et réduisent les erreurs.",
            fix_suggestion="Utilisez des formats standardisés, évitez les abréviations non conventionnelles, structurez clairement les informations.",
            fix_complexity=FixComplexity.SIMPLE,
            examples=[
                "Adresses complètes et structurées",
                "Descriptions de produits claires et précises",
                "Montants avec séparateurs décimaux cohérents"
            ],
            prevention_tips=[
                "Standardisez vos processus de saisie",
                "Utilisez des listes déroulantes quand possible",
                "Contrôlez la qualité avant envoi"
            ]
        )
        
        return catalog
    
    def get_error_details(self, error_code: str) -> Optional[ErrorDetails]:
        """Get detailed information for an error code"""
        return self.error_catalog.get(error_code)
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[ErrorDetails]:
        """Get all errors for a specific category"""
        return [error for error in self.error_catalog.values() if error.category == category]
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[ErrorDetails]:
        """Get all errors for a specific severity level"""
        return [error for error in self.error_catalog.values() if error.severity == severity]
    
    def search_errors(self, search_term: str, language: str = "fr") -> List[ErrorDetails]:
        """Search errors by term in French descriptions"""
        search_term_lower = search_term.lower()
        results = []
        
        for error in self.error_catalog.values():
            if (search_term_lower in error.french_title.lower() or 
                search_term_lower in error.french_description.lower() or
                search_term_lower in error.fix_suggestion.lower()):
                results.append(error)
        
        return results

class ErrorClassifier:
    """Classifies and categorizes validation errors intelligently"""
    
    def __init__(self):
        self.catalog = FrenchErrorCatalog()
        self.classification_rules = self._build_classification_rules()
    
    def _build_classification_rules(self) -> Dict[str, Any]:
        """Build rules for automatic error classification"""
        return {
            "field_patterns": {
                r"siren": ErrorCategory.SIREN_SIRET,
                r"siret": ErrorCategory.SIREN_SIRET,
                r"tva|vat": ErrorCategory.TVA_COMPLIANCE,
                r"invoice_number|numero": ErrorCategory.SEQUENTIAL_NUMBERING,
                r"date": ErrorCategory.MANDATORY_FIELDS,
                r"amount|montant": ErrorCategory.CALCULATION_ERRORS
            },
            "content_patterns": {
                r"luhn|algorith": ErrorCategory.SIREN_SIRET,
                r"taux|rate|calcul": ErrorCategory.TVA_COMPLIANCE,
                r"séquen|sequence|gap": ErrorCategory.SEQUENTIAL_NUMBERING,
                r"obligat|manquant|missing": ErrorCategory.MANDATORY_FIELDS,
                r"compte|pcg|comptab": ErrorCategory.PCG_MAPPING
            },
            "severity_escalation": {
                ErrorCategory.SIREN_SIRET: {
                    "format_error": ErrorSeverity.ERREUR,
                    "not_found": ErrorSeverity.AVERTISSEMENT,
                    "closed": ErrorSeverity.AVERTISSEMENT
                },
                ErrorCategory.TVA_COMPLIANCE: {
                    "invalid_rate": ErrorSeverity.ERREUR,
                    "calculation_error": ErrorSeverity.ERREUR,
                    "unusual_rate": ErrorSeverity.AVERTISSEMENT
                },
                ErrorCategory.SEQUENTIAL_NUMBERING: {
                    "gap_detected": ErrorSeverity.CRITIQUE,
                    "format_issue": ErrorSeverity.ERREUR
                }
            }
        }
    
    def classify_error(
        self, 
        error_message: str, 
        field_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ErrorCategory, ErrorSeverity, Optional[str]]:
        """
        Classify an error based on message, field, and context
        
        Returns:
            Tuple of (category, severity, suggested_error_code)
        """
        message_lower = error_message.lower()
        
        # Try to match with existing error codes first
        for code, details in self.catalog.error_catalog.items():
            if self._matches_error_pattern(message_lower, details):
                return details.category, details.severity, code
        
        # Fallback to rule-based classification
        category = self._classify_by_rules(message_lower, field_name)
        severity = self._determine_severity(category, message_lower, context)
        
        return category, severity, None
    
    def _matches_error_pattern(self, message: str, error_details: ErrorDetails) -> bool:
        """Check if message matches known error patterns"""
        keywords = [
            error_details.french_title.lower(),
            error_details.french_description.lower()
        ]
        
        # Simple keyword matching - could be enhanced with NLP
        for keyword in keywords:
            if any(word in message for word in keyword.split()[:3]):  # First 3 words
                return True
        
        return False
    
    def _classify_by_rules(self, message: str, field_name: Optional[str]) -> ErrorCategory:
        """Classify error using pattern matching rules"""
        
        # Check field name patterns first
        if field_name:
            field_lower = field_name.lower()
            for pattern, category in self.classification_rules["field_patterns"].items():
                if re.search(pattern, field_lower):
                    return category
        
        # Check message content patterns
        for pattern, category in self.classification_rules["content_patterns"].items():
            if re.search(pattern, message):
                return category
        
        # Default category
        return ErrorCategory.DATA_QUALITY
    
    def _determine_severity(
        self, 
        category: ErrorCategory, 
        message: str, 
        context: Optional[Dict[str, Any]]
    ) -> ErrorSeverity:
        """Determine severity based on category, message, and context"""
        
        # Critical keywords that escalate severity
        critical_keywords = ["critique", "interdit", "obligatoire", "manquant"]
        warning_keywords = ["inhabituel", "recommandé", "avertissement"]
        
        if any(word in message for word in critical_keywords):
            return ErrorSeverity.CRITIQUE if category == ErrorCategory.SEQUENTIAL_NUMBERING else ErrorSeverity.ERREUR
        
        if any(word in message for word in warning_keywords):
            return ErrorSeverity.AVERTISSEMENT
        
        # Default severity by category
        severity_defaults = {
            ErrorCategory.SIREN_SIRET: ErrorSeverity.ERREUR,
            ErrorCategory.TVA_COMPLIANCE: ErrorSeverity.ERREUR,
            ErrorCategory.SEQUENTIAL_NUMBERING: ErrorSeverity.CRITIQUE,
            ErrorCategory.MANDATORY_FIELDS: ErrorSeverity.ERREUR,
            ErrorCategory.CALCULATION_ERRORS: ErrorSeverity.ERREUR,
            ErrorCategory.LEGAL_REQUIREMENTS: ErrorSeverity.ERREUR,
            ErrorCategory.BUSINESS_RULES: ErrorSeverity.AVERTISSEMENT,
            ErrorCategory.PCG_MAPPING: ErrorSeverity.AVERTISSEMENT,
            ErrorCategory.DATA_QUALITY: ErrorSeverity.INFO
        }
        
        return severity_defaults.get(category, ErrorSeverity.INFO)

class FixSuggestionEngine:
    """Generates actionable fix suggestions for validation errors"""
    
    def __init__(self):
        self.catalog = FrenchErrorCatalog()
        self.fix_templates = self._build_fix_templates()
    
    def _build_fix_templates(self) -> Dict[str, Any]:
        """Build templates for generating contextual fix suggestions"""
        return {
            "siren_format": {
                "template": "Corrigez le format du SIREN : '{value}' → attendu 9 chiffres exactement",
                "steps": [
                    "Supprimez tous les espaces et caractères spéciaux",
                    "Vérifiez que le numéro contient exactement 9 chiffres",
                    "Contrôlez avec un document officiel (Kbis, etc.)"
                ]
            },
            "tva_calculation": {
                "template": "Recalculez la TVA : {amount_ht}€ × {rate}% = {expected_tva}€ (trouvé : {actual_tva}€)",
                "steps": [
                    "Utilisez la formule : Montant HT × Taux TVA / 100",
                    "Arrondissez au centime le plus proche",
                    "Vérifiez que TTC = HT + TVA"
                ]
            },
            "mandatory_field": {
                "template": "Ajoutez le champ obligatoire '{field_name}' à votre facture",
                "steps": [
                    "Identifiez la source de l'information manquante",
                    "Complétez le champ dans votre logiciel",
                    "Vérifiez la conformité avec la réglementation"
                ]
            }
        }
    
    def generate_fix_suggestion(
        self, 
        error_code: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate detailed fix suggestion for an error"""
        
        error_details = self.catalog.get_error_details(error_code)
        if not error_details:
            return self._generate_generic_suggestion(context)
        
        context = context or {}
        
        suggestion = {
            "primary_action": error_details.fix_suggestion,
            "complexity": error_details.fix_complexity.value,
            "steps": self._generate_fix_steps(error_details, context),
            "prevention": error_details.prevention_tips,
            "regulatory_info": error_details.regulatory_reference,
            "examples": error_details.examples,
            "estimated_time": self._estimate_fix_time(error_details.fix_complexity),
            "requires_external_validation": error_details.fix_complexity in [FixComplexity.COMPLEX, FixComplexity.SYSTEMATIC]
        }
        
        # Add contextual information if available
        if context:
            suggestion["contextual_help"] = self._generate_contextual_help(error_details, context)
        
        return suggestion
    
    def _generate_fix_steps(self, error_details: ErrorDetails, context: Dict[str, Any]) -> List[str]:
        """Generate step-by-step fix instructions"""
        
        base_steps = []
        
        if error_details.category == ErrorCategory.SIREN_SIRET:
            if "format" in error_details.code:
                base_steps = [
                    "1. Localisez le document officiel (Kbis, facture précédente)",
                    "2. Copiez exactement le numéro SIREN/SIRET",
                    "3. Supprimez tous les espaces et caractères spéciaux",
                    "4. Vérifiez que vous avez 9 chiffres (SIREN) ou 14 chiffres (SIRET)",
                    "5. Ressaisissez le numéro corrigé dans votre facture"
                ]
            elif "not_found" in error_details.code or "inexistant" in error_details.french_description:
                base_steps = [
                    "1. Vérifiez l'orthographe et l'exactitude du numéro saisi",
                    "2. Consultez www.insee.fr pour vérifier l'existence de l'entreprise",
                    "3. Contactez votre fournisseur pour confirmer ses coordonnées",
                    "4. Demandez un extrait Kbis récent si nécessaire",
                    "5. Mettez à jour vos données fournisseur"
                ]
        
        elif error_details.category == ErrorCategory.TVA_COMPLIANCE:
            if "taux" in error_details.french_description:
                base_steps = [
                    "1. Identifiez la nature exacte du bien ou service",
                    "2. Consultez la grille des taux de TVA français",
                    "3. Appliquez le taux correct : 20%, 10%, 5,5%, 2,1% ou 0%",
                    "4. Recalculez tous les montants",
                    "5. Vérifiez la cohérence HT + TVA = TTC"
                ]
            elif "calcul" in error_details.french_description:
                ht = context.get("amount_ht", 0)
                rate = context.get("rate", 0)
                base_steps = [
                    f"1. Montant HT : {ht}€",
                    f"2. Taux TVA : {rate}%",
                    f"3. Calcul : {ht}€ × {rate}% = {ht * rate / 100:.2f}€",
                    f"4. Montant TTC : {ht + (ht * rate / 100):.2f}€",
                    "5. Arrondissez au centime le plus proche si nécessaire"
                ]
        
        elif error_details.category == ErrorCategory.MANDATORY_FIELDS:
            base_steps = [
                "1. Identifiez le champ manquant dans votre modèle de facture",
                "2. Recherchez l'information requise dans vos données",
                "3. Complétez le champ avec l'information correcte",
                "4. Vérifiez que tous les champs obligatoires sont remplis",
                "5. Mettez à jour votre modèle pour éviter la répétition"
            ]
        
        # Add contextual steps if specific field is mentioned
        if context.get("field_name"):
            field_name = context["field_name"]
            base_steps.insert(1, f"1.5. Focus sur le champ '{field_name}'")
        
        return base_steps or ["Consultez la documentation spécialisée pour ce type d'erreur"]
    
    def _generate_contextual_help(self, error_details: ErrorDetails, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate contextual help based on specific error context"""
        
        help_info = {}
        
        # Add specific values if available
        if context.get("field_value"):
            help_info["current_value"] = f"Valeur actuelle : '{context['field_value']}'"
        
        if context.get("expected_value"):
            help_info["expected_value"] = f"Valeur attendue : '{context['expected_value']}'"
        
        # Add calculation details for numerical errors
        if error_details.category == ErrorCategory.CALCULATION_ERRORS:
            if all(key in context for key in ["amount_ht", "rate", "expected_tva", "actual_tva"]):
                help_info["calculation_details"] = (
                    f"Calcul attendu : {context['amount_ht']}€ × {context['rate']}% = "
                    f"{context['expected_tva']}€ (trouvé : {context['actual_tva']}€)"
                )
        
        # Add regulatory context
        if error_details.regulatory_reference:
            help_info["legal_reference"] = f"Base légale : {error_details.regulatory_reference}"
        
        return help_info
    
    def _estimate_fix_time(self, complexity: FixComplexity) -> str:
        """Estimate time needed to fix the error"""
        time_estimates = {
            FixComplexity.SIMPLE: "1-5 minutes",
            FixComplexity.MODERATE: "10-30 minutes", 
            FixComplexity.COMPLEX: "1-2 heures",
            FixComplexity.SYSTEMATIC: "Plusieurs heures à plusieurs jours"
        }
        return time_estimates.get(complexity, "Temps indéterminé")
    
    def _generate_generic_suggestion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate generic suggestion when specific error is not recognized"""
        return {
            "primary_action": "Vérifiez et corrigez les données selon la réglementation française",
            "complexity": "moderate",
            "steps": [
                "1. Analysez le message d'erreur en détail",
                "2. Consultez la documentation réglementaire appropriée",
                "3. Corrigez les données identifiées",
                "4. Testez la validation à nouveau",
                "5. Documentez la correction pour éviter la répétition"
            ],
            "prevention": ["Utilisez des logiciels certifiés", "Formez les équipes", "Contrôlez régulièrement"],
            "estimated_time": "15-45 minutes"
        }

class ErrorPatternTracker:
    """Tracks error patterns and learns from resolution history"""
    
    def __init__(self):
        self.pattern_cache = {}
    
    async def track_error_pattern(
        self, 
        error: ValidationError,
        db_session: AsyncSession,
        resolution_feedback: Optional[Dict[str, Any]] = None
    ):
        """Track error patterns for machine learning"""
        
        pattern_key = self._generate_pattern_key(error)
        
        # Check if pattern exists
        stmt = select(ValidationErrorPattern).where(
            ValidationErrorPattern.error_type == error.error_details.category.value,
            ValidationErrorPattern.error_subtype == error.error_details.code
        )
        
        existing_pattern = await db_session.execute(stmt)
        pattern = existing_pattern.scalar_one_or_none()
        
        if pattern:
            # Update existing pattern
            pattern.increment_occurrence()
            if resolution_feedback:
                await self._update_pattern_success_rate(pattern, resolution_feedback, db_session)
        else:
            # Create new pattern
            pattern = ValidationErrorPattern(
                error_type=error.error_details.category.value,
                error_subtype=error.error_details.code,
                pattern_data={
                    "field_name": error.field_name,
                    "field_value": error.field_value,
                    "context": error.context.value,
                    "additional_info": error.additional_info
                },
                suggested_fixes=[error.error_details.fix_suggestion],
                occurrence_count=1
            )
            db_session.add(pattern)
        
        # Log audit event
        await log_audit_event(
            db_session,
            user_id=None,
            operation_type="error_pattern_tracking",
            data_categories=["validation_data", "error_patterns"],
            risk_level="low",
            details={
                "error_code": error.error_details.code,
                "pattern_key": pattern_key,
                "occurrence_count": pattern.occurrence_count if pattern else 1,
                "purpose": "error_pattern_analysis"
            }
        )
        
        await db_session.commit()
    
    def _generate_pattern_key(self, error: ValidationError) -> str:
        """Generate unique pattern key for error"""
        components = [
            error.error_details.category.value,
            error.error_details.code,
            error.field_name or "no_field",
            error.context.value
        ]
        return "|".join(components)
    
    async def _update_pattern_success_rate(
        self, 
        pattern: ValidationErrorPattern,
        feedback: Dict[str, Any],
        db_session: AsyncSession
    ):
        """Update pattern success rate based on user feedback"""
        
        if feedback.get("resolution_successful"):
            # Improve success rate
            current_rate = pattern.resolution_success_rate or 50.0
            new_rate = min(100.0, current_rate + 5.0)
            pattern.resolution_success_rate = new_rate
            
            # Add successful fix to suggestions if not already there
            fix_method = feedback.get("fix_method")
            if fix_method and fix_method not in pattern.suggested_fixes:
                pattern.suggested_fixes.append(fix_method)
        
        elif feedback.get("resolution_successful") is False:
            # Decrease success rate
            current_rate = pattern.resolution_success_rate or 50.0
            new_rate = max(0.0, current_rate - 3.0)
            pattern.resolution_success_rate = new_rate
    
    async def get_pattern_insights(
        self, 
        db_session: AsyncSession,
        category: Optional[ErrorCategory] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get insights about error patterns"""
        
        # Build query for pattern analysis
        query = select(ValidationErrorPattern)
        
        if category:
            query = query.where(ValidationErrorPattern.error_type == category.value)
        
        # Get recent patterns
        cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_back)
        
        query = query.where(ValidationErrorPattern.last_seen >= cutoff_date)
        query = query.order_by(ValidationErrorPattern.occurrence_count.desc())
        
        result = await db_session.execute(query)
        patterns = result.scalars().all()
        
        # Analyze patterns
        insights = {
            "most_common_errors": [],
            "success_rates": {},
            "trending_errors": [],
            "recommendations": []
        }
        
        for pattern in patterns[:10]:  # Top 10 patterns
            insights["most_common_errors"].append({
                "error_type": pattern.error_type,
                "error_subtype": pattern.error_subtype,
                "occurrence_count": pattern.occurrence_count,
                "success_rate": pattern.resolution_success_rate
            })
            
            if pattern.resolution_success_rate:
                insights["success_rates"][pattern.error_subtype] = pattern.resolution_success_rate
        
        # Generate recommendations
        low_success_patterns = [p for p in patterns if (p.resolution_success_rate or 0) < 70]
        if low_success_patterns:
            insights["recommendations"].append(
                "Améliorez la documentation pour les erreurs avec faible taux de résolution"
            )
        
        high_frequency_patterns = [p for p in patterns if p.occurrence_count > 50]
        if high_frequency_patterns:
            insights["recommendations"].append(
                "Automatisez les corrections pour les erreurs les plus fréquentes"
            )
        
        return insights

class FrenchComplianceErrorTaxonomy:
    """
    Main service for French compliance error taxonomy
    Orchestrates error classification, suggestions, and pattern learning
    """
    
    def __init__(self):
        self.catalog = FrenchErrorCatalog()
        self.classifier = ErrorClassifier()
        self.suggestion_engine = FixSuggestionEngine()
        self.pattern_tracker = ErrorPatternTracker()
    
    async def process_validation_errors(
        self,
        raw_errors: List[str],
        context: ErrorContext,
        invoice_id: str,
        db_session: AsyncSession,
        field_mappings: Optional[Dict[str, str]] = None
    ) -> ErrorReport:
        """
        Process raw validation errors into structured error report
        
        Args:
            raw_errors: Raw error messages from validators
            context: Context in which errors occurred
            invoice_id: Invoice identifier
            db_session: Database session
            field_mappings: Optional mapping of error messages to field names
            
        Returns:
            Complete structured error report
        """
        
        field_mappings = field_mappings or {}
        
        # GDPR audit log
        await log_audit_event(
            db_session,
            user_id=None,
            operation_type="error_taxonomy_processing",
            data_categories=["validation_errors", "error_analysis"],
            risk_level="low",
            details={
                "invoice_id": invoice_id,
                "error_count": len(raw_errors),
                "context": context.value,
                "purpose": "french_compliance_error_processing"
            }
        )
        
        report = ErrorReport(
            invoice_id=invoice_id,
            validation_timestamp=datetime.utcnow()
        )
        
        for raw_error in raw_errors:
            try:
                # Extract field name if possible
                field_name = self._extract_field_name(raw_error, field_mappings)
                
                # Classify the error
                category, severity, suggested_code = self.classifier.classify_error(
                    raw_error, field_name, {"context": context.value}
                )
                
                # Get or create error details
                if suggested_code:
                    error_details = self.catalog.get_error_details(suggested_code)
                else:
                    error_details = self._create_generic_error_details(
                        raw_error, category, severity
                    )
                
                # Create validation error
                validation_error = ValidationError(
                    error_details=error_details,
                    context=context,
                    field_name=field_name,
                    field_value=self._extract_field_value(raw_error),
                    additional_info={"raw_message": raw_error}
                )
                
                # Add to appropriate list based on severity
                if severity == ErrorSeverity.CRITIQUE:
                    report.errors.append(validation_error)
                elif severity == ErrorSeverity.ERREUR:
                    report.errors.append(validation_error)
                elif severity == ErrorSeverity.AVERTISSEMENT:
                    report.warnings.append(validation_error)
                else:
                    report.infos.append(validation_error)
                
                # Track pattern
                await self.pattern_tracker.track_error_pattern(
                    validation_error, db_session
                )
                
            except Exception as e:
                logger.error(f"Error processing validation error '{raw_error}': {e}")
                # Add as generic error
                generic_error = self._create_fallback_error(raw_error, context)
                report.errors.append(generic_error)
        
        # Calculate overall score and compliance status
        report.overall_score = self._calculate_overall_score(report)
        report.compliance_status = self._determine_compliance_status(report)
        report.fix_priority_order = self._generate_fix_priority_order(report)
        report.estimated_fix_time = self._estimate_total_fix_time(report)
        
        return report
    
    def _extract_field_name(self, error_message: str, field_mappings: Dict[str, str]) -> Optional[str]:
        """Extract field name from error message"""
        
        # Check explicit mappings first
        for pattern, field_name in field_mappings.items():
            if pattern.lower() in error_message.lower():
                return field_name
        
        # Common field patterns
        field_patterns = {
            r"siren": "siren_number",
            r"siret": "siret_number", 
            r"tva|vat": "tva_number",
            r"invoice.number|numéro": "invoice_number",
            r"date": "date",
            r"amount|montant": "amount",
            r"vendor|vendeur|fournisseur": "vendor_name",
            r"customer|client": "customer_name"
        }
        
        for pattern, field_name in field_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return field_name
        
        return None
    
    def _extract_field_value(self, error_message: str) -> Optional[str]:
        """Extract field value from error message if present"""
        
        # Look for quoted values
        quoted_match = re.search(r"['\"]([^'\"]+)['\"]", error_message)
        if quoted_match:
            return quoted_match.group(1)
        
        # Look for numeric values
        number_match = re.search(r"\b(\d{4,14})\b", error_message)
        if number_match:
            return number_match.group(1)
        
        return None
    
    def _create_generic_error_details(
        self, 
        message: str, 
        category: ErrorCategory, 
        severity: ErrorSeverity
    ) -> ErrorDetails:
        """Create generic error details for unrecognized errors"""
        
        return ErrorDetails(
            code="FR999",
            category=category,
            severity=severity,
            french_title="Erreur de validation détectée",
            french_description=f"Une erreur de validation a été détectée : {message}",
            technical_explanation="Erreur non cataloguée nécessitant une analyse manuelle.",
            fix_suggestion="Vérifiez les données et consultez la documentation appropriée.",
            fix_complexity=FixComplexity.MODERATE,
            examples=[],
            prevention_tips=["Contrôlez la qualité des données en amont"]
        )
    
    def _create_fallback_error(self, message: str, context: ErrorContext) -> ValidationError:
        """Create fallback error for processing failures"""
        
        error_details = ErrorDetails(
            code="FR998",
            category=ErrorCategory.DATA_QUALITY,
            severity=ErrorSeverity.INFO,
            french_title="Erreur de traitement",
            french_description=f"Impossible de traiter automatiquement cette erreur : {message}",
            technical_explanation="Le système n'a pas pu analyser automatiquement cette erreur.",
            fix_suggestion="Analysez manuellement le message d'erreur et consultez la documentation.",
            fix_complexity=FixComplexity.MODERATE
        )
        
        return ValidationError(
            error_details=error_details,
            context=context,
            additional_info={"processing_failed": True, "raw_message": message}
        )
    
    def _calculate_overall_score(self, report: ErrorReport) -> float:
        """Calculate overall compliance score"""
        
        score = 100.0
        
        # Deduct for errors based on severity
        for error in report.errors:
            if error.error_details.severity == ErrorSeverity.CRITIQUE:
                score -= 20
            elif error.error_details.severity == ErrorSeverity.ERREUR:
                score -= 10
        
        # Deduct for warnings
        score -= len(report.warnings) * 3
        
        # Deduct for info items
        score -= len(report.infos) * 1
        
        return max(0.0, score)
    
    def _determine_compliance_status(self, report: ErrorReport) -> str:
        """Determine overall compliance status"""
        
        critical_errors = [e for e in report.errors 
                          if e.error_details.severity == ErrorSeverity.CRITIQUE]
        
        if critical_errors:
            return "non_compliant_critical"
        elif report.errors:
            return "non_compliant"
        elif report.warnings:
            return "compliant_with_warnings"
        else:
            return "fully_compliant"
    
    def _generate_fix_priority_order(self, report: ErrorReport) -> List[str]:
        """Generate prioritized order for fixing errors"""
        
        # Priority order: Critical > Error > Warning > Info
        # Within same severity: Legal > Financial > Data Quality
        
        all_issues = report.errors + report.warnings + report.infos
        
        priority_weights = {
            ErrorSeverity.CRITIQUE: 1000,
            ErrorSeverity.ERREUR: 100,
            ErrorSeverity.AVERTISSEMENT: 10,
            ErrorSeverity.INFO: 1
        }
        
        category_weights = {
            ErrorCategory.SEQUENTIAL_NUMBERING: 50,
            ErrorCategory.LEGAL_REQUIREMENTS: 40,
            ErrorCategory.TVA_COMPLIANCE: 30,
            ErrorCategory.SIREN_SIRET: 20,
            ErrorCategory.MANDATORY_FIELDS: 15,
            ErrorCategory.CALCULATION_ERRORS: 10,
            ErrorCategory.BUSINESS_RULES: 5,
            ErrorCategory.PCG_MAPPING: 3,
            ErrorCategory.DATA_QUALITY: 1
        }
        
        def priority_score(error: ValidationError) -> int:
            severity_score = priority_weights.get(error.error_details.severity, 1)
            category_score = category_weights.get(error.error_details.category, 1)
            return severity_score + category_score
        
        sorted_issues = sorted(all_issues, key=priority_score, reverse=True)
        
        return [f"{issue.error_details.code}: {issue.error_details.french_title}" 
                for issue in sorted_issues]
    
    def _estimate_total_fix_time(self, report: ErrorReport) -> str:
        """Estimate total time needed to fix all issues"""
        
        time_mapping = {
            FixComplexity.SIMPLE: 5,      # 5 minutes
            FixComplexity.MODERATE: 20,   # 20 minutes
            FixComplexity.COMPLEX: 90,    # 1.5 hours
            FixComplexity.SYSTEMATIC: 480 # 8 hours
        }
        
        total_minutes = 0
        all_issues = report.errors + report.warnings + report.infos
        
        for issue in all_issues:
            complexity = issue.error_details.fix_complexity
            total_minutes += time_mapping.get(complexity, 20)
        
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        elif total_minutes < 480:
            hours = total_minutes / 60
            return f"{hours:.1f} heures"
        else:
            days = total_minutes / 480
            return f"{days:.1f} jours"
    
    async def get_fix_suggestions(
        self, 
        error_codes: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get detailed fix suggestions for multiple errors"""
        
        suggestions = {}
        
        for code in error_codes:
            suggestions[code] = self.suggestion_engine.generate_fix_suggestion(
                code, context
            )
        
        return suggestions
    
    async def report_fix_feedback(
        self,
        error_code: str,
        success: bool,
        fix_method: Optional[str],
        time_taken: Optional[int],
        db_session: AsyncSession,
        user_comments: Optional[str] = None
    ):
        """Report feedback on error fix attempts"""
        
        feedback = {
            "resolution_successful": success,
            "fix_method": fix_method,
            "time_taken_minutes": time_taken,
            "user_comments": user_comments,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Find the error pattern
        stmt = select(ValidationErrorPattern).where(
            ValidationErrorPattern.error_subtype == error_code
        )
        
        result = await db_session.execute(stmt)
        pattern = result.scalar_one_or_none()
        
        if pattern:
            await self.pattern_tracker._update_pattern_success_rate(
                pattern, feedback, db_session
            )
        
        # Log audit event
        await log_audit_event(
            db_session,
            user_id=None,
            operation_type="error_fix_feedback",
            data_categories=["user_feedback", "resolution_data"],
            risk_level="low",
            details={
                "error_code": error_code,
                "success": success,
                "feedback": feedback,
                "purpose": "error_resolution_improvement"
            }
        )
        
        await db_session.commit()
    
    async def get_error_analytics(
        self, 
        db_session: AsyncSession,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get analytics about error patterns and resolution"""
        
        return await self.pattern_tracker.get_pattern_insights(
            db_session, days_back=days_back
        )

# Convenience functions for easy integration

async def process_french_compliance_errors(
    errors: List[str],
    context: ErrorContext,
    invoice_id: str,
    db_session: AsyncSession,
    field_mappings: Optional[Dict[str, str]] = None
) -> ErrorReport:
    """
    Convenience function to process French compliance errors
    
    Args:
        errors: Raw error messages
        context: Error context
        invoice_id: Invoice identifier  
        db_session: Database session
        field_mappings: Optional field mappings
        
    Returns:
        Structured error report
    """
    taxonomy = FrenchComplianceErrorTaxonomy()
    return await taxonomy.process_validation_errors(
        errors, context, invoice_id, db_session, field_mappings
    )

def get_error_catalog() -> FrenchErrorCatalog:
    """Get the French error catalog"""
    return FrenchErrorCatalog()

def search_error_solutions(search_term: str) -> List[ErrorDetails]:
    """Search for error solutions by term"""
    catalog = FrenchErrorCatalog()
    return catalog.search_errors(search_term)
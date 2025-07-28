# Guide du Système de Taxonomie d'Erreurs Françaises

## Pour les Expert-Comptables : Validation Professionnelle des Factures

### Vue d'ensemble

Le système de taxonomie d'erreurs françaises d'InvoiceAI fournit une validation de conformité de niveau professionnel spécifiquement conçue pour les expert-comptables. Il offre des messages d'erreur en français, des suggestions de correction détaillées, et une classification intelligent des problèmes de conformité.

## 🎯 Fonctionnalités Clés

### 1. **Validation Complète Multi-Niveaux**
- ✅ Validation SIREN/SIRET avec l'API INSEE
- ✅ Contrôle TVA complet avec détection automatique des taux
- ✅ Vérification de la numérotation séquentielle
- ✅ Validation des champs obligatoires français
- ✅ Mappage automatique Plan Comptable Général (PCG)
- ✅ Contrôles des règles métier

### 2. **Messages d'Erreur Professionnels**
- 🇫🇷 Messages entièrement en français
- 📋 Descriptions détaillées des problèmes
- 🔧 Suggestions de correction étape par étape
- ⏱️ Estimation du temps de correction
- 📚 Références réglementaires

### 3. **Classification Intelligente**
```
CRITIQUE    → Bloque l'utilisation de la facture
ERREUR      → Doit être corrigé avant export
AVERTISSEMENT → À examiner pour améliorer la qualité
INFO        → Suggestions d'optimisation
```

## 📊 Niveaux de Validation

### Validation Rapide
```bash
POST /api/validation-reports/validate
{
  "invoice_data": {...},
  "validation_type": "quick"
}
```
- Contrôles essentiels uniquement
- Temps de réponse : < 2 secondes
- Idéal pour validation en temps réel

### Validation Complète
```bash
POST /api/validation-reports/validate
{
  "invoice_data": {...},
  "validation_type": "comprehensive",
  "include_pcg_mapping": true,
  "include_business_rules": true
}
```
- Tous les contrôles disponibles
- Mapping PCG automatique
- Suggestions d'amélioration

### Validation Export
```bash
POST /api/validation-reports/validate-for-export
{
  "invoice_data": {...},
  "export_format": "sage"
}
```
- Optimisé pour l'export comptable
- Contrôles spécifiques par logiciel
- Mapping des comptes garantie

## 🔍 Catalogue d'Erreurs

### Erreurs SIREN/SIRET

#### FR001 - Format SIREN Invalide
```json
{
  "code": "FR001",
  "severity": "ERREUR",
  "title": "Format de numéro SIREN invalide",
  "description": "Le numéro SIREN doit contenir exactement 9 chiffres numériques consécutifs",
  "fix_suggestion": "Vérifiez que le numéro contient 9 chiffres sans espaces ni caractères spéciaux",
  "fix_complexity": "simple",
  "estimated_time": "1-5 minutes"
}
```

#### FR002 - SIREN Incorrect (Luhn)
- **Problème** : Numéro ne respectant pas l'algorithme de Luhn
- **Cause** : Erreur de frappe probable
- **Solution** : Comparer avec un document officiel (Kbis)

#### FR003 - SIREN Inexistant INSEE
- **Problème** : Numéro non trouvé dans la base INSEE
- **Cause** : Entreprise fermée ou numéro erroné
- **Solution** : Vérifier sur insee.fr ou contacter le fournisseur

### Erreurs TVA

#### FR021 - Taux TVA Non Conforme
```
Taux français autorisés :
- 20% : Taux normal (biens et services standard)
- 10% : Taux réduit (restauration, hôtellerie, transport)
- 5,5% : Taux réduit (alimentaire, livres, médicaments)
- 2,1% : Taux super réduit (presse, médicaments remboursables)
- 0% : Exonéré (export, intracommunautaire, médical)
```

#### FR022 - Erreur Calcul TVA
- **Formule** : TVA = Montant HT × (Taux TVA / 100)
- **Vérification** : TTC = HT + TVA
- **Tolérance** : ±0,02€ pour les arrondis

### Erreurs de Numérotation

#### FR031 - Rupture Séquentielle (CRITIQUE)
- **Impact** : Amende jusqu'à 5 000€ par exercice
- **Obligation** : Numérotation continue et chronologique
- **Action** : Identifier et justifier toute interruption

## 🛠️ Utilisation Pratique

### 1. Validation Automatique
Lors du traitement d'une facture, la validation française est automatiquement déclenchée :

```python
# Intégré dans le processus de traitement
french_validation = await validate_invoice_comprehensive(
    invoice_data,
    db_session,
    ValidationTrigger.AUTO
)
```

### 2. Rapport de Validation
```json
{
  "validation_summary": {
    "overall_compliant": false,
    "compliance_score": 87.5,
    "error_count": 2,
    "warning_count": 1,
    "estimated_fix_time": "15-20 minutes"
  },
  "error_details": [
    {
      "code": "FR001",
      "severity": "ERREUR",
      "french_title": "Format de numéro SIREN invalide",
      "fix_suggestion": "Vérifiez que le numéro SIREN contient 9 chiffres...",
      "field_name": "siren_number",
      "field_value": "12345678"
    }
  ],
  "recommendations": [
    "Mettez à jour votre base de données fournisseurs",
    "Formez vos équipes sur les taux de TVA"
  ],
  "next_actions": [
    "❌ Corrigez les erreurs avant de continuer",
    "🔧 Commencez par: FR001: Format de numéro SIREN invalide",
    "⏱️ Temps estimé de correction: 15-20 minutes"
  ]
}
```

### 3. Suggestions de Correction
```bash
POST /api/validation-reports/errors/fix-suggestions
{
  "error_codes": ["FR001", "FR021"],
  "context": {
    "field_value": "12345678",
    "amount_ht": 100.0,
    "rate": 20.0
  }
}
```

Réponse avec guide étape par étape :
```json
{
  "suggestions": {
    "FR001": {
      "primary_action": "Corrigez le format du SIREN",
      "complexity": "simple",
      "steps": [
        "1. Localisez le document officiel (Kbis)",
        "2. Copiez exactement le numéro SIREN",
        "3. Supprimez tous les espaces et caractères spéciaux",
        "4. Vérifiez que vous avez 9 chiffres exactement",
        "5. Ressaisissez le numéro corrigé"
      ],
      "prevention": [
        "Copiez-collez depuis des sources fiables",
        "Vérifiez immédiatement après saisie"
      ],
      "estimated_time": "1-5 minutes"
    }
  }
}
```

## 📈 Analytics et Suivi

### Dashboard Expert-Comptable
```bash
GET /api/validation-reports/dashboard/summary
```
- Statistiques des 30 derniers jours
- Taux de conformité global
- Erreurs les plus fréquentes
- Validations récentes

### Tendances de Conformité
```bash
GET /api/validation-reports/analytics/compliance-trends?days_back=30
```
- Évolution du score de conformité
- Nombre de validations quotidiennes
- Taux de conformité par jour

### Patterns d'Erreurs
```bash
GET /api/validation-reports/analytics/error-patterns?days_back=30
```
- Erreurs les plus courantes
- Taux de résolution par type d'erreur
- Recommandations d'amélioration

## 🔄 Système d'Apprentissage

### Feedback de Résolution
```bash
POST /api/validation-reports/errors/feedback
{
  "error_code": "FR001",
  "success": true,
  "fix_method": "Correction manuelle depuis Kbis",
  "time_taken_minutes": 3,
  "user_comments": "Erreur de saisie initiale"
}
```

Le système apprend de vos retours pour :
- Améliorer les suggestions
- Affiner les estimations de temps
- Identifier les problèmes récurrents

## 🎓 Formation et Support

### Recherche d'Erreurs
```bash
GET /api/validation-reports/errors/catalog?search="tva"
```
- Recherche dans le catalogue d'erreurs
- Filtrage par catégorie et sévérité
- Solutions détaillées

### Détails d'une Erreur
```bash
GET /api/validation-reports/errors/FR001
```
- Description complète
- Références réglementaires
- Exemples concrets
- Conseils de prévention

## ⚡ Optimisation des Performances

### Mise en Cache
- Validation SIREN/SIRET mise en cache (24h)
- Mappage PCG en mémoire
- Patterns d'erreurs optimisés

### Traitement Asynchrone
- Validation automatique en arrière-plan
- Notification des résultats
- Pas de blocage de l'interface

## 🔒 Conformité GDPR

- Audit de toutes les validations
- Anonymisation des données sensibles
- Traitement conforme au RGPD
- Logs de traçabilité complets

## 🚀 Intégration

### API RESTful
- Endpoints documentés avec OpenAPI
- Authentification JWT
- Gestion d'erreurs standardisée

### Codes de Retour
```
200 OK           - Validation réussie
400 Bad Request  - Données invalides
401 Unauthorized - Authentication requise
422 Unprocessable Entity - Erreurs de validation
500 Internal Server Error - Erreur système
```

## 📞 Support

Pour toute question ou assistance :
- Documentation API : `/docs`
- Support technique : support@invoiceai.fr
- Formation : formation@invoiceai.fr

---

*Ce système de validation est conçu pour les expert-comptables par des expert-comptables, garantissant une conformité réglementaire française optimale.*
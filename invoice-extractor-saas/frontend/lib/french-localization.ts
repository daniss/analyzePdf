/**
 * French Localization for InvoiceAI France
 * 
 * Provides French translations and formatting for the application
 * specifically tailored for French accounting professionals.
 */

export const frenchTranslations = {
  // Common terms
  common: {
    loading: "Chargement...",
    save: "Enregistrer",
    cancel: "Annuler",
    delete: "Supprimer",
    edit: "Modifier",
    create: "Créer",
    update: "Mettre à jour",
    search: "Rechercher",
    filter: "Filtrer",
    export: "Exporter",
    import: "Importer",
    download: "Télécharger",
    upload: "Téléverser",
    next: "Suivant",
    previous: "Précédent",
    close: "Fermer",
    confirm: "Confirmer",
    yes: "Oui",
    no: "Non"
  },

  // Navigation
  navigation: {
    dashboard: "Tableau de bord",
    invoices: "Factures",
    clients: "Clients",
    suppliers: "Fournisseurs",
    reports: "Rapports",
    settings: "Paramètres",
    profile: "Profil",
    logout: "Déconnexion",
    home: "Accueil"
  },

  // Invoice-specific terms
  invoice: {
    title: "Facture",
    number: "Numéro de facture",
    date: "Date de facture",
    dueDate: "Date d'échéance",
    issueDate: "Date d'émission",
    
    // French mandatory fields
    siren: "Numéro SIREN",
    siret: "Numéro SIRET",
    tvaNumber: "Numéro TVA intracommunautaire",
    nafCode: "Code NAF/APE",
    legalForm: "Forme juridique",
    shareCapital: "Capital social",
    rcsNumber: "Numéro RCS",
    rmNumber: "Numéro RM",
    
    // Parties
    vendor: "Fournisseur",
    customer: "Client",
    supplier: "Fournisseur",
    buyer: "Acheteur",
    
    // Amounts (French terminology)
    subtotalHT: "Sous-total HT",
    totalTVA: "Total TVA",
    totalTTC: "Total TTC",
    amountHT: "Montant HT",
    amountTTC: "Montant TTC",
    tvaRate: "Taux de TVA",
    tvaAmount: "Montant TVA",
    
    // Line items
    lineItems: "Articles",
    description: "Description",
    quantity: "Quantité",
    unit: "Unité",
    unitPrice: "Prix unitaire",
    unitPriceHT: "Prix unitaire HT",
    total: "Total",
    totalHT: "Total HT",
    
    // Payment terms
    paymentTerms: "Conditions de paiement",
    paymentDue: "Échéance de paiement",
    latePaymentPenalties: "Pénalités de retard",
    recoveryFees: "Indemnité forfaitaire de recouvrement",
    
    // Status
    status: {
      draft: "Brouillon",
      sent: "Envoyée",
      paid: "Payée",
      overdue: "En retard",
      cancelled: "Annulée",
      processing: "En cours de traitement",
      completed: "Traitée",
      failed: "Échec du traitement"
    }
  },

  // Accounting software
  accountingSoftware: {
    sage: "Sage",
    ebp: "EBP Comptabilité",
    ciel: "Ciel Comptabilité",
    fec: "Format FEC (Administration Fiscale)",
    export: "Exporter vers {software}",
    formats: {
      csv: "CSV Français",
      json: "JSON Structuré",
      sage: "Format Sage PNM",
      ebp: "Format EBP ASCII",
      ciel: "Format Ciel XIMPORT",
      fec: "Fichier des Écritures Comptables (FEC)"
    }
  },

  // Compliance
  compliance: {
    frenchCompliant: "Conforme réglementation française",
    gdprCompliant: "Conforme GDPR",
    validation: "Validation",
    errors: "Erreurs de conformité",
    warnings: "Avertissements",
    mandatoryFields: "Champs obligatoires",
    missingFields: "Champs manquants",
    invalidFormat: "Format invalide",
    
    // French specific compliance
    frenchTaxRates: "Taux de TVA français",
    frenchAddressFormat: "Format d'adresse français",
    sequentialNumbering: "Numérotation séquentielle",
    businessIdentifiers: "Identifiants d'entreprise français"
  },

  // Dashboard
  dashboard: {
    welcome: "Bienvenue",
    recentInvoices: "Factures récentes",
    monthlyStats: "Statistiques mensuelles",
    processingQueue: "File d'attente",
    quickActions: "Actions rapides",
    uploadInvoice: "Téléverser une facture",
    viewAllInvoices: "Voir toutes les factures",
    
    // Statistics
    stats: {
      totalInvoices: "Total des factures",
      processedThisMonth: "Traitées ce mois",
      averageProcessingTime: "Temps de traitement moyen",
      complianceRate: "Taux de conformité",
      savings: "Économies réalisées",
      timesSaved: "Temps économisé"
    }
  },

  // File upload
  fileUpload: {
    dragAndDrop: "Glissez-déposez vos factures ici",
    orClickToSelect: "ou cliquez pour sélectionner",
    supportedFormats: "Formats supportés: PDF, PNG, JPG",
    maxFileSize: "Taille maximale: 10 MB",
    selectFiles: "Sélectionner des fichiers",
    uploading: "Téléversement en cours...",
    processingInvoice: "Traitement de la facture...",
    uploadComplete: "Téléversement terminé",
    uploadFailed: "Échec du téléversement"
  },

  // Errors and messages
  messages: {
    success: {
      invoiceProcessed: "Facture traitée avec succès",
      dataExported: "Données exportées avec succès",
      settingsSaved: "Paramètres sauvegardés",
      invoiceDeleted: "Facture supprimée"
    },
    error: {
      processingFailed: "Échec du traitement de la facture",
      exportFailed: "Échec de l'export",
      invalidFile: "Fichier invalide",
      networkError: "Erreur de connexion",
      unauthorized: "Non autorisé",
      serverError: "Erreur serveur"
    },
    validation: {
      required: "Ce champ est obligatoire",
      invalidEmail: "Adresse email invalide",
      invalidSiren: "Numéro SIREN invalide (9 chiffres)",
      invalidSiret: "Numéro SIRET invalide (14 chiffres)",
      invalidTvaNumber: "Numéro TVA invalide (format: FR + 11 chiffres)",
      invalidPostalCode: "Code postal invalide (5 chiffres)",
      invalidAmount: "Montant invalide"
    }
  },

  // Authentication
  auth: {
    signIn: "Connexion",
    signUp: "Inscription",
    signOut: "Déconnexion",
    email: "Adresse email",
    password: "Mot de passe",
    confirmPassword: "Confirmer le mot de passe",
    forgotPassword: "Mot de passe oublié ?",
    rememberMe: "Se souvenir de moi",
    createAccount: "Créer un compte",
    alreadyHaveAccount: "Vous avez déjà un compte ?",
    dontHaveAccount: "Vous n'avez pas de compte ?",
    
    // Account types
    accountType: "Type de compte",
    expertComptable: "Expert-comptable",
    comptable: "Comptable",
    entreprise: "Entreprise",
    
    // Firm information
    firmName: "Nom du cabinet",
    firmSize: "Taille du cabinet",
    clientCount: "Nombre de clients",
    location: "Localisation"
  },

  // Settings
  settings: {
    general: "Général",
    account: "Compte",
    billing: "Facturation",
    integrations: "Intégrations",
    preferences: "Préférences",
    notifications: "Notifications",
    
    // Preferences
    language: "Langue",
    dateFormat: "Format de date",
    numberFormat: "Format des nombres",
    currency: "Devise",
    timezone: "Fuseau horaire",
    
    // French specific settings
    defaultTvaRate: "Taux de TVA par défaut",
    accountingYear: "Exercice comptable",
    preferredExportFormat: "Format d'export préféré",
    complianceLevel: "Niveau de conformité"
  }
};

/**
 * French number formatting utilities
 */
export const frenchFormatting = {
  /**
   * Format number with French locale (comma as decimal separator)
   */
  formatNumber: (num: number, decimals: number = 2): string => {
    return new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    }).format(num);
  },

  /**
   * Format currency in euros with French formatting
   */
  formatCurrency: (amount: number): string => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  },

  /**
   * Format date with French locale
   */
  formatDate: (date: Date | string): string => {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat('fr-FR').format(dateObj);
  },

  /**
   * Format date for French invoices (DD/MM/YYYY)
   */
  formatInvoiceDate: (date: Date | string): string => {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return dateObj.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  },

  /**
   * Parse French number format (comma as decimal separator)
   */
  parseFrenchNumber: (str: string): number => {
    const cleaned = str.replace(/\s/g, '').replace(',', '.');
    return parseFloat(cleaned) || 0;
  }
};

/**
 * French validation patterns
 */
export const frenchValidation = {
  siren: /^\d{9}$/,
  siret: /^\d{14}$/,
  tvaNumber: /^FR\d{11}$/,
  nafCode: /^\d{4}[A-Z]$/,
  postalCode: /^\d{5}$/,
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
};

/**
 * French business legal forms
 */
export const frenchLegalForms = [
  'SARL',
  'SAS',
  'SASU',
  'EURL',
  'SA',
  'SNC',
  'SCP',
  'SEL',
  'SELARL',
  'SELAFA',
  'SELCA',
  'SELAS',
  'SEM',
  'EPIC',
  'EI',
  'EIRL',
  'Micro-entreprise',
  'Auto-entrepreneur'
];

/**
 * French VAT rates
 */
export const frenchVATRates = [
  { rate: 20.0, label: "20% (Taux normal)" },
  { rate: 10.0, label: "10% (Taux réduit)" },
  { rate: 5.5, label: "5,5% (Taux réduit spécial)" },
  { rate: 2.1, label: "2,1% (Taux super réduit)" },
  { rate: 0.0, label: "0% (Exonéré)" }
];

/**
 * Utility function to get translation
 */
export const t = (key: string): string => {
  const keys = key.split('.');
  let value: any = frenchTranslations;
  
  for (const k of keys) {
    value = value?.[k];
    if (value === undefined) {
      console.warn(`Translation key not found: ${key}`);
      return key;
    }
  }
  
  return value;
};

export default frenchTranslations;
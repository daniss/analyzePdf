/**
 * React hook for French business validation
 * Provides validation and formatting for SIREN, SIRET, TVA, and other French business data
 */

import { useState, useCallback } from 'react'
import { 
  validateSIREN, 
  validateSIRET, 
  validateTVA, 
  validatePostalCode,
  formatSIREN,
  formatSIRET,
  formatTVA,
  getValidationError 
} from '../french-validation'

export interface ValidationResult {
  isValid: boolean
  error?: string
  formatted?: string
}

export interface FrenchValidationHook {
  validateField: (field: string, value: string) => ValidationResult
  validateTVARate: (rate: number) => ValidationResult
  validateInvoiceAmount: (amount: number, vatAmount: number, vatRate: number) => ValidationResult
  formatField: (field: string, value: string) => string
  getTVACalculation: (amountHT: number, vatRate: number) => { amountTTC: number, vatAmount: number }
}

/**
 * French TVA rates as of 2024
 */
export const FRENCH_TVA_RATES = {
  STANDARD: 20.0,     // Taux normal
  REDUCED_1: 10.0,    // Taux réduit (restauration, transport)
  REDUCED_2: 5.5,     // Taux réduit (alimentaire, livres)
  SUPER_REDUCED: 2.1, // Taux super réduit (médicaments, presse)
  EXEMPT: 0.0         // Exonéré
} as const

export function useFrenchValidation(): FrenchValidationHook {
  const validateField = useCallback((field: string, value: string): ValidationResult => {
    if (!value || value.trim() === '') {
      return { isValid: true } // Empty values are considered valid (not required)
    }

    const error = getValidationError(field, value)
    if (error) {
      return { isValid: false, error }
    }

    // Format the value if validation passes
    const formatted = formatField(field, value)
    return { isValid: true, formatted }
  }, [])

  const validateTVARate = useCallback((rate: number): ValidationResult => {
    if (rate < 0 || rate > 100) {
      return { isValid: false, error: 'Le taux de TVA doit être entre 0% et 100%' }
    }

    const validRates = Object.values(FRENCH_TVA_RATES)
    if (!validRates.includes(rate)) {
      return { 
        isValid: false, 
        error: `Taux de TVA non standard. Taux français valides: ${validRates.join('%, ')}%` 
      }
    }

    return { isValid: true }
  }, [])

  const validateInvoiceAmount = useCallback((amountHT: number, vatAmount: number, vatRate: number): ValidationResult => {
    if (amountHT <= 0) {
      return { isValid: false, error: 'Le montant HT doit être positif' }
    }

    if (vatRate === 0 && vatAmount !== 0) {
      return { isValid: false, error: 'Montant TVA doit être 0 pour un taux de 0%' }
    }

    if (vatRate > 0) {
      const expectedVatAmount = Math.round((amountHT * vatRate / 100) * 100) / 100
      const tolerance = 0.02 // 2 centimes de tolerance pour les arrondis
      
      if (Math.abs(vatAmount - expectedVatAmount) > tolerance) {
        return { 
          isValid: false, 
          error: `Montant TVA incorrect. Attendu: ${expectedVatAmount.toFixed(2)}€ (calculé: ${amountHT}€ × ${vatRate}%)` 
        }
      }
    }

    return { isValid: true }
  }, [])

  const formatField = useCallback((field: string, value: string): string => {
    switch (field) {
      case 'siren':
        return formatSIREN(value)
      case 'siret':
        return formatSIRET(value)
      case 'tva':
      case 'tva_number':
        return formatTVA(value)
      default:
        return value
    }
  }, [])

  const getTVACalculation = useCallback((amountHT: number, vatRate: number) => {
    const vatAmount = Math.round((amountHT * vatRate / 100) * 100) / 100
    const amountTTC = Math.round((amountHT + vatAmount) * 100) / 100
    return { amountTTC, vatAmount }
  }, [])

  return {
    validateField,
    validateTVARate,
    validateInvoiceAmount,
    formatField,
    getTVACalculation
  }
}

/**
 * Helper function to get French business field label
 */
export function getFrenchFieldLabel(field: string): string {
  const labels: Record<string, string> = {
    siren: 'N° SIREN',
    siret: 'N° SIRET',
    tva: 'N° TVA Intracommunautaire',
    tva_number: 'N° TVA',
    postal_code: 'Code Postal',
    amount_ht: 'Montant HT',
    amount_ttc: 'Montant TTC',
    tva_amount: 'Montant TVA',
    tva_rate: 'Taux TVA'
  }
  return labels[field] || field
}

/**
 * Helper to detect if a string contains a French business identifier
 */
export function detectFrenchBusinessNumber(text: string): { type: string, value: string } | null {
  // SIRET pattern (14 digits)
  const siretMatch = text.match(/\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b/)
  if (siretMatch && validateSIRET(siretMatch[0])) {
    return { type: 'siret', value: siretMatch[0] }
  }

  // SIREN pattern (9 digits)
  const sirenMatch = text.match(/\b\d{3}\s?\d{3}\s?\d{3}\b/)
  if (sirenMatch && validateSIREN(sirenMatch[0])) {
    return { type: 'siren', value: sirenMatch[0] }
  }

  // TVA pattern (FR + 2 chars + 9 digits)
  const tvaMatch = text.match(/\bFR\s?[A-Z0-9]{2}\s?\d{3}\s?\d{3}\s?\d{3}\b/i)
  if (tvaMatch && validateTVA(tvaMatch[0])) {
    return { type: 'tva', value: tvaMatch[0] }
  }

  return null
}
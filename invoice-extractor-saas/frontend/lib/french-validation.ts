/**
 * French business validation utilities
 * Validates SIREN, SIRET, and TVA numbers according to French standards
 */

/**
 * Validate French SIREN number (9 digits with Luhn algorithm)
 */
export function validateSIREN(siren: string): boolean {
  if (!siren) return false
  
  // Remove spaces and non-numeric characters
  const cleanSiren = siren.replace(/\s+/g, '').replace(/\D/g, '')
  
  // Must be exactly 9 digits
  if (cleanSiren.length !== 9) return false
  
  // Apply Luhn algorithm for SIREN validation
  let sum = 0
  for (let i = 0; i < 9; i++) {
    let digit = parseInt(cleanSiren[i])
    
    // Double every second digit from right to left
    if ((9 - i) % 2 === 0) {
      digit *= 2
      if (digit > 9) {
        digit = Math.floor(digit / 10) + (digit % 10)
      }
    }
    sum += digit
  }
  
  return sum % 10 === 0
}

/**
 * Validate French SIRET number (14 digits: SIREN + 5 digits)
 */
export function validateSIRET(siret: string): boolean {
  if (!siret) return false
  
  // Remove spaces and non-numeric characters
  const cleanSiret = siret.replace(/\s+/g, '').replace(/\D/g, '')
  
  // Must be exactly 14 digits
  if (cleanSiret.length !== 14) return false
  
  // Extract SIREN (first 9 digits) and validate it
  const siren = cleanSiret.substring(0, 9)
  if (!validateSIREN(siren)) return false
  
  // Validate SIRET with Luhn algorithm
  let sum = 0
  for (let i = 0; i < 14; i++) {
    let digit = parseInt(cleanSiret[i])
    
    // Double every second digit from right to left
    if ((14 - i) % 2 === 0) {
      digit *= 2
      if (digit > 9) {
        digit = Math.floor(digit / 10) + (digit % 10)
      }
    }
    sum += digit
  }
  
  return sum % 10 === 0
}

/**
 * Validate French TVA number (FR + 11 digits)
 */
export function validateTVA(tva: string): boolean {
  if (!tva) return false
  
  // Remove spaces and convert to uppercase
  const cleanTva = tva.replace(/\s+/g, '').toUpperCase()
  
  // Must start with FR followed by 11 characters
  if (!cleanTva.startsWith('FR') || cleanTva.length !== 13) return false
  
  const tvaNumber = cleanTva.substring(2)
  
  // First two characters can be digits or letters, followed by 9 digits (SIREN)
  const prefix = tvaNumber.substring(0, 2)
  const siren = tvaNumber.substring(2)
  
  // Validate SIREN part
  if (!validateSIREN(siren)) return false
  
  // If prefix is numeric, validate the checksum
  if (/^\d{2}$/.test(prefix)) {
    const checksum = parseInt(prefix)
    const sirenNumber = parseInt(siren)
    const calculatedChecksum = (12 + 3 * (sirenNumber % 97)) % 97
    return checksum === calculatedChecksum
  }
  
  // If prefix contains letters, it's a special format (valid but no checksum verification)
  return /^[A-Z0-9]{2}$/.test(prefix)
}

/**
 * Format SIREN number with spaces for display
 */
export function formatSIREN(siren: string): string {
  const cleanSiren = siren.replace(/\s+/g, '').replace(/\D/g, '')
  if (cleanSiren.length === 9) {
    return `${cleanSiren.substring(0, 3)} ${cleanSiren.substring(3, 6)} ${cleanSiren.substring(6, 9)}`
  }
  return siren
}

/**
 * Format SIRET number with spaces for display
 */
export function formatSIRET(siret: string): string {
  const cleanSiret = siret.replace(/\s+/g, '').replace(/\D/g, '')
  if (cleanSiret.length === 14) {
    return `${cleanSiret.substring(0, 3)} ${cleanSiret.substring(3, 6)} ${cleanSiret.substring(6, 9)} ${cleanSiret.substring(9, 14)}`
  }
  return siret
}

/**
 * Format TVA number for display
 */
export function formatTVA(tva: string): string {
  const cleanTva = tva.replace(/\s+/g, '').toUpperCase()
  if (cleanTva.startsWith('FR') && cleanTva.length === 13) {
    const prefix = cleanTva.substring(2, 4)
    const siren = cleanTva.substring(4)
    return `FR ${prefix} ${formatSIREN(siren)}`
  }
  return tva
}

/**
 * Validate French postal code (5 digits)
 */
export function validatePostalCode(postalCode: string): boolean {
  if (!postalCode) return false
  const clean = postalCode.replace(/\s+/g, '')
  return /^\d{5}$/.test(clean)
}

/**
 * Get validation error message in French
 */
export function getValidationError(field: string, value: string): string | null {
  switch (field) {
    case 'siren':
      if (!validateSIREN(value)) {
        return 'Numéro SIREN invalide (9 chiffres requis avec algorithme de Luhn)'
      }
      break
    case 'siret':
      if (!validateSIRET(value)) {
        return 'Numéro SIRET invalide (14 chiffres requis avec SIREN valide)'
      }
      break
    case 'tva':
      if (!validateTVA(value)) {
        return 'Numéro de TVA invalide (format: FR + 2 caractères + 9 chiffres SIREN)'
      }
      break
    case 'postal_code':
      if (!validatePostalCode(value)) {
        return 'Code postal invalide (5 chiffres requis)'
      }
      break
  }
  return null
}
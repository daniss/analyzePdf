"""
French Invoice Parser

Specialized parser for French invoice documents with enhanced pattern recognition
for French business information, TVA rates, and regulatory compliance.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from decimal import Decimal

from schemas.invoice import InvoiceData, FrenchBusinessInfo, FrenchTVABreakdown, LineItem


class FrenchInvoiceParser:
    """Specialized parser for French invoices with enhanced pattern matching"""
    
    # French TVA rates and their common representations
    FRENCH_TVA_PATTERNS = {
        '20': [r'20\.?0?\s*%', r'TVA\s*20', r'taux\s*normal', r'20,0?\s*%'],
        '10': [r'10\.?0?\s*%', r'TVA\s*10', r'taux\s*réduit', r'10,0?\s*%'],
        '5.5': [r'5\.?5\s*%', r'TVA\s*5[\.,]5', r'5,5\s*%'],
        '2.1': [r'2\.?1\s*%', r'TVA\s*2[\.,]1', r'2,1\s*%'],
        '0': [r'0\.?0?\s*%', r'TVA\s*0', r'exonéré', r'non\s*applicable']
    }
    
    # SIREN/SIRET patterns
    SIREN_PATTERNS = [
        r'SIREN\s*:?\s*(\d{3}\s*\d{3}\s*\d{3})',
        r'SIREN\s*:?\s*(\d{9})',
        r'(\d{3}\s*\d{3}\s*\d{3})',  # Generic 9-digit pattern
        r'(\d{9})'
    ]
    
    SIRET_PATTERNS = [
        r'SIRET\s*:?\s*(\d{3}\s*\d{3}\s*\d{3}\s*\d{5})',
        r'SIRET\s*:?\s*(\d{14})',
        r'(\d{3}\s*\d{3}\s*\d{3}\s*\d{5})',  # Generic 14-digit pattern
        r'(\d{14})'
    ]
    
    # French TVA number patterns
    TVA_NUMBER_PATTERNS = [
        r'TVA\s*:?\s*(FR\s*\d{11})',
        r'N°\s*TVA\s*:?\s*(FR\s*\d{11})',
        r'Numéro\s*TVA\s*:?\s*(FR\s*\d{11})',
        r'(FR\s*\d{2}\s*\d{9})',
        r'(FR\d{11})'
    ]
    
    # NAF/APE code patterns
    NAF_PATTERNS = [
        r'NAF\s*:?\s*(\d{4}[A-Z])',
        r'APE\s*:?\s*(\d{4}[A-Z])',
        r'Code\s*NAF\s*:?\s*(\d{4}[A-Z])',
        r'(\d{4}[A-Z])'  # Generic pattern
    ]
    
    # French legal forms
    LEGAL_FORM_PATTERNS = [
        r'\b(SARL|SAS|SASU|EURL|SA|SNC|SCP|SEL|SELARL|SELAFA|SELCA|SELAS|SEM|EPIC|EI|EIRL)\b',
        r'\b(Micro[-\s]?entreprise|Auto[-\s]?entrepreneur)\b'
    ]
    
    # French monetary patterns (with comma as decimal separator)
    FRENCH_MONEY_PATTERNS = [
        r'(\d{1,3}(?:\s\d{3})*(?:,\d{2})?)\s*€',  # 1 234,56 €
        r'(\d+(?:,\d{2})?)\s*€',  # 123,45 €
        r'€\s*(\d{1,3}(?:\s\d{3})*(?:,\d{2})?)',  # € 1 234,56
        r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*EUR',  # 1.234,56 EUR
    ]
    
    def __init__(self):
        pass
    
    def enhance_extracted_data(self, invoice_data: InvoiceData, raw_text: str) -> InvoiceData:
        """
        Enhance AI-extracted data with French-specific parsing improvements
        
        Args:
            invoice_data: Initial extraction from AI processing
            raw_text: Raw text from OCR or AI processing
            
        Returns:
            Enhanced InvoiceData with improved French parsing
        """
        
        # Extract missing SIREN/SIRET numbers
        if invoice_data.vendor and not invoice_data.vendor.siren_number:
            siren = self._extract_siren(raw_text)
            if siren:
                invoice_data.vendor.siren_number = siren
        
        if invoice_data.vendor and not invoice_data.vendor.siret_number:
            siret = self._extract_siret(raw_text)
            if siret:
                invoice_data.vendor.siret_number = siret
        
        # Extract missing TVA number
        if invoice_data.vendor and not invoice_data.vendor.tva_number:
            tva_number = self._extract_tva_number(raw_text)
            if tva_number:
                invoice_data.vendor.tva_number = tva_number
        
        # Extract missing NAF code
        if invoice_data.vendor and not invoice_data.vendor.naf_code:
            naf_code = self._extract_naf_code(raw_text)
            if naf_code:
                invoice_data.vendor.naf_code = naf_code
        
        # Extract legal form if missing
        if invoice_data.vendor and not invoice_data.vendor.legal_form:
            legal_form = self._extract_legal_form(raw_text)
            if legal_form:
                invoice_data.vendor.legal_form = legal_form
        
        # Enhance TVA breakdown if incomplete
        if not invoice_data.tva_breakdown or len(invoice_data.tva_breakdown) == 0:
            tva_breakdown = self._extract_tva_breakdown(raw_text)
            if tva_breakdown:
                invoice_data.tva_breakdown = tva_breakdown
        
        # Extract French-specific payment clauses
        if not invoice_data.late_payment_penalties:
            penalties_clause = self._extract_late_payment_clause(raw_text)
            if penalties_clause:
                invoice_data.late_payment_penalties = penalties_clause
        
        if not invoice_data.recovery_fees:
            recovery_clause = self._extract_recovery_fees_clause(raw_text)
            if recovery_clause:
                invoice_data.recovery_fees = recovery_clause
        
        # Validate and correct French number formats
        invoice_data = self._normalize_french_numbers(invoice_data)
        
        return invoice_data
    
    def _extract_siren(self, text: str) -> Optional[str]:
        """Extract SIREN number from text"""
        for pattern in self.SIREN_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean the match (remove spaces)
                siren = re.sub(r'\s+', '', match)
                if len(siren) == 9 and siren.isdigit():
                    return siren
        return None
    
    def _extract_siret(self, text: str) -> Optional[str]:
        """Extract SIRET number from text"""
        for pattern in self.SIRET_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean the match (remove spaces)
                siret = re.sub(r'\s+', '', match)
                if len(siret) == 14 and siret.isdigit():
                    return siret
        return None
    
    def _extract_tva_number(self, text: str) -> Optional[str]:
        """Extract French TVA number from text"""
        for pattern in self.TVA_NUMBER_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean the match (remove spaces, uppercase)
                tva_number = re.sub(r'\s+', '', match).upper()
                if re.match(r'^FR\d{11}$', tva_number):
                    return tva_number
        return None
    
    def _extract_naf_code(self, text: str) -> Optional[str]:
        """Extract NAF/APE code from text"""
        for pattern in self.NAF_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                naf_code = match.upper()
                if re.match(r'^\d{4}[A-Z]$', naf_code):
                    return naf_code
        return None
    
    def _extract_legal_form(self, text: str) -> Optional[str]:
        """Extract legal form from text"""
        for pattern in self.LEGAL_FORM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].upper()
        return None
    
    def _extract_tva_breakdown(self, text: str) -> List[FrenchTVABreakdown]:
        """Extract TVA breakdown from text"""
        tva_breakdown = []
        
        # Look for TVA sections in the text
        tva_sections = re.findall(
            r'TVA\s*(\d{1,2}[,.]?\d*)\s*%?\s*:?\s*(\d{1,6}[,.]?\d{0,2})\s*€?.*?(\d{1,6}[,.]?\d{0,2})\s*€?',
            text,
            re.IGNORECASE
        )
        
        for rate_str, base_str, tva_str in tva_sections:
            try:
                # Convert French number format to float
                rate = float(rate_str.replace(',', '.'))
                base_amount = self._parse_french_number(base_str)
                tva_amount = self._parse_french_number(tva_str)
                
                if rate in [0.0, 2.1, 5.5, 10.0, 20.0]:
                    tva_breakdown.append(FrenchTVABreakdown(
                        rate=rate,
                        taxable_amount=base_amount,
                        tva_amount=tva_amount
                    ))
            except (ValueError, TypeError):
                continue
        
        return tva_breakdown
    
    def _extract_late_payment_clause(self, text: str) -> Optional[str]:
        """Extract late payment penalty clause"""
        patterns = [
            r'(En cas de retard de paiement.*?taux d\'intérêt légal.*?)',
            r'(Pénalité.*?retard.*?paiement.*?)',
            r'(Conformément.*?L441-6.*?Code de commerce.*?)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                return matches[0].strip()
        
        return None
    
    def _extract_recovery_fees_clause(self, text: str) -> Optional[str]:
        """Extract recovery fees clause (€40 mandatory fee)"""
        patterns = [
            r'(.*?indemnité.*?40.*?euros?.*?recouvrement.*?)',
            r'(.*?40.*?€.*?frais.*?recouvrement.*?)',
            r'(.*?quarante.*?euros?.*?recouvrement.*?)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
            if matches:
                return matches[0].strip()
        
        return None
    
    def _parse_french_number(self, number_str: str) -> float:
        """Parse French number format (comma as decimal separator)"""
        if not number_str:
            return 0.0
        
        # Remove currency symbols and spaces
        cleaned = re.sub(r'[€$£\s]', '', number_str.strip())
        
        # Handle French format: 1 234,56 or 1.234,56
        if ',' in cleaned:
            # Split on comma (decimal separator)
            parts = cleaned.split(',')
            if len(parts) == 2:
                integer_part = re.sub(r'[.\s]', '', parts[0])  # Remove thousand separators
                decimal_part = parts[1][:2]  # Max 2 decimal places
                return float(f"{integer_part}.{decimal_part}")
        
        # Handle standard format without decimals
        cleaned = re.sub(r'[.\s]', '', cleaned)
        return float(cleaned) if cleaned.isdigit() else 0.0
    
    def _normalize_french_numbers(self, invoice_data: InvoiceData) -> InvoiceData:
        """Normalize number formats in invoice data"""
        
        # This would typically be done during parsing, but we ensure consistency here
        if invoice_data.currency != 'EUR':
            invoice_data.currency = 'EUR'
        
        # Ensure line items have proper TVA rates
        for item in invoice_data.line_items:
            if item.tva_rate and item.tva_rate not in [0.0, 2.1, 5.5, 10.0, 20.0]:
                # Try to match to closest valid French rate
                if 19 <= item.tva_rate <= 21:
                    item.tva_rate = 20.0
                elif 9 <= item.tva_rate <= 11:
                    item.tva_rate = 10.0
                elif 5 <= item.tva_rate <= 6:
                    item.tva_rate = 5.5
                elif 2 <= item.tva_rate <= 3:
                    item.tva_rate = 2.1
                elif item.tva_rate <= 1:
                    item.tva_rate = 0.0
        
        return invoice_data
    
    def extract_french_addresses(self, text: str) -> Dict[str, Dict[str, str]]:
        """Extract French addresses with postal codes"""
        addresses = {}
        
        # French postal code pattern (5 digits)
        postal_code_pattern = r'\b(\d{5})\b'
        postal_codes = re.findall(postal_code_pattern, text)
        
        # Extract addresses around postal codes
        for postal_code in postal_codes[:2]:  # Usually vendor and customer
            # Look for address context around postal code
            pattern = rf'(.{{0,100}}{re.escape(postal_code)}.{{0,50}})'
            matches = re.findall(pattern, text, re.MULTILINE)
            
            if matches:
                address_text = matches[0].strip()
                # This is a simplified extraction - in practice, you'd want more sophisticated parsing
                if len(addresses) == 0:
                    addresses['vendor'] = {
                        'address': address_text,
                        'postal_code': postal_code
                    }
                else:
                    addresses['customer'] = {
                        'address': address_text,
                        'postal_code': postal_code
                    }
        
        return addresses
    
    def validate_french_invoice_format(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """Validate French invoice format requirements"""
        from core.validation.french_validator import validate_french_invoice
        
        return validate_french_invoice(invoice_data)


def enhance_french_invoice_extraction(invoice_data: InvoiceData, raw_text: str = "") -> InvoiceData:
    """
    Convenience function to enhance invoice extraction with French parsing
    
    Args:
        invoice_data: Initial extracted data
        raw_text: Raw text for pattern matching enhancement
        
    Returns:
        Enhanced InvoiceData
    """
    parser = FrenchInvoiceParser()
    return parser.enhance_extracted_data(invoice_data, raw_text)
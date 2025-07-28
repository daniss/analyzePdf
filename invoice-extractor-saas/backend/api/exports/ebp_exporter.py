"""
EBP Accounting Software Export Module

Exports invoice data to EBP ASCII format for seamless integration with 
EBP accounting software used by French experts-comptables.
"""

import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

from schemas.invoice import InvoiceData, FrenchBusinessInfo


class EBPExporter:
    """Export invoice data to EBP ASCII format"""
    
    def __init__(self):
        self.format_name = "EBP ASCII"
        self.file_extension = ".txt"
        self.line_length = 256  # Fixed line length for EBP format
    
    def export_invoice(self, invoice: InvoiceData) -> str:
        """
        Export a single invoice to EBP ASCII format
        
        Args:
            invoice: Invoice data to export
            
        Returns:
            EBP ASCII formatted string
        """
        lines = []
        
        # Format: Fixed-width fields, space-padded
        # Structure: Type|Journal|Date|CompteGeneral|CompteAuxiliaire|Libelle|Debit|Credit|...
        
        # Vendor entry (credit)
        if invoice.vendor:
            vendor_line = self._format_vendor_entry(invoice)
            lines.append(vendor_line)
        
        # Customer entry (debit) - if different from vendor
        if invoice.customer and invoice.customer != invoice.vendor:
            customer_line = self._format_customer_entry(invoice)
            lines.append(customer_line)
        
        # Line items entries
        for i, item in enumerate(invoice.line_items):
            item_line = self._format_line_item_entry(item, invoice, i + 1)
            lines.append(item_line)
        
        # TVA entries
        for tva_item in invoice.tva_breakdown:
            tva_line = self._format_tva_entry(tva_item, invoice)
            lines.append(tva_line)
        
        return '\\n'.join(lines)
    
    def export_batch(self, invoices: List[InvoiceData]) -> str:
        """
        Export multiple invoices to EBP ASCII format
        
        Args:
            invoices: List of invoice data to export
            
        Returns:
            EBP ASCII formatted string for all invoices
        """
        all_lines = []
        
        # EBP batch header
        header = self._format_batch_header(len(invoices))
        all_lines.append(header)
        
        # Export each invoice
        for invoice in invoices:
            invoice_lines = self.export_invoice(invoice).split('\\n')
            all_lines.extend(invoice_lines)
        
        return '\\n'.join(all_lines)
    
    def _format_vendor_entry(self, invoice: InvoiceData) -> str:
        """Format vendor entry for EBP"""
        
        # EBP fixed-width format
        fields = {
            'type': 'V',  # Vendor entry
            'journal': 'ACH',  # Purchase journal
            'date': self._format_date_ebp(invoice.date),
            'compte_general': '401000',  # General account for suppliers
            'compte_auxiliaire': self._get_vendor_account(invoice.vendor),
            'libelle': self._truncate(f"Facture {invoice.invoice_number}", 30),
            'debit': self._format_amount_ebp(0),
            'credit': self._format_amount_ebp(invoice.total_ttc or invoice.total or 0),
            'tva_code': self._get_main_tva_code(invoice),
            'piece': invoice.invoice_number or '',
            'echeance': self._format_date_ebp(invoice.due_date) if invoice.due_date else self._format_date_ebp(invoice.date),
            'siren': invoice.vendor.siren_number if invoice.vendor else '',
            'siret': invoice.vendor.siret_number if invoice.vendor else '',
            'tva_number': invoice.vendor.tva_number if invoice.vendor else ''
        }
        
        return self._format_fixed_line(fields)
    
    def _format_customer_entry(self, invoice: InvoiceData) -> str:
        """Format customer entry for EBP (if needed for some transaction types)"""
        
        fields = {
            'type': 'C',  # Customer entry
            'journal': 'VTE',  # Sales journal
            'date': self._format_date_ebp(invoice.date),
            'compte_general': '411000',  # General account for customers
            'compte_auxiliaire': self._get_customer_account(invoice.customer),
            'libelle': self._truncate(f"Facture {invoice.invoice_number}", 30),
            'debit': self._format_amount_ebp(invoice.total_ttc or invoice.total or 0),
            'credit': self._format_amount_ebp(0),
            'tva_code': '',
            'piece': invoice.invoice_number or '',
            'echeance': self._format_date_ebp(invoice.due_date) if invoice.due_date else self._format_date_ebp(invoice.date),
            'siren': invoice.customer.siren_number if invoice.customer else '',
            'siret': invoice.customer.siret_number if invoice.customer else ''
        }
        
        return self._format_fixed_line(fields)
    
    def _format_line_item_entry(self, item, invoice: InvoiceData, line_number: int) -> str:
        """Format line item entry for EBP"""
        
        # Determine account based on item description (simplified)
        account_code = self._determine_account_code(item.description)
        
        fields = {
            'type': 'L',  # Line item
            'journal': 'ACH',
            'date': self._format_date_ebp(invoice.date),
            'compte_general': account_code,
            'compte_auxiliaire': '',
            'libelle': self._truncate(item.description, 30),
            'debit': self._format_amount_ebp(item.total),
            'credit': self._format_amount_ebp(0),
            'tva_code': self._get_tva_code(item.tva_rate or 20.0),
            'piece': invoice.invoice_number or '',
            'quantite': str(item.quantity),
            'unite': item.unit or '',
            'prix_unitaire': self._format_amount_ebp(item.unit_price)
        }
        
        return self._format_fixed_line(fields)
    
    def _format_tva_entry(self, tva_item, invoice: InvoiceData) -> str:
        """Format TVA entry for EBP"""
        
        tva_account = self._get_tva_account(tva_item.rate)
        
        fields = {
            'type': 'T',  # TVA entry
            'journal': 'ACH',
            'date': self._format_date_ebp(invoice.date),
            'compte_general': tva_account,
            'compte_auxiliaire': '',
            'libelle': self._truncate(f"TVA {tva_item.rate}%", 30),
            'debit': self._format_amount_ebp(tva_item.tva_amount),
            'credit': self._format_amount_ebp(0),
            'tva_code': self._get_tva_code(tva_item.rate),
            'piece': invoice.invoice_number or '',
            'taux_tva': str(tva_item.rate),
            'base_tva': self._format_amount_ebp(tva_item.taxable_amount)
        }
        
        return self._format_fixed_line(fields)
    
    def _format_batch_header(self, count: int) -> str:
        """Format batch header for EBP"""
        
        fields = {
            'type': 'H',  # Header
            'version': 'EBP_V3',
            'date_creation': datetime.now().strftime('%d/%m/%Y'),
            'nb_ecritures': str(count),
            'origine': 'INVOICE_AI',
            'format': 'ASCII_FIXE'
        }
        
        return self._format_fixed_line(fields)
    
    def _format_fixed_line(self, fields: Dict[str, str]) -> str:
        """Format a line with fixed-width fields for EBP"""
        
        # EBP field definitions (position and width)
        field_specs = {
            'type': (1, 1),
            'journal': (2, 3),
            'date': (5, 8),
            'compte_general': (13, 8),
            'compte_auxiliaire': (21, 8),
            'libelle': (29, 30),
            'debit': (59, 15),
            'credit': (74, 15),
            'tva_code': (89, 3),
            'piece': (92, 20),
            'echeance': (112, 8),
            'siren': (120, 9),
            'siret': (129, 14),
            'tva_number': (143, 13),
            'quantite': (156, 10),
            'unite': (166, 5),
            'prix_unitaire': (171, 15),
            'taux_tva': (186, 5),
            'base_tva': (191, 15),
            'version': (2, 10),
            'date_creation': (12, 8),
            'nb_ecritures': (20, 10),
            'origine': (30, 20),
            'format': (50, 20)
        }
        
        # Create line buffer
        line = [' '] * self.line_length
        
        # Fill fields
        for field_name, value in fields.items():
            if field_name in field_specs and value:
                start_pos, width = field_specs[field_name]
                # Adjust for 0-based indexing
                start_pos -= 1
                
                # Truncate or pad value
                formatted_value = str(value)[:width].ljust(width)
                
                # Insert into line buffer
                for i, char in enumerate(formatted_value):
                    if start_pos + i < len(line):
                        line[start_pos + i] = char
        
        return ''.join(line).rstrip()
    
    def _format_date_ebp(self, date_input) -> str:
        """Format date for EBP (DDMMYYYY)"""
        
        if not date_input:
            return datetime.now().strftime('%d%m%Y')
        
        if isinstance(date_input, str):
            try:
                # Try to parse ISO format
                date_obj = datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try French format
                    date_obj = datetime.strptime(date_input, '%d/%m/%Y').date()
                except ValueError:
                    return datetime.now().strftime('%d%m%Y')
        else:
            date_obj = date_input
        
        return date_obj.strftime('%d%m%Y')
    
    def _format_amount_ebp(self, amount) -> str:
        """Format amount for EBP (15 chars, right-aligned, 2 decimals)"""
        
        if amount is None:
            amount = 0
        
        # Convert to cents (EBP often uses cents for precision)
        cents = int(round(float(amount) * 100))
        
        # Format as string with sign
        amount_str = f"{cents:+013d}"  # 13 digits + sign = 14 chars
        
        return amount_str.rjust(15)
    
    def _get_vendor_account(self, vendor: Optional[FrenchBusinessInfo]) -> str:
        """Get vendor account code"""
        
        if not vendor or not vendor.siren_number:
            return 'FOUR001'
        
        # Use last 6 digits of SIREN for account code
        return f"F{vendor.siren_number[-6:]}"
    
    def _get_customer_account(self, customer: Optional[FrenchBusinessInfo]) -> str:
        """Get customer account code"""
        
        if not customer or not customer.siren_number:
            return 'CLIE001'
        
        # Use last 6 digits of SIREN for account code
        return f"C{customer.siren_number[-6:]}"
    
    def _get_tva_code(self, rate: float) -> str:
        """Get TVA code for EBP"""
        
        tva_codes = {
            20.0: 'T20',
            10.0: 'T10',
            5.5: 'T55',
            2.1: 'T21',
            0.0: 'T00'
        }
        
        return tva_codes.get(rate, 'T20')
    
    def _get_tva_account(self, rate: float) -> str:
        """Get TVA account code"""
        
        tva_accounts = {
            20.0: '445662',  # TVA déductible 20%
            10.0: '445661',  # TVA déductible 10%
            5.5: '445663',   # TVA déductible 5.5%
            2.1: '445664',   # TVA déductible 2.1%
            0.0: '445660'    # TVA déductible 0%
        }
        
        return tva_accounts.get(rate, '445662')
    
    def _get_main_tva_code(self, invoice: InvoiceData) -> str:
        """Get main TVA code for invoice"""
        
        if invoice.tva_breakdown:
            # Use the TVA rate with highest amount
            main_tva = max(invoice.tva_breakdown, key=lambda x: x.tva_amount)
            return self._get_tva_code(main_tva.rate)
        
        return 'T20'  # Default to 20%
    
    def _determine_account_code(self, description: str) -> str:
        """Determine account code based on item description (simplified)"""
        
        # This is a simplified mapping - in practice, you'd want more sophisticated categorization
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['service', 'prestation', 'consultation']):
            return '606000'  # Services
        elif any(word in description_lower for word in ['matériel', 'équipement', 'machine']):
            return '606100'  # Equipment
        elif any(word in description_lower for word in ['fourniture', 'matière', 'produit']):
            return '607000'  # Supplies
        else:
            return '607000'  # Default to supplies
    
    def _truncate(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length"""
        
        if not text:
            return ''
        
        return text[:max_length]
    
    def get_export_info(self) -> Dict[str, Any]:
        """Get information about this export format"""
        
        return {
            'name': 'EBP ASCII',
            'description': 'Format d\'export ASCII pour logiciels EBP Comptabilité',
            'file_extension': '.txt',
            'mime_type': 'text/plain',
            'software_compatibility': [
                'EBP Comptabilité Open Line',
                'EBP Comptabilité Pro',
                'EBP Gestion Commerciale',
                'EBP Bâtiment',
                'EBP Auto-Entrepreneur'
            ],
            'features': [
                'Format fixe ASCII',
                'Import direct dans EBP',
                'Gestion automatique des écritures comptables',
                'Support complet TVA française',
                'Codes comptes automatiques',
                'Informations SIREN/SIRET'
            ]
        }


def export_to_ebp_ascii(invoice: InvoiceData) -> str:
    """
    Convenience function to export a single invoice to EBP ASCII format
    
    Args:
        invoice: Invoice data to export
        
    Returns:
        EBP ASCII formatted string
    """
    exporter = EBPExporter()
    return exporter.export_invoice(invoice)


def export_batch_to_ebp_ascii(invoices: List[InvoiceData]) -> str:
    """
    Convenience function to export multiple invoices to EBP ASCII format
    
    Args:
        invoices: List of invoice data to export
        
    Returns:
        EBP ASCII formatted string for all invoices
    """
    exporter = EBPExporter()
    return exporter.export_batch(invoices)
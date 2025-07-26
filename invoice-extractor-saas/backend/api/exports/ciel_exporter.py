"""
Ciel Accounting Software Export Module

Exports invoice data to Ciel XIMPORT format for seamless integration with 
Ciel accounting software used by French experts-comptables.
"""

import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

from schemas.invoice import InvoiceData, FrenchBusinessInfo


class CielExporter:
    """Export invoice data to Ciel XIMPORT format"""
    
    def __init__(self):
        self.format_name = "Ciel XIMPORT"
        self.file_extension = ".txt"
    
    def export_invoice(self, invoice: InvoiceData) -> str:
        """
        Export a single invoice to Ciel XIMPORT format
        
        Args:
            invoice: Invoice data to export
            
        Returns:
            XIMPORT formatted string
        """
        lines = []
        
        # XIMPORT format uses fixed-width fields
        # Each line represents an accounting entry
        
        # Invoice header entry
        header_entry = self._format_invoice_header(invoice)
        lines.append(header_entry)
        
        # Vendor entry (if new vendor)
        if invoice.vendor and self._is_new_vendor(invoice.vendor):
            vendor_entries = self._format_vendor_entries(invoice.vendor)
            lines.extend(vendor_entries)
        
        # Accounting entries for the invoice
        accounting_entries = self._format_accounting_entries(invoice)
        lines.extend(accounting_entries)
        
        return '\\n'.join(lines)
    
    def export_batch(self, invoices: List[InvoiceData]) -> str:
        """
        Export multiple invoices to Ciel XIMPORT format
        
        Args:
            invoices: List of invoice data to export
            
        Returns:
            XIMPORT formatted string for all invoices
        """
        all_lines = []
        
        # XIMPORT batch header
        batch_header = self._format_batch_header(len(invoices))
        all_lines.append(batch_header)
        
        # Export each invoice
        for invoice in invoices:
            invoice_lines = self.export_invoice(invoice).split('\\n')
            all_lines.extend(invoice_lines)
        
        # Batch control totals
        batch_footer = self._format_batch_footer(invoices)
        all_lines.append(batch_footer)
        
        return '\\n'.join(all_lines)
    
    def _format_invoice_header(self, invoice: InvoiceData) -> str:
        """Format invoice header for Ciel XIMPORT"""
        
        # XIMPORT line format: Type(1) + Journal(2) + Date(8) + Piece(20) + Libelle(25) + etc.
        fields = []
        
        # Type (1 char): 'E' for Ecriture (Entry)
        fields.append('E')
        
        # Journal (2 chars): 'AC' for Achats (Purchases)
        fields.append('AC')
        
        # Date (8 chars): DDMMYYYY
        fields.append(self._format_date_ciel(invoice.date))
        
        # Piece number (20 chars)
        fields.append(self._pad_field(invoice.invoice_number or '', 20))
        
        # Description (25 chars)
        description = f"Facture {invoice.invoice_number}" if invoice.invoice_number else "Facture"
        fields.append(self._pad_field(description, 25))
        
        # Additional header information
        fields.append(self._pad_field('', 10))  # Reserved
        
        return ''.join(fields)
    
    def _format_vendor_entries(self, vendor: FrenchBusinessInfo) -> List[str]:
        """Format vendor creation entries for Ciel"""
        
        entries = []
        
        # Main vendor entry
        vendor_entry = self._format_vendor_main_entry(vendor)
        entries.append(vendor_entry)
        
        # Additional vendor information entries
        if vendor.address:
            address_entry = self._format_vendor_address_entry(vendor)
            entries.append(address_entry)
        
        return entries
    
    def _format_vendor_main_entry(self, vendor: FrenchBusinessInfo) -> str:
        """Format main vendor entry"""
        
        fields = []
        
        # Type: 'F' for Fournisseur (Supplier)
        fields.append('F')
        
        # Vendor code (8 chars) - based on SIREN if available
        vendor_code = self._generate_vendor_code(vendor)
        fields.append(self._pad_field(vendor_code, 8))
        
        # Vendor name (35 chars)
        fields.append(self._pad_field(vendor.name, 35))
        
        # SIREN (9 chars)
        fields.append(self._pad_field(vendor.siren_number or '', 9))
        
        # SIRET (14 chars)
        fields.append(self._pad_field(vendor.siret_number or '', 14))
        
        # TVA number (13 chars)
        fields.append(self._pad_field(vendor.tva_number or '', 13))
        
        # NAF code (5 chars)
        fields.append(self._pad_field(vendor.naf_code or '', 5))
        
        # Legal form (10 chars)
        fields.append(self._pad_field(vendor.legal_form or '', 10))
        
        return ''.join(fields)
    
    def _format_vendor_address_entry(self, vendor: FrenchBusinessInfo) -> str:
        """Format vendor address entry"""
        
        fields = []
        
        # Type: 'A' for Address
        fields.append('A')
        
        # Vendor code (8 chars)
        vendor_code = self._generate_vendor_code(vendor)
        fields.append(self._pad_field(vendor_code, 8))
        
        # Address (35 chars)
        fields.append(self._pad_field(vendor.address or '', 35))
        
        # Postal code (5 chars)
        fields.append(self._pad_field(vendor.postal_code or '', 5))
        
        # City (25 chars)
        fields.append(self._pad_field(vendor.city or '', 25))
        
        # Country (15 chars)
        fields.append(self._pad_field(vendor.country or 'France', 15))
        
        # Phone (15 chars)
        fields.append(self._pad_field(vendor.phone or '', 15))
        
        # Email (50 chars)
        fields.append(self._pad_field(vendor.email or '', 50))
        
        return ''.join(fields)
    
    def _format_accounting_entries(self, invoice: InvoiceData) -> List[str]:
        """Format accounting entries for the invoice"""
        
        entries = []
        
        # Supplier credit entry
        supplier_entry = self._format_supplier_credit_entry(invoice)
        entries.append(supplier_entry)
        
        # Line items debit entries
        for i, item in enumerate(invoice.line_items):
            item_entry = self._format_line_item_entry(item, invoice, i + 1)
            entries.append(item_entry)
        
        # TVA debit entries
        for tva_item in invoice.tva_breakdown:
            tva_entry = self._format_tva_debit_entry(tva_item, invoice)
            entries.append(tva_entry)
        
        return entries
    
    def _format_supplier_credit_entry(self, invoice: InvoiceData) -> str:
        """Format supplier account credit entry"""
        
        fields = []
        
        # Type: 'L' for Ligne d'écriture (Accounting line)
        fields.append('L')
        
        # Journal (2 chars)
        fields.append('AC')
        
        # Date (8 chars)
        fields.append(self._format_date_ciel(invoice.date))
        
        # Account (8 chars) - Supplier account
        supplier_account = self._get_supplier_account(invoice.vendor)
        fields.append(self._pad_field(supplier_account, 8))
        
        # Auxiliary account (8 chars) - Vendor code
        vendor_code = self._generate_vendor_code(invoice.vendor) if invoice.vendor else ''
        fields.append(self._pad_field(vendor_code, 8))
        
        # Description (25 chars)
        description = f"Facture {invoice.invoice_number}" if invoice.invoice_number else "Facture"
        fields.append(self._pad_field(description, 25))
        
        # Debit amount (15 chars) - 0 for credit entry
        fields.append(self._format_amount_ciel(0))
        
        # Credit amount (15 chars)
        total_amount = invoice.total_ttc or invoice.total or 0
        fields.append(self._format_amount_ciel(total_amount))
        
        # Piece number (20 chars)
        fields.append(self._pad_field(invoice.invoice_number or '', 20))
        
        # Due date (8 chars)
        due_date = invoice.due_date if invoice.due_date else invoice.date
        fields.append(self._format_date_ciel(due_date))
        
        return ''.join(fields)
    
    def _format_line_item_entry(self, item, invoice: InvoiceData, line_number: int) -> str:
        """Format line item debit entry"""
        
        fields = []
        
        # Type: 'L' for Ligne d'écriture
        fields.append('L')
        
        # Journal (2 chars)
        fields.append('AC')
        
        # Date (8 chars)
        fields.append(self._format_date_ciel(invoice.date))
        
        # Account (8 chars) - Expense account based on item type
        account = self._determine_expense_account(item.description)
        fields.append(self._pad_field(account, 8))
        
        # Auxiliary account (8 chars) - Empty for expense accounts
        fields.append(self._pad_field('', 8))
        
        # Description (25 chars)
        description = self._truncate_field(item.description, 25)
        fields.append(self._pad_field(description, 25))
        
        # Debit amount (15 chars) - Item total HT
        fields.append(self._format_amount_ciel(item.total))
        
        # Credit amount (15 chars) - 0 for debit entry
        fields.append(self._format_amount_ciel(0))
        
        # Piece number (20 chars)
        fields.append(self._pad_field(invoice.invoice_number or '', 20))
        
        # Additional fields
        fields.append(self._pad_field('', 8))  # Date échéance (empty for expense)
        
        # Quantity and unit price
        fields.append(self._format_quantity_ciel(item.quantity))
        fields.append(self._format_amount_ciel(item.unit_price))
        
        return ''.join(fields)
    
    def _format_tva_debit_entry(self, tva_item, invoice: InvoiceData) -> str:
        """Format TVA debit entry"""
        
        fields = []
        
        # Type: 'L' for Ligne d'écriture
        fields.append('L')
        
        # Journal (2 chars)
        fields.append('AC')
        
        # Date (8 chars)
        fields.append(self._format_date_ciel(invoice.date))
        
        # Account (8 chars) - TVA account
        tva_account = self._get_tva_account_ciel(tva_item.rate)
        fields.append(self._pad_field(tva_account, 8))
        
        # Auxiliary account (8 chars) - Empty
        fields.append(self._pad_field('', 8))
        
        # Description (25 chars)
        description = f"TVA {tva_item.rate}%"
        fields.append(self._pad_field(description, 25))
        
        # Debit amount (15 chars) - TVA amount
        fields.append(self._format_amount_ciel(tva_item.tva_amount))
        
        # Credit amount (15 chars) - 0 for debit entry
        fields.append(self._format_amount_ciel(0))
        
        # Piece number (20 chars)
        fields.append(self._pad_field(invoice.invoice_number or '', 20))
        
        # Additional fields
        fields.append(self._pad_field('', 8))  # Date échéance
        
        return ''.join(fields)
    
    def _format_batch_header(self, count: int) -> str:
        """Format batch header for Ciel XIMPORT"""
        
        fields = []
        
        # Header type
        fields.append('H')
        
        # Version
        fields.append(self._pad_field('CIEL_V3', 10))
        
        # Creation date
        fields.append(self._format_date_ciel(datetime.now().date()))
        
        # Number of entries
        fields.append(self._pad_field(str(count), 10))
        
        # Origin
        fields.append(self._pad_field('INVOICE_AI', 20))
        
        return ''.join(fields)
    
    def _format_batch_footer(self, invoices: List[InvoiceData]) -> str:
        """Format batch footer with control totals"""
        
        total_debit = sum(
            (inv.subtotal_ht or inv.subtotal or 0) + (inv.total_tva or inv.tax or 0)
            for inv in invoices
        )
        total_credit = sum(inv.total_ttc or inv.total or 0 for inv in invoices)
        
        fields = []
        
        # Footer type
        fields.append('T')
        
        # Total entries
        fields.append(self._pad_field(str(len(invoices)), 10))
        
        # Total debit
        fields.append(self._format_amount_ciel(total_debit))
        
        # Total credit
        fields.append(self._format_amount_ciel(total_credit))
        
        return ''.join(fields)
    
    # Helper methods
    
    def _format_date_ciel(self, date_input) -> str:
        """Format date for Ciel (DDMMYYYY)"""
        
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
    
    def _format_amount_ciel(self, amount) -> str:
        """Format amount for Ciel (15 chars, right-aligned, 2 decimals)"""
        
        if amount is None:
            amount = 0
        
        # Convert to cents for precision
        cents = int(round(float(amount) * 100))
        
        # Format with sign
        amount_str = f"{cents:+013d}"  # 13 digits + sign
        
        return amount_str.rjust(15)
    
    def _format_quantity_ciel(self, quantity) -> str:
        """Format quantity for Ciel (10 chars)"""
        
        if quantity is None:
            return ' ' * 10
        
        # Format with 3 decimal places
        qty_str = f"{float(quantity):.3f}"
        return qty_str.rjust(10)
    
    def _pad_field(self, value: str, width: int) -> str:
        """Pad field to specified width"""
        
        return str(value)[:width].ljust(width)
    
    def _truncate_field(self, value: str, max_length: int) -> str:
        """Truncate field to maximum length"""
        
        return str(value)[:max_length] if value else ''
    
    def _generate_vendor_code(self, vendor: Optional[FrenchBusinessInfo]) -> str:
        """Generate vendor code from SIREN or name"""
        
        if not vendor:
            return 'FOUR001'
        
        if vendor.siren_number:
            return f"F{vendor.siren_number[-6:]}"
        elif vendor.name:
            # Use first 8 chars of name, alphanumeric only
            name_clean = ''.join(c for c in vendor.name if c.isalnum())[:8]
            return name_clean.upper().ljust(8)
        else:
            return 'FOUR001'
    
    def _get_supplier_account(self, vendor: Optional[FrenchBusinessInfo]) -> str:
        """Get supplier general account"""
        
        return '401000'  # Standard French supplier account
    
    def _determine_expense_account(self, description: str) -> str:
        """Determine expense account based on description"""
        
        # Simplified mapping - in practice, you'd want more sophisticated logic
        description_lower = description.lower() if description else ''
        
        if any(word in description_lower for word in ['service', 'prestation', 'consultation']):
            return '606000'  # Services
        elif any(word in description_lower for word in ['matériel', 'équipement']):
            return '606100'  # Equipment
        elif any(word in description_lower for word in ['fourniture', 'matière']):
            return '607000'  # Supplies
        else:
            return '607000'  # Default
    
    def _get_tva_account_ciel(self, rate: float) -> str:
        """Get TVA account for Ciel"""
        
        tva_accounts = {
            20.0: '445662',  # TVA déductible 20%
            10.0: '445661',  # TVA déductible 10%
            5.5: '445663',   # TVA déductible 5.5%
            2.1: '445664',   # TVA déductible 2.1%
            0.0: '445660'    # TVA déductible 0%
        }
        
        return tva_accounts.get(rate, '445662')
    
    def _is_new_vendor(self, vendor: FrenchBusinessInfo) -> bool:
        """Check if vendor is new (simplified - in practice, check against existing vendors)"""
        
        # In a real implementation, you'd check against existing vendor database
        return True
    
    def get_export_info(self) -> Dict[str, Any]:
        """Get information about this export format"""
        
        return {
            'name': 'Ciel XIMPORT',
            'description': 'Format d\\'export XIMPORT pour logiciels Ciel Comptabilité',
            'file_extension': '.txt',
            'mime_type': 'text/plain',
            'software_compatibility': [
                'Ciel Comptabilité',
                'Ciel Compta Evolution',
                'Ciel Gestion Commerciale',
                'Ciel Associations',
                'Ciel Auto-Entrepreneur'
            ],
            'features': [
                'Format XIMPORT standard',
                'Import direct dans Ciel',
                'Création automatique des fournisseurs',
                'Écritures comptables complètes',
                'Support TVA multi-taux',
                'Informations SIREN/SIRET/TVA'
            ]
        }


def export_to_ciel_ximport(invoice: InvoiceData) -> str:
    """
    Convenience function to export a single invoice to Ciel XIMPORT format
    
    Args:
        invoice: Invoice data to export
        
    Returns:
        XIMPORT formatted string
    """
    exporter = CielExporter()
    return exporter.export_invoice(invoice)


def export_batch_to_ciel_ximport(invoices: List[InvoiceData]) -> str:
    """
    Convenience function to export multiple invoices to Ciel XIMPORT format
    
    Args:
        invoices: List of invoice data to export
        
    Returns:
        XIMPORT formatted string for all invoices
    """
    exporter = CielExporter()
    return exporter.export_batch(invoices)
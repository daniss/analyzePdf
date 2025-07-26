"""
Sage Accounting Software Export Module

Exports invoice data to Sage PNM format for seamless integration with 
Sage accounting software used by French experts-comptables.
"""

import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

from schemas.invoice import InvoiceData, FrenchBusinessInfo


class SageExporter:
    """Export invoice data to Sage PNM format"""
    
    def __init__(self):
        self.format_name = "Sage PNM"
        self.file_extension = ".pnm"
    
    def export_invoice(self, invoice: InvoiceData) -> str:
        """
        Export a single invoice to Sage PNM format
        
        Args:
            invoice: Invoice data to export
            
        Returns:
            PNM formatted string
        """
        lines = []
        
        # Header line with invoice information
        header = self._format_header_line(invoice)
        lines.append(header)
        
        # Vendor line (if needed)
        if invoice.vendor:
            vendor_line = self._format_vendor_line(invoice.vendor)
            if vendor_line:
                lines.append(vendor_line)
        
        # Customer line (if needed)
        if invoice.customer:
            customer_line = self._format_customer_line(invoice.customer)
            if customer_line:
                lines.append(customer_line)
        
        # Line items
        for item in invoice.line_items:
            item_line = self._format_line_item(item, invoice)
            lines.append(item_line)
        
        # TVA lines
        for tva_item in invoice.tva_breakdown:
            tva_line = self._format_tva_line(tva_item, invoice)
            lines.append(tva_line)
        
        # Total line
        total_line = self._format_total_line(invoice)
        lines.append(total_line)
        
        return '\\n'.join(lines)
    
    def export_batch(self, invoices: List[InvoiceData]) -> str:
        """
        Export multiple invoices to Sage PNM format
        
        Args:
            invoices: List of invoice data to export
            
        Returns:
            PNM formatted string for all invoices
        """
        all_lines = []
        
        # Batch header
        batch_header = self._format_batch_header(len(invoices))
        all_lines.append(batch_header)
        
        # Export each invoice
        for invoice in invoices:
            invoice_lines = self.export_invoice(invoice).split('\\n')
            all_lines.extend(invoice_lines)
        
        # Batch footer
        batch_footer = self._format_batch_footer(invoices)
        all_lines.append(batch_footer)
        
        return '\\n'.join(all_lines)
    
    def _format_header_line(self, invoice: InvoiceData) -> str:
        """Format the header line for Sage PNM"""
        
        # PNM header format: Type|Date|Reference|Description|...
        return '|'.join([
            'ENT',  # Entry type
            self._format_date(invoice.date) or '',
            invoice.invoice_number or '',
            f"Facture {invoice.invoice_number}" if invoice.invoice_number else 'Facture',
            invoice.vendor.name if invoice.vendor else '',
            self._format_amount(invoice.total_ttc or invoice.total or 0),
            'EUR',  # Currency
            ''  # Additional fields as needed
        ])
    
    def _format_vendor_line(self, vendor: FrenchBusinessInfo) -> Optional[str]:
        """Format vendor information line"""
        
        if not vendor.name:
            return None
        
        return '|'.join([
            'FOU',  # Supplier type
            self._clean_text(vendor.name),
            self._clean_text(vendor.address or ''),
            vendor.postal_code or '',
            self._clean_text(vendor.city or ''),
            vendor.siren_number or '',
            vendor.siret_number or '',
            vendor.tva_number or '',
            vendor.naf_code or '',
            vendor.legal_form or '',
            str(vendor.share_capital or '') if vendor.share_capital else '',
            vendor.phone or '',
            vendor.email or ''
        ])
    
    def _format_customer_line(self, customer: FrenchBusinessInfo) -> Optional[str]:
        """Format customer information line"""
        
        if not customer.name:
            return None
        
        return '|'.join([
            'CLI',  # Customer type
            self._clean_text(customer.name),
            self._clean_text(customer.address or ''),
            customer.postal_code or '',
            self._clean_text(customer.city or ''),
            customer.siren_number or '',
            customer.siret_number or '',
            customer.tva_number or '',
            customer.phone or '',
            customer.email or ''
        ])
    
    def _format_line_item(self, item, invoice: InvoiceData) -> str:
        """Format line item for Sage PNM"""
        
        return '|'.join([
            'LIG',  # Line item type
            self._clean_text(item.description),
            str(item.quantity),
            item.unit or 'pièce',
            self._format_amount(item.unit_price),
            self._format_amount(item.total),
            str(item.tva_rate or 20.0),
            self._format_amount(item.tva_amount or 0),
            'EUR'
        ])
    
    def _format_tva_line(self, tva_item, invoice: InvoiceData) -> str:
        """Format TVA breakdown line"""
        
        return '|'.join([
            'TVA',  # TVA type
            str(tva_item.rate),
            self._format_amount(tva_item.taxable_amount),
            self._format_amount(tva_item.tva_amount),
            'EUR'
        ])
    
    def _format_total_line(self, invoice: InvoiceData) -> str:
        """Format total line"""
        
        return '|'.join([
            'TOT',  # Total type
            self._format_amount(invoice.subtotal_ht or invoice.subtotal or 0),
            self._format_amount(invoice.total_tva or invoice.tax or 0),
            self._format_amount(invoice.total_ttc or invoice.total or 0),
            'EUR'
        ])
    
    def _format_batch_header(self, count: int) -> str:
        """Format batch header"""
        
        return '|'.join([
            'BAT',  # Batch type
            'DEBUT',
            str(count),
            self._format_date(datetime.now().date()),
            'IMPORT_FACTURES'
        ])
    
    def _format_batch_footer(self, invoices: List[InvoiceData]) -> str:
        """Format batch footer with totals"""
        
        total_ht = sum(inv.subtotal_ht or inv.subtotal or 0 for inv in invoices)
        total_tva = sum(inv.total_tva or inv.tax or 0 for inv in invoices)
        total_ttc = sum(inv.total_ttc or inv.total or 0 for inv in invoices)
        
        return '|'.join([
            'BAT',  # Batch type
            'FIN',
            str(len(invoices)),
            self._format_amount(total_ht),
            self._format_amount(total_tva),
            self._format_amount(total_ttc),
            'EUR'
        ])
    
    def _format_date(self, date_input) -> str:
        """Format date for Sage PNM (DD/MM/YYYY)"""
        
        if not date_input:
            return ''
        
        if isinstance(date_input, str):
            try:
                # Try to parse ISO format
                date_obj = datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try French format
                    date_obj = datetime.strptime(date_input, '%d/%m/%Y').date()
                except ValueError:
                    return date_input  # Return as-is if can't parse
        else:
            date_obj = date_input
        
        return date_obj.strftime('%d/%m/%Y')
    
    def _format_amount(self, amount) -> str:
        """Format amount for Sage PNM (French decimal format)"""
        
        if amount is None:
            return '0,00'
        
        # Convert to float if needed
        if isinstance(amount, str):
            try:
                amount = float(amount.replace(',', '.'))
            except ValueError:
                return '0,00'
        
        # Format with French decimal separator (comma)
        return f"{amount:.2f}".replace('.', ',')
    
    def _clean_text(self, text: str) -> str:
        """Clean text for PNM format (remove special characters)"""
        
        if not text:
            return ''
        
        # Remove pipe characters and other problematic chars
        cleaned = text.replace('|', ' ').replace('\\n', ' ').replace('\\r', ' ')
        
        # Remove extra whitespace
        return ' '.join(cleaned.split())
    
    def get_export_info(self) -> Dict[str, Any]:
        """Get information about this export format"""
        
        return {
            'name': 'Sage PNM',
            'description': 'Format d\\'export pour logiciels comptables Sage',
            'file_extension': '.pnm',
            'mime_type': 'text/plain',
            'software_compatibility': [
                'Sage 100 Comptabilité',
                'Sage 100 Gestion Commerciale',
                'Sage Ligne 100',
                'Sage i7'
            ],
            'features': [
                'Import direct dans Sage',
                'Gestion des fournisseurs et clients',
                'Détail des TVA par taux',
                'Numéros SIREN/SIRET',
                'Format français (DD/MM/YYYY, virgule décimale)'
            ]
        }


def export_to_sage_pnm(invoice: InvoiceData) -> str:
    """
    Convenience function to export a single invoice to Sage PNM format
    
    Args:
        invoice: Invoice data to export
        
    Returns:
        PNM formatted string
    """
    exporter = SageExporter()
    return exporter.export_invoice(invoice)


def export_batch_to_sage_pnm(invoices: List[InvoiceData]) -> str:
    """
    Convenience function to export multiple invoices to Sage PNM format
    
    Args:
        invoices: List of invoice data to export
        
    Returns:
        PNM formatted string for all invoices
    """
    exporter = SageExporter()
    return exporter.export_batch(invoices)
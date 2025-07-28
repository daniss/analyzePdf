"""
FEC (Fichier des Écritures Comptables) Export Module

Exports invoice data to FEC format for French tax administration compliance.
FEC format is mandatory for French businesses and must be provided during tax audits.

Complies with:
- Article L. 47 A of the French tax procedures book
- Decree of July 29, 2013
- DGFiP specifications for computerized accounting files
"""

import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

from schemas.invoice import InvoiceData, FrenchBusinessInfo


class FECExporter:
    """Export invoice data to FEC (Fichier des Écritures Comptables) format"""
    
    def __init__(self):
        self.format_name = "FEC"
        self.file_extension = ".txt"
        self.separator = "|"  # Pipe separator as per FEC specification
        
        # FEC column headers as per DGFiP specification
        self.fec_headers = [
            'JournalCode',       # Code journal
            'JournalLib',        # Libellé journal
            'EcritureNum',       # Numéro sur une séquence continue
            'EcritureDate',      # Date de comptabilisation
            'CompteNum',         # Numéro de compte
            'CompteLib',         # Libellé de compte
            'CompAuxNum',        # Numéro de compte auxiliaire
            'CompAuxLib',        # Libellé de compte auxiliaire
            'PieceRef',          # Référence de la pièce justificative
            'PieceDate',         # Date de la pièce justificative
            'EcritureLib',       # Libellé de l\'écriture
            'Debit',             # Montant au débit
            'Credit',            # Montant au crédit
            'EcritureLet',       # Lettrage de l\'écriture
            'DateLet',           # Date de lettrage
            'ValidDate',         # Date de validation de l\'écriture
            'Montantdevise',     # Montant en devise
            'Idevise'            # Identifiant de la devise
        ]
    
    def export_invoice(self, invoice: InvoiceData, journal_code: str = "ACH", 
                      sequence_number: int = 1) -> str:
        """
        Export a single invoice to FEC format
        
        Args:
            invoice: Invoice data to export
            journal_code: Journal code (default: ACH for purchases)
            sequence_number: Sequential number for FEC compliance
            
        Returns:
            FEC formatted string
        """
        entries = []
        
        # Generate accounting entries for the invoice
        invoice_entries = self._generate_invoice_entries(
            invoice, journal_code, sequence_number
        )
        entries.extend(invoice_entries)
        
        return self._format_fec_output(entries)
    
    def export_batch(self, invoices: List[InvoiceData], 
                    journal_code: str = "ACH") -> str:
        """
        Export multiple invoices to FEC format
        
        Args:
            invoices: List of invoice data to export
            journal_code: Journal code for all invoices
            
        Returns:
            FEC formatted string for all invoices
        """
        all_entries = []
        sequence_counter = 1
        
        for invoice in invoices:
            invoice_entries = self._generate_invoice_entries(
                invoice, journal_code, sequence_counter
            )
            all_entries.extend(invoice_entries)
            sequence_counter += len(invoice_entries)
        
        return self._format_fec_output(all_entries)
    
    def _generate_invoice_entries(self, invoice: InvoiceData, 
                                journal_code: str, 
                                base_sequence: int) -> List[Dict[str, str]]:
        """Generate FEC accounting entries for an invoice"""
        
        entries = []
        sequence = base_sequence
        
        # Entry date (comptabilization date)
        entry_date = self._format_fec_date(invoice.date)
        piece_date = self._format_fec_date(invoice.date)
        validation_date = self._format_fec_date(datetime.now().date())
        
        # 1. Supplier account credit entry (401xxx)
        supplier_entry = {
            'JournalCode': journal_code,
            'JournalLib': self._get_journal_name(journal_code),
            'EcritureNum': str(sequence),
            'EcritureDate': entry_date,
            'CompteNum': self._get_supplier_account(invoice.vendor),
            'CompteLib': 'Fournisseurs',
            'CompAuxNum': self._get_supplier_aux_account(invoice.vendor),
            'CompAuxLib': self._get_supplier_name(invoice.vendor)[:100],  # Max 100 chars
            'PieceRef': invoice.invoice_number or f"FACT{sequence}",
            'PieceDate': piece_date,
            'EcritureLib': f"Facture {invoice.invoice_number or sequence}"[:100],
            'Debit': self._format_fec_amount(0),
            'Credit': self._format_fec_amount(invoice.total_ttc or invoice.total or 0),
            'EcritureLet': '',
            'DateLet': '',
            'ValidDate': validation_date,
            'Montantdevise': self._format_fec_amount(invoice.total_ttc or invoice.total or 0),
            'Idevise': 'EUR'
        }
        entries.append(supplier_entry)
        sequence += 1
        
        # 2. Expense account debit entries (6xxxxx)
        for item in invoice.line_items:
            expense_account = self._determine_expense_account(item.description)
            
            item_entry = {
                'JournalCode': journal_code,
                'JournalLib': self._get_journal_name(journal_code),
                'EcritureNum': str(sequence),
                'EcritureDate': entry_date,
                'CompteNum': expense_account,
                'CompteLib': self._get_account_name(expense_account),
                'CompAuxNum': '',
                'CompAuxLib': '',
                'PieceRef': invoice.invoice_number or f"FACT{base_sequence}",
                'PieceDate': piece_date,
                'EcritureLib': item.description[:100] if item.description else f"Article {sequence}",
                'Debit': self._format_fec_amount(item.total),
                'Credit': self._format_fec_amount(0),
                'EcritureLet': '',
                'DateLet': '',
                'ValidDate': validation_date,
                'Montantdevise': self._format_fec_amount(item.total),
                'Idevise': 'EUR'
            }
            entries.append(item_entry)
            sequence += 1
        
        # 3. TVA debit entries (445xxx)
        for tva_item in invoice.tva_breakdown:
            if tva_item.tva_amount > 0:  # Only create entry if TVA amount > 0
                tva_account = self._get_tva_account(tva_item.rate)
                
                tva_entry = {
                    'JournalCode': journal_code,
                    'JournalLib': self._get_journal_name(journal_code),
                    'EcritureNum': str(sequence),
                    'EcritureDate': entry_date,
                    'CompteNum': tva_account,
                    'CompteLib': f"TVA déductible {tva_item.rate}%",
                    'CompAuxNum': '',
                    'CompAuxLib': '',
                    'PieceRef': invoice.invoice_number or f"FACT{base_sequence}",
                    'PieceDate': piece_date,
                    'EcritureLib': f"TVA {tva_item.rate}% sur facture {invoice.invoice_number or base_sequence}"[:100],
                    'Debit': self._format_fec_amount(tva_item.tva_amount),
                    'Credit': self._format_fec_amount(0),
                    'EcritureLet': '',
                    'DateLet': '',
                    'ValidDate': validation_date,
                    'Montantdevise': self._format_fec_amount(tva_item.tva_amount),
                    'Idevise': 'EUR'
                }
                entries.append(tva_entry)
                sequence += 1
        
        return entries
    
    def _format_fec_output(self, entries: List[Dict[str, str]]) -> str:
        """Format entries as FEC file content"""
        
        output = io.StringIO()
        writer = csv.DictWriter(
            output, 
            fieldnames=self.fec_headers, 
            delimiter=self.separator,
            quoting=csv.QUOTE_NONE,
            escapechar=None,
            lineterminator='\\n'
        )
        
        # Write header
        writer.writeheader()
        
        # Write entries
        for entry in entries:
            writer.writerow(entry)
        
        content = output.getvalue()
        output.close()
        
        return content
    
    def _format_fec_date(self, date_input) -> str:
        """Format date for FEC (YYYYMMDD)"""
        
        if not date_input:
            return datetime.now().strftime('%Y%m%d')
        
        if isinstance(date_input, str):
            try:
                # Try to parse ISO format
                date_obj = datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try French format
                    date_obj = datetime.strptime(date_input, '%d/%m/%Y').date()
                except ValueError:
                    return datetime.now().strftime('%Y%m%d')
        else:
            date_obj = date_input
        
        return date_obj.strftime('%Y%m%d')
    
    def _format_fec_amount(self, amount) -> str:
        """Format amount for FEC (no currency symbol, dot as decimal separator)"""
        
        if amount is None or amount == 0:
            return ''  # Empty for zero amounts in FEC
        
        # Convert to float if needed
        if isinstance(amount, str):
            try:
                amount = float(amount.replace(',', '.'))
            except ValueError:
                return ''
        
        # Format with 2 decimal places, dot as separator
        return f"{float(amount):.2f}"
    
    def _get_journal_name(self, journal_code: str) -> str:
        """Get journal name from code"""
        
        journal_names = {
            'ACH': 'Achats',
            'VTE': 'Ventes',
            'BQ': 'Banque',
            'CAS': 'Caisse',
            'OD': 'Opérations diverses'
        }
        
        return journal_names.get(journal_code, 'Journal')
    
    def _get_supplier_account(self, vendor: Optional[FrenchBusinessInfo]) -> str:
        """Get supplier general account (401xxx)"""
        
        return '401000'  # Standard French supplier account
    
    def _get_supplier_aux_account(self, vendor: Optional[FrenchBusinessInfo]) -> str:
        """Get supplier auxiliary account code"""
        
        if not vendor:
            return 'FOUR001'
        
        if vendor.siren_number:
            # Use SIREN for auxiliary account
            return vendor.siren_number
        elif vendor.siret_number:
            # Use SIRET if no SIREN
            return vendor.siret_number
        else:
            # Generate from name
            name_clean = ''.join(c for c in (vendor.name or 'FOUR') if c.isalnum())[:8]
            return name_clean.upper()
    
    def _get_supplier_name(self, vendor: Optional[FrenchBusinessInfo]) -> str:
        """Get supplier name for FEC"""
        
        if not vendor or not vendor.name:
            return 'Fournisseur inconnu'
        
        return vendor.name
    
    def _determine_expense_account(self, description: str) -> str:
        """Determine expense account based on item description"""
        
        if not description:
            return '607000'  # Default supplies account
        
        description_lower = description.lower()
        
        # French Chart of Accounts (Plan Comptable Général)
        if any(word in description_lower for word in [
            'service', 'prestation', 'consultation', 'formation', 'conseil'
        ]):
            return '611000'  # Services extérieurs
        elif any(word in description_lower for word in [
            'matériel', 'équipement', 'machine', 'ordinateur', 'informatique'
        ]):
            return '606200'  # Matériel et équipements
        elif any(word in description_lower for word in [
            'fourniture', 'matière', 'produit', 'stock'
        ]):
            return '607000'  # Achats de marchandises
        elif any(word in description_lower for word in [
            'transport', 'livraison', 'expédition'
        ]):
            return '624100'  # Transport de biens
        elif any(word in description_lower for word in [
            'communication', 'téléphone', 'internet', 'publicité'
        ]):
            return '623000'  # Publicité, publications, relations publiques
        elif any(word in description_lower for word in [
            'assurance', 'responsabilité'
        ]):
            return '616000'  # Primes d\'assurance
        elif any(word in description_lower for word in [
            'location', 'loyer', 'bail'
        ]):
            return '613000'  # Locations
        else:
            return '607000'  # Default to supplies
    
    def _get_account_name(self, account_code: str) -> str:
        """Get account name from code"""
        
        account_names = {
            '401000': 'Fournisseurs',
            '607000': 'Achats de marchandises',
            '606200': 'Matériel et équipements',
            '611000': 'Services extérieurs',
            '624100': 'Transport de biens',
            '623000': 'Publicité et relations publiques',
            '616000': 'Primes d\'assurance',
            '613000': 'Locations',
            '445662': 'TVA déductible sur biens',
            '445663': 'TVA déductible sur services'
        }
        
        return account_names.get(account_code, 'Compte')
    
    def _get_tva_account(self, rate: float) -> str:
        """Get TVA account based on rate"""
        
        # French TVA accounts (Plan Comptable Général)
        tva_accounts = {
            20.0: '445662',  # TVA déductible sur biens
            10.0: '445663',  # TVA déductible sur services
            5.5: '445663',   # TVA déductible sur services (reduced rate)
            2.1: '445663',   # TVA déductible sur services (super reduced)
            0.0: '445660'    # TVA déductible (exempt)
        }
        
        return tva_accounts.get(rate, '445662')
    
    def validate_fec_compliance(self, entries: List[Dict[str, str]]) -> Dict[str, Any]:
        """Validate FEC compliance"""
        
        errors = []
        warnings = []
        
        # Check balanced entries
        total_debit = 0
        total_credit = 0
        
        for entry in entries:
            try:
                debit = float(entry.get('Debit', '0') or '0')
                credit = float(entry.get('Credit', '0') or '0')
                total_debit += debit
                total_credit += credit
            except ValueError:
                errors.append(f"Invalid amount in entry {entry.get('EcritureNum', '?')}")
        
        # Check if entries are balanced
        if abs(total_debit - total_credit) > 0.01:
            errors.append(f"Entries not balanced: Debit {total_debit:.2f} != Credit {total_credit:.2f}")
        
        # Check required fields
        required_fields = ['JournalCode', 'EcritureDate', 'CompteNum', 'PieceRef']
        for i, entry in enumerate(entries):
            for field in required_fields:
                if not entry.get(field):
                    errors.append(f"Missing required field '{field}' in entry {i+1}")
        
        # Check date format
        for i, entry in enumerate(entries):
            date_fields = ['EcritureDate', 'PieceDate', 'ValidDate']
            for date_field in date_fields:
                date_value = entry.get(date_field)
                if date_value and not self._is_valid_fec_date(date_value):
                    errors.append(f"Invalid date format in entry {i+1}, field {date_field}: {date_value}")
        
        # Check sequential numbering (warning only)
        sequence_numbers = [int(entry.get('EcritureNum', '0')) for entry in entries]
        if sequence_numbers != sorted(sequence_numbers):
            warnings.append("Entry numbers are not sequential")
        
        return {
            'is_compliant': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_entries': len(entries),
            'total_debit': total_debit,
            'total_credit': total_credit
        }
    
    def _is_valid_fec_date(self, date_str: str) -> bool:
        """Check if date string is valid FEC format (YYYYMMDD)"""
        
        if not date_str or len(date_str) != 8:
            return False
        
        try:
            datetime.strptime(date_str, '%Y%m%d')
            return True
        except ValueError:
            return False
    
    def get_export_info(self) -> Dict[str, Any]:
        """Get information about FEC export format"""
        
        return {
            'name': 'FEC',
            'description': 'Fichier des Écritures Comptables pour l\'administration fiscale française',
            'file_extension': '.txt',
            'mime_type': 'text/plain',
            'compliance': [
                'Article L. 47 A du livre des procédures fiscales',
                'Décret du 29 juillet 2013',
                'Spécifications DGFiP'
            ],
            'mandatory_for': [
                'Entreprises tenues de respecter les obligations comptables',
                'Contrôles fiscaux',
                'Audits comptables'
            ],
            'features': [
                'Format standardisé DGFiP',
                'Écritures comptables équilibrées',
                'Numérotation séquentielle',
                'Contrôles de cohérence intégrés',
                'Comptes du Plan Comptable Général',
                'Gestion TVA multi-taux'
            ]
        }


def export_to_fec(invoice: InvoiceData, journal_code: str = "ACH", 
                 sequence_number: int = 1) -> str:
    """
    Convenience function to export a single invoice to FEC format
    
    Args:
        invoice: Invoice data to export
        journal_code: Journal code (default: ACH)
        sequence_number: Sequential number for FEC compliance
        
    Returns:
        FEC formatted string
    """
    exporter = FECExporter()
    return exporter.export_invoice(invoice, journal_code, sequence_number)


def export_batch_to_fec(invoices: List[InvoiceData], 
                       journal_code: str = "ACH") -> str:
    """
    Convenience function to export multiple invoices to FEC format
    
    Args:
        invoices: List of invoice data to export
        journal_code: Journal code for all invoices
        
    Returns:
        FEC formatted string for all invoices
    """
    exporter = FECExporter()
    return exporter.export_batch(invoices, journal_code)


def validate_fec_file(fec_content: str) -> Dict[str, Any]:
    """
    Validate FEC file content for compliance
    
    Args:
        fec_content: FEC file content as string
        
    Returns:
        Validation results
    """
    exporter = FECExporter()
    
    # Parse FEC content back to entries
    lines = fec_content.strip().split('\\n')
    if not lines:
        return {'is_compliant': False, 'errors': ['Empty FEC file']}
    
    # Skip header line
    entries = []
    reader = csv.DictReader(lines, delimiter=exporter.separator)
    
    try:
        for row in reader:
            entries.append(row)
    except csv.Error as e:
        return {'is_compliant': False, 'errors': [f'CSV parsing error: {e}']}
    
    return exporter.validate_fec_compliance(entries)
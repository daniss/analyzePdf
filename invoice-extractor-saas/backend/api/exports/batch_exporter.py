import os
import json
import csv
import io
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from schemas.invoice import InvoiceData


class BatchExporter:
    """Handles batch export of processed invoices to various formats"""
    
    async def create_batch_export(
        self, 
        processed_data: List[Dict[str, Any]], 
        export_format: str, 
        output_dir: str
    ) -> str:
        """Create batch export file and return file path"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == "csv":
            return await self._export_to_csv(processed_data, output_dir, timestamp)
        elif export_format == "json":
            return await self._export_to_json(processed_data, output_dir, timestamp)
        elif export_format == "excel":
            return await self._export_to_excel(processed_data, output_dir, timestamp)
        elif export_format == "sage":
            return await self._export_to_sage(processed_data, output_dir, timestamp)
        elif export_format == "ebp":
            return await self._export_to_ebp(processed_data, output_dir, timestamp)
        elif export_format == "ciel":
            return await self._export_to_ciel(processed_data, output_dir, timestamp)
        elif export_format == "fec":
            return await self._export_to_fec(processed_data, output_dir, timestamp)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    async def _export_to_csv(self, processed_data: List[Dict], output_dir: str, timestamp: str) -> str:
        """Export all invoices to a single CSV file"""
        
        csv_path = os.path.join(output_dir, f"export_invoices_{timestamp}.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            # French CSV format with semicolon separator
            writer = csv.writer(csvfile, delimiter=';')
            
            # Write headers
            headers = [
                "Nom_Fichier", "Numéro_Facture", "Date", "Date_Échéance",
                "Fournisseur_Nom", "Fournisseur_Adresse", "Fournisseur_SIREN", "Fournisseur_SIRET", "Fournisseur_TVA",
                "Client_Nom", "Client_Adresse", "Client_SIREN",
                "Sous_Total_HT", "Total_TVA", "Total_TTC", "Devise",
                "Articles_Description", "Articles_Quantité", "Articles_Prix_Unitaire", "Articles_Total",
                "Conditions_Paiement"
            ]
            writer.writerow(headers)
            
            # Write data for each invoice
            for item in processed_data:
                invoice_data: InvoiceData = item["data"]
                filename = item["filename"]
                
                # Handle line items - combine all into single strings
                descriptions = []
                quantities = []
                unit_prices = []
                totals = []
                
                if invoice_data.line_items:
                    for line_item in invoice_data.line_items:
                        descriptions.append(line_item.description or "")
                        quantities.append(str(line_item.quantity or 0).replace('.', ','))
                        unit_prices.append(f"{line_item.unit_price or 0:.2f}".replace('.', ','))
                        totals.append(f"{line_item.total or 0:.2f}".replace('.', ','))
                
                # Get vendor and customer info
                vendor_name = invoice_data.vendor.name if invoice_data.vendor else (invoice_data.vendor_name or "")
                vendor_address = invoice_data.vendor.address if invoice_data.vendor else (invoice_data.vendor_address or "")
                vendor_siren = invoice_data.vendor.siren_number if invoice_data.vendor else ""
                vendor_siret = invoice_data.vendor.siret_number if invoice_data.vendor else ""
                vendor_tva = invoice_data.vendor.tva_number if invoice_data.vendor else ""
                
                customer_name = invoice_data.customer.name if invoice_data.customer else (invoice_data.customer_name or "")
                customer_address = invoice_data.customer.address if invoice_data.customer else (invoice_data.customer_address or "")
                customer_siren = invoice_data.customer.siren_number if invoice_data.customer else ""
                
                # Financial totals
                subtotal = invoice_data.subtotal_ht or invoice_data.subtotal or 0
                total_tax = invoice_data.total_tva or invoice_data.tax or 0
                total = invoice_data.total_ttc or invoice_data.total or 0
                
                row = [
                    filename,
                    invoice_data.invoice_number or "",
                    invoice_data.date or "",
                    invoice_data.due_date or "",
                    vendor_name,
                    vendor_address,
                    vendor_siren,
                    vendor_siret,
                    vendor_tva,
                    customer_name,
                    customer_address,
                    customer_siren,
                    f"{subtotal:.2f}".replace('.', ','),
                    f"{total_tax:.2f}".replace('.', ','),
                    f"{total:.2f}".replace('.', ','),
                    invoice_data.currency or "EUR",
                    " | ".join(descriptions),
                    " | ".join(quantities),
                    " | ".join(unit_prices),
                    " | ".join(totals),
                    invoice_data.payment_terms or ""
                ]
                
                writer.writerow(row)
        
        return csv_path
    
    async def _export_to_json(self, processed_data: List[Dict], output_dir: str, timestamp: str) -> str:
        """Export all invoices to a single JSON file"""
        
        json_path = os.path.join(output_dir, f"export_invoices_{timestamp}.json")
        
        export_data = {
            "export_metadata": {
                "export_date": datetime.now().isoformat(),
                "invoice_count": len(processed_data),
                "format": "json"
            },
            "invoices": []
        }
        
        for item in processed_data:
            invoice_data: InvoiceData = item["data"]
            filename = item["filename"]
            
            invoice_json = {
                "filename": filename,
                "invoice_id": item["invoice_id"],
                "numero_facture": invoice_data.invoice_number,
                "date_facture": invoice_data.date,
                "date_echeance": invoice_data.due_date,
                "fournisseur": {
                    "nom": invoice_data.vendor.name if invoice_data.vendor else (invoice_data.vendor_name or ""),
                    "adresse": invoice_data.vendor.address if invoice_data.vendor else (invoice_data.vendor_address or ""),
                    "siren": invoice_data.vendor.siren_number if invoice_data.vendor else "",
                    "siret": invoice_data.vendor.siret_number if invoice_data.vendor else "",
                    "numero_tva": invoice_data.vendor.tva_number if invoice_data.vendor else ""
                },
                "client": {
                    "nom": invoice_data.customer.name if invoice_data.customer else (invoice_data.customer_name or ""),
                    "adresse": invoice_data.customer.address if invoice_data.customer else (invoice_data.customer_address or ""),
                    "siren": invoice_data.customer.siren_number if invoice_data.customer else ""
                },
                "articles": [
                    {
                        "description": item.description,
                        "quantite": item.quantity,
                        "prix_unitaire_ht": item.unit_price,
                        "total_ht": item.total,
                        "taux_tva": item.tva_rate,
                        "montant_tva": item.tva_amount
                    }
                    for item in (invoice_data.line_items or [])
                ],
                "totaux": {
                    "sous_total_ht": invoice_data.subtotal_ht or invoice_data.subtotal,
                    "total_tva": invoice_data.total_tva or invoice_data.tax,
                    "total_ttc": invoice_data.total_ttc or invoice_data.total,
                    "devise": invoice_data.currency or "EUR"
                },
                "conditions_paiement": invoice_data.payment_terms
            }
            
            export_data["invoices"].append(invoice_json)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return json_path
    
    async def _export_to_excel(self, processed_data: List[Dict], output_dir: str, timestamp: str) -> str:
        """Export all invoices to Excel file with multiple sheets"""
        
        excel_path = os.path.join(output_dir, f"export_invoices_{timestamp}.xlsx")
        
        # Create main summary sheet
        summary_data = []
        line_items_data = []
        
        for item in processed_data:
            invoice_data: InvoiceData = item["data"]
            filename = item["filename"]
            
            # Main invoice data
            vendor_name = invoice_data.vendor.name if invoice_data.vendor else (invoice_data.vendor_name or "")
            customer_name = invoice_data.customer.name if invoice_data.customer else (invoice_data.customer_name or "")
            subtotal = invoice_data.subtotal_ht or invoice_data.subtotal or 0
            total_tax = invoice_data.total_tva or invoice_data.tax or 0
            total = invoice_data.total_ttc or invoice_data.total or 0
            
            summary_data.append({
                "Nom_Fichier": filename,
                "Numéro_Facture": invoice_data.invoice_number or "",
                "Date": invoice_data.date or "",
                "Date_Échéance": invoice_data.due_date or "",
                "Fournisseur": vendor_name,
                "Client": customer_name,
                "Sous_Total_HT": subtotal,
                "Total_TVA": total_tax,
                "Total_TTC": total,
                "Devise": invoice_data.currency or "EUR"
            })
            
            # Line items data
            if invoice_data.line_items:
                for idx, line_item in enumerate(invoice_data.line_items):
                    line_items_data.append({
                        "Nom_Fichier": filename,
                        "Numéro_Facture": invoice_data.invoice_number or "",
                        "Article_Numéro": idx + 1,
                        "Description": line_item.description or "",
                        "Quantité": line_item.quantity or 0,
                        "Prix_Unitaire": line_item.unit_price or 0,
                        "Total_HT": line_item.total or 0,
                        "Taux_TVA": line_item.tva_rate or 0,
                        "Montant_TVA": line_item.tva_amount or 0
                    })
        
        # Create Excel file with multiple sheets
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Résumé_Factures', index=False)
            
            # Line items sheet
            if line_items_data:
                items_df = pd.DataFrame(line_items_data)
                items_df.to_excel(writer, sheet_name='Articles_Détail', index=False)
        
        return excel_path
    
    async def _export_to_sage(self, processed_data: List[Dict], output_dir: str, timestamp: str) -> str:
        """Export to Sage PNM format"""
        from api.exports.sage_exporter import export_batch_to_sage_pnm
        
        sage_path = os.path.join(output_dir, f"export_sage_{timestamp}.pnm")
        invoice_data_list = [item["data"] for item in processed_data]
        
        sage_content = export_batch_to_sage_pnm(invoice_data_list)
        
        with open(sage_path, 'w', encoding='utf-8') as f:
            f.write(sage_content)
        
        return sage_path
    
    async def _export_to_ebp(self, processed_data: List[Dict], output_dir: str, timestamp: str) -> str:
        """Export to EBP ASCII format"""
        from api.exports.ebp_exporter import export_batch_to_ebp_ascii
        
        ebp_path = os.path.join(output_dir, f"export_ebp_{timestamp}.txt")
        invoice_data_list = [item["data"] for item in processed_data]
        
        ebp_content = export_batch_to_ebp_ascii(invoice_data_list)
        
        with open(ebp_path, 'w', encoding='utf-8') as f:
            f.write(ebp_content)
        
        return ebp_path
    
    async def _export_to_ciel(self, processed_data: List[Dict], output_dir: str, timestamp: str) -> str:
        """Export to Ciel XIMPORT format"""
        from api.exports.ciel_exporter import export_batch_to_ciel_ximport
        
        ciel_path = os.path.join(output_dir, f"export_ciel_{timestamp}.txt")
        invoice_data_list = [item["data"] for item in processed_data]
        
        ciel_content = export_batch_to_ciel_ximport(invoice_data_list)
        
        with open(ciel_path, 'w', encoding='utf-8') as f:
            f.write(ciel_content)
        
        return ciel_path
    
    async def _export_to_fec(self, processed_data: List[Dict], output_dir: str, timestamp: str) -> str:
        """Export to FEC format"""
        from api.exports.fec_exporter import export_batch_to_fec
        
        fec_path = os.path.join(output_dir, f"export_fec_{timestamp}.txt")
        invoice_data_list = [item["data"] for item in processed_data]
        
        fec_content = export_batch_to_fec(invoice_data_list, "ACH")  # Default journal code
        
        with open(fec_path, 'w', encoding='utf-8') as f:
            f.write(fec_content)
        
        return fec_path
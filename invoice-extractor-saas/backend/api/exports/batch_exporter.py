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
        """Export all invoices to a single CSV file with duplicate prevention"""
        
        # CRITICAL: Deduplicate invoices to prevent accounting errors in CSV export
        try:
            unique_processed_data = []
            seen_business_keys = set()
            duplicate_count = 0
            
            for item in processed_data:
                invoice_data = item["data"]
                
                # Build business key (invoice_number + supplier_siret)
                invoice_number = invoice_data.invoice_number or "SANS_NUMERO"
                supplier_siret = ""
                
                if invoice_data.vendor and invoice_data.vendor.siret_number:
                    supplier_siret = invoice_data.vendor.siret_number
                
                business_key = f"{supplier_siret}_{invoice_number}"
                
                if business_key in seen_business_keys:
                    # Skip duplicate
                    duplicate_count += 1
                    continue
                
                seen_business_keys.add(business_key)
                unique_processed_data.append(item)
            
            # Use deduplicated data
            processed_data = unique_processed_data
            
            # Log deduplication if any duplicates were found
            if duplicate_count > 0:
                print(f"⚠️ CSV Export deduplication: {duplicate_count} duplicate(s) removed from batch")
                
        except Exception as e:
            print(f"Error during CSV export deduplication: {str(e)}")
            # Continue with original data if deduplication fails
        
        csv_path = os.path.join(output_dir, f"export_invoices_{timestamp}.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            # French CSV format with semicolon separator
            writer = csv.writer(csvfile, delimiter=';')
            
            # Simplified MVP CSV headers - French accountant friendly (15 columns max)
            headers = [
                "Numéro_Facture",
                "Date", 
                "Date_Échéance",
                "Fournisseur_Nom",
                "Fournisseur_SIRET",
                "Fournisseur_Adresse",
                "Client_Nom", 
                "Client_SIRET",
                "Montant_HT",
                "Montant_TVA", 
                "Montant_TTC",
                "Taux_TVA_Principal",
                "Conditions_Paiement",
                "Statut_SIRET_Validation",
                "Notes"
            ]
            writer.writerow(headers)
            
            # Write data for each invoice
            for item in processed_data:
                invoice_data: InvoiceData = item["data"]
                filename = item["filename"]
                
                # Extract essential vendor information only
                vendor = invoice_data.vendor
                vendor_name = vendor.name if vendor else (invoice_data.vendor_name or "")
                vendor_siret = vendor.siret_number if vendor else ""
                
                # Build complete vendor address 
                vendor_address_parts = []
                if vendor:
                    if vendor.address:
                        vendor_address_parts.append(vendor.address)
                    if vendor.postal_code and vendor.city:
                        vendor_address_parts.append(f"{vendor.postal_code} {vendor.city}")
                    elif vendor.city:
                        vendor_address_parts.append(vendor.city)
                else:
                    if invoice_data.vendor_address:
                        vendor_address_parts.append(invoice_data.vendor_address)
                
                vendor_address = ", ".join(vendor_address_parts)
                
                # Extract essential customer information only
                customer = invoice_data.customer
                customer_name = customer.name if customer else (invoice_data.customer_name or "")
                customer_siret = customer.siret_number if customer else ""
                
                # Financial totals with French formatting
                subtotal = invoice_data.subtotal_ht or invoice_data.subtotal or 0
                total_tax = invoice_data.total_tva or invoice_data.tax or 0
                total = invoice_data.total_ttc or invoice_data.total or 0
                
                # Determine principal VAT rate (most common rate)
                principal_vat_rate = 0.0
                if invoice_data.tva_breakdown:
                    # Find the TVA rate with highest base amount
                    max_base = 0
                    for tva_item in invoice_data.tva_breakdown:
                        if tva_item.taxable_amount > max_base:
                            max_base = tva_item.taxable_amount
                            principal_vat_rate = tva_item.rate
                
                # SIRET validation status
                siret_validation_status = "Non vérifié"
                if vendor_siret and len(vendor_siret) == 14 and vendor_siret.isdigit():
                    siret_validation_status = "Format valide"
                elif vendor_siret:
                    siret_validation_status = "Format invalide"
                
                # Combine notes (simple approach)
                notes_parts = []
                if invoice_data.notes:
                    notes_parts.append(invoice_data.notes)
                if hasattr(invoice_data, 'order_number') and invoice_data.order_number:
                    notes_parts.append(f"Cmd: {invoice_data.order_number}")
                
                notes = " | ".join(notes_parts) if notes_parts else ""
                
                # Generate simple MVP row (15 columns) - French accountant friendly
                row = [
                    invoice_data.invoice_number or "",                              # Numéro_Facture
                    invoice_data.date or "",                                        # Date
                    invoice_data.due_date or "",                                    # Date_Échéance
                    vendor_name,                                                    # Fournisseur_Nom
                    vendor_siret,                                                   # Fournisseur_SIRET
                    vendor_address,                                                 # Fournisseur_Adresse
                    customer_name,                                                  # Client_Nom
                    customer_siret,                                                 # Client_SIRET
                    f"{subtotal:.2f}".replace('.', ','),                          # Montant_HT
                    f"{total_tax:.2f}".replace('.', ','),                         # Montant_TVA
                    f"{total:.2f}".replace('.', ','),                             # Montant_TTC
                    f"{principal_vat_rate:.1f}%".replace('.', ','),               # Taux_TVA_Principal
                    invoice_data.payment_terms or "",                              # Conditions_Paiement
                    siret_validation_status,                                       # Statut_SIRET_Validation
                    notes                                                          # Notes
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
            
            # Extract complete vendor information
            vendor = invoice_data.vendor
            fournisseur_data = {
                "nom": vendor.name if vendor else (invoice_data.vendor_name or ""),
                "adresse": vendor.address if vendor else (invoice_data.vendor_address or ""),
                "code_postal": vendor.postal_code if vendor else "",
                "ville": vendor.city if vendor else "",
                "pays": vendor.country if vendor else "",
                "siren": vendor.siren_number if vendor else "",
                "siret": vendor.siret_number if vendor else "",
                "numero_tva": vendor.tva_number if vendor else "",
                "code_naf": vendor.naf_code if vendor else "",
                "forme_juridique": vendor.legal_form if vendor else "",
                "capital_social": vendor.share_capital if vendor else None,
                "rcs": vendor.rcs_number if vendor else "",
                "rm": vendor.rm_number if vendor else "",
                "telephone": vendor.phone if vendor else "",
                "email": vendor.email if vendor else ""
            }
            
            # Extract complete customer information
            customer = invoice_data.customer
            client_data = {
                "nom": customer.name if customer else (invoice_data.customer_name or ""),
                "adresse": customer.address if customer else (invoice_data.customer_address or ""),
                "code_postal": customer.postal_code if customer else "",
                "ville": customer.city if customer else "",
                "pays": customer.country if customer else "",
                "siren": customer.siren_number if customer else "",
                "siret": customer.siret_number if customer else "",
                "numero_tva": customer.tva_number if customer else "",
                "code_naf": customer.naf_code if customer else "",
                "forme_juridique": customer.legal_form if customer else "",
                "capital_social": customer.share_capital if customer else None,
                "rcs": customer.rcs_number if customer else "",
                "rm": customer.rm_number if customer else "",
                "telephone": customer.phone if customer else "",
                "email": customer.email if customer else ""
            }
            
            # Complete line items with all available data
            articles_data = []
            for item in (invoice_data.line_items or []):
                articles_data.append({
                    "description": item.description or "",
                    "quantite": item.quantity or 0,
                    "unite": item.unit or "",
                    "prix_unitaire_ht": item.unit_price or 0,
                    "total_ht": item.total or 0,
                    "taux_tva": item.tva_rate or 0,
                    "montant_tva": item.tva_amount or 0
                })
            
            # Complete TVA breakdown by rates
            tva_breakdown_data = []
            for tva_item in (invoice_data.tva_breakdown or []):
                tva_breakdown_data.append({
                    "taux": tva_item.rate,
                    "base_imposable": tva_item.taxable_amount,
                    "montant_tva": tva_item.tva_amount,
                    "taux_francais": getattr(tva_item, 'is_french_rate', None)
                })
            
            # Financial totals
            subtotal = invoice_data.subtotal_ht or invoice_data.subtotal or 0
            total_tax = invoice_data.total_tva or invoice_data.tax or 0
            total = invoice_data.total_ttc or invoice_data.total or 0
            
            # Convert to exact JSON structure matching user's specification
            invoice_json = {
                "filename": filename,
                "invoice_id": item["invoice_id"],
                "invoice_number": invoice_data.invoice_number or "",
                "invoice_date": invoice_data.date or "",
                "due_date": invoice_data.due_date or "",
                
                "supplier": {
                    "name": fournisseur_data["nom"],
                    "siret": fournisseur_data["siret"],
                    "siren": fournisseur_data["siren"],
                    "address": fournisseur_data["adresse"],
                    "postal_code": fournisseur_data["code_postal"],
                    "city": fournisseur_data["ville"],
                    "vat_number": fournisseur_data["numero_tva"],
                    "naf_code": fournisseur_data["code_naf"],
                    "legal_form": fournisseur_data["forme_juridique"],
                    "share_capital": fournisseur_data["capital_social"],
                    "rcs_number": fournisseur_data["rcs"],
                    "rm_number": fournisseur_data["rm"],
                    "phone": fournisseur_data["telephone"],
                    "email": fournisseur_data["email"]
                },
                
                "customer": {
                    "name": client_data["nom"],
                    "siret": client_data["siret"],
                    "siren": client_data["siren"],
                    "address": client_data["adresse"],
                    "postal_code": client_data["code_postal"],
                    "city": client_data["ville"],
                    "vat_number": client_data["numero_tva"],
                    "naf_code": client_data["code_naf"],
                    "legal_form": client_data["forme_juridique"],
                    "share_capital": client_data["capital_social"],
                    "rcs_number": client_data["rcs"],
                    "rm_number": client_data["rm"],
                    "phone": client_data["telephone"],
                    "email": client_data["email"]
                },
                
                "amounts": {
                    "total_ht": subtotal,
                    "total_vat": total_tax,
                    "total_ttc": total,
                    "vat_breakdown": {}
                },
                
                "line_items": [
                    {
                        "description": item["description"],
                        "quantity": item["quantite"],
                        "unit": item["unite"],
                        "unit_price": item["prix_unitaire_ht"],
                        "vat_rate": f"{item['taux_tva']:.1f}%",
                        "amount_ht": item["total_ht"],
                        "vat_amount": item["montant_tva"],
                        "amount_ttc": item["total_ht"] + item["montant_tva"]
                    }
                    for item in articles_data
                ],
                
                # 🟡 IMPORTANT - Payment Information
                "payment_terms": invoice_data.payment_terms or "",
                "payment_method": getattr(invoice_data, 'payment_method', '') or "",
                "bank_details": getattr(invoice_data, 'bank_details', '') or "",
                "discount_amount": getattr(invoice_data, 'discount_amount', 0) or 0,
                "deposit_amount": getattr(invoice_data, 'deposit_amount', 0) or 0,
                "shipping_cost": getattr(invoice_data, 'shipping_cost', 0) or 0,
                "packaging_cost": getattr(invoice_data, 'packaging_cost', 0) or 0,
                "other_charges": getattr(invoice_data, 'other_charges', 0) or 0,
                
                # 🟢 OPTIONAL - Business Context
                "order_number": getattr(invoice_data, 'order_number', '') or "",
                "delivery_date": invoice_data.delivery_date or "",
                "project_reference": getattr(invoice_data, 'project_reference', '') or "",
                "contract_number": getattr(invoice_data, 'contract_number', '') or "",
                "delivery_address": invoice_data.delivery_address or "",
                "notes": invoice_data.notes or "",
                
                # 🟢 OPTIONAL - Tax Specifics
                "auto_entrepreneur_mention": getattr(invoice_data, 'auto_entrepreneur_mention', '') or "",
                "vat_exemption_reason": getattr(invoice_data, 'vat_exemption_reason', '') or "",
                "reverse_charge_mention": getattr(invoice_data, 'reverse_charge_mention', '') or "",
                
                # Legal mentions
                "late_payment_penalty": invoice_data.late_payment_penalties or "",
                "recovery_indemnity": invoice_data.recovery_fees or "",
                
                # Compliance
                "is_french_compliant": invoice_data.is_french_compliant or False
            }
            
            # Add VAT breakdown to amounts section
            if tva_breakdown_data:
                for tva_item in tva_breakdown_data:
                    rate_key = f"{tva_item['taux']:.1f}%"
                    invoice_json["amounts"]["vat_breakdown"][rate_key] = {
                        "base": tva_item["base_imposable"],
                        "vat": tva_item["montant_tva"]
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
        """Export to Sage PNM format with duplicate prevention (CRITICAL for accounting)"""
        from api.exports.sage_exporter import export_batch_to_sage_pnm
        
        # CRITICAL: Deduplicate invoices to prevent Sage PNM accounting errors
        try:
            unique_processed_data = []
            seen_business_keys = set()
            duplicate_count = 0
            
            for item in processed_data:
                invoice_data = item["data"]
                
                # Build business key (invoice_number + supplier_siret)
                invoice_number = invoice_data.invoice_number or "SANS_NUMERO"
                supplier_siret = ""
                
                if invoice_data.vendor and invoice_data.vendor.siret_number:
                    supplier_siret = invoice_data.vendor.siret_number
                
                business_key = f"{supplier_siret}_{invoice_number}"
                
                if business_key in seen_business_keys:
                    # Skip duplicate - CRITICAL for Sage accounting integrity
                    duplicate_count += 1
                    print(f"⚠️ SAGE PNM: Removed duplicate invoice {invoice_number} from {invoice_data.vendor.name if invoice_data.vendor else 'Unknown supplier'}")
                    continue
                
                seen_business_keys.add(business_key)
                unique_processed_data.append(item)
            
            # Use deduplicated data
            processed_data = unique_processed_data
            
            # Log deduplication - especially important for Sage PNM
            if duplicate_count > 0:
                print(f"🚨 SAGE PNM Export deduplication: {duplicate_count} duplicate(s) removed to prevent accounting errors!")
                
        except Exception as e:
            print(f"Error during Sage PNM export deduplication: {str(e)}")
            # Continue with original data if deduplication fails - better than no export
        
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
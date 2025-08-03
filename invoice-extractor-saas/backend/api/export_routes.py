from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import json
import csv
import io
import zipfile
import uuid
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import get_current_user
from models.user import User
from core.database import get_db
from crud.invoice import get_invoice_by_id, get_extracted_data
from schemas.invoice import InvoiceData, FrenchBusinessInfo, FrenchTVABreakdown, LineItem
from api.exports.sage_exporter import export_to_sage_pnm, export_batch_to_sage_pnm
from api.exports.ebp_exporter import export_to_ebp_ascii, export_batch_to_ebp_ascii
from api.exports.ciel_exporter import export_to_ciel_ximport, export_batch_to_ciel_ximport
from api.exports.fec_exporter import export_to_fec, export_batch_to_fec

router = APIRouter()

logger = logging.getLogger(__name__)


async def get_real_invoice_data(invoice_id: str, user_id: uuid.UUID, db: AsyncSession, require_approved: bool = False) -> InvoiceData:
    """Get real invoice data from database"""
    try:
        # Get invoice from database
        invoice = await get_invoice_by_id(db=db, invoice_id=uuid.UUID(invoice_id), user_id=user_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Check if invoice is approved (for export from review workflow)
        if require_approved and invoice.review_status != "approved":
            raise HTTPException(
                status_code=400, 
                detail=f"Invoice must be approved before export. Current status: {invoice.review_status or 'pending_review'}"
            )
        
        # Get extracted data
        extracted_data_dict = await get_extracted_data(db=db, invoice_id=invoice.id, user_id=user_id)
        if not extracted_data_dict:
            raise HTTPException(status_code=404, detail="Invoice data not found")
        
        # Handle both old format (wrapped in "invoice_data") and new format (direct)
        if "invoice_data" in extracted_data_dict:
            invoice_data_dict = extracted_data_dict["invoice_data"]
        else:
            invoice_data_dict = extracted_data_dict
        
        # Convert back to InvoiceData object
        try:
            invoice_data = InvoiceData(**invoice_data_dict)
            return invoice_data
        except Exception as validation_error:
            # Log the validation error for debugging
            logger.error(f"InvoiceData validation failed for invoice {invoice_id}: {str(validation_error)}")
            logger.error(f"Invoice data dict keys: {list(invoice_data_dict.keys()) if isinstance(invoice_data_dict, dict) else 'Not a dict'}")
            raise HTTPException(status_code=500, detail=f"Invoice data validation failed: {str(validation_error)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get invoice data: {str(e)}")


# Mock function to get invoice data (replace with actual database query)
def get_mock_french_invoice(invoice_id: str) -> InvoiceData:
    """Generate mock French invoice data for testing"""
    
    vendor = FrenchBusinessInfo(
        name="Entreprise Française SARL",
        address="123 Rue de la République",
        postal_code="75001",
        city="Paris",
        country="France",
        siren_number="123456789",
        siret_number="12345678900123",
        tva_number="FR12345678901",
        naf_code="6201A",
        legal_form="SARL",
        share_capital=10000.0,
        phone="01 23 45 67 89",
        email="contact@entreprise.fr"
    )
    
    customer = FrenchBusinessInfo(
        name="Client Expert-Comptable SAS",
        address="456 Avenue des Champs",
        postal_code="69000",
        city="Lyon",
        country="France",
        siren_number="987654321",
        siret_number="98765432100456"
    )
    
    line_items = [
        LineItem(
            description="Prestation de conseil",
            quantity=1.0,
            unit="service",
            unit_price=1000.0,
            total=1000.0,
            tva_rate=20.0,
            tva_amount=200.0
        ),
        LineItem(
            description="Formation comptable",
            quantity=2.0,
            unit="jour",
            unit_price=500.0,
            total=1000.0,
            tva_rate=20.0,
            tva_amount=200.0
        )
    ]
    
    tva_breakdown = [
        FrenchTVABreakdown(
            rate=20.0,
            taxable_amount=2000.0,
            tva_amount=400.0
        )
    ]
    
    return InvoiceData(
        invoice_number=f"FACT-2024-{invoice_id}",
        date="2024-01-15",
        due_date="2024-02-15",
        vendor=vendor,
        customer=customer,
        line_items=line_items,
        subtotal_ht=2000.0,
        tva_breakdown=tva_breakdown,
        total_tva=400.0,
        total_ttc=2400.0,
        currency="EUR",
        payment_terms="Paiement à 30 jours",
        late_payment_penalties="En cas de retard de paiement, des pénalités de retard seront appliquées au taux de 3 fois le taux d'intérêt légal.",
        recovery_fees="Une indemnité forfaitaire de 40 euros pour frais de recouvrement sera exigible en cas de retard de paiement.",
        is_french_compliant=True
    )


@router.get("/{invoice_id}/csv")
async def export_csv(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export invoice as CSV matching exact French field specification"""
    
    # Get real invoice from database
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db)
    
    # Create French-formatted CSV using the same structure as batch exporter
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')  # French CSV uses semicolon
    
    # Complete CSV headers - All required fields for French accountants
    headers = [
        "Numéro_Facture",
        "Date_Émission", 
        "Date_Échéance",
        "Montant_HT",
        "Montant_TVA", 
        "Montant_TTC",
        "Fournisseur_Nom",
        "Fournisseur_SIRET",
        "Fournisseur_SIREN",
        "Fournisseur_TVA",
        "Fournisseur_Adresse",
        "Fournisseur_IBAN",
        "Client_Nom", 
        "Client_SIRET",
        "Client_SIREN",
        "Client_TVA",
        "Client_Adresse",
        "Désignation_Lignes",
        "Quantité_Total",
        "Prix_Unitaire_Moyen",
        "TVA_Par_Ligne",
        "Moyen_Paiement",
        "Conditions_Paiement",
        "Numéro_Commande",
        "Numéro_Contrat",
        "Référence_Projet",
        "Date_Livraison",
        "Adresse_Livraison",
        "Notes"
    ]
    writer.writerow(headers)
    
    # Complete data extraction - all required fields
    vendor = invoice_data.vendor
    customer = invoice_data.customer
    
    # Vendor information
    vendor_name = vendor.name if vendor else (invoice_data.vendor_name or "")
    vendor_siret = vendor.siret_number if vendor else ""
    vendor_siren = vendor.siren_number if vendor else ""
    vendor_tva = vendor.tva_number if vendor else ""
    vendor_iban = invoice_data.bank_details or ""
    
    # Build complete vendor address 
    vendor_address_parts = []
    if vendor:
        if vendor.address:
            vendor_address_parts.append(vendor.address)
        if vendor.postal_code and vendor.city:
            vendor_address_parts.append(f"{vendor.postal_code} {vendor.city}")
        elif vendor.city:
            vendor_address_parts.append(vendor.city)
        if vendor.country and vendor.country != "France":
            vendor_address_parts.append(vendor.country)
    else:
        if invoice_data.vendor_address:
            vendor_address_parts.append(invoice_data.vendor_address)
    vendor_address = ", ".join(vendor_address_parts)
    
    # Customer information
    customer_name = customer.name if customer else (invoice_data.customer_name or "")
    customer_siret = customer.siret_number if customer else ""
    customer_siren = customer.siren_number if customer else ""
    customer_tva = customer.tva_number if customer else ""
    
    # Build complete customer address
    customer_address_parts = []
    if customer:
        if customer.address:
            customer_address_parts.append(customer.address)
        if customer.postal_code and customer.city:
            customer_address_parts.append(f"{customer.postal_code} {customer.city}")
        elif customer.city:
            customer_address_parts.append(customer.city)
        if customer.country and customer.country != "France":
            customer_address_parts.append(customer.country)
    else:
        if invoice_data.customer_address:
            customer_address_parts.append(invoice_data.customer_address)
    customer_address = ", ".join(customer_address_parts)
    
    # Financial totals with French formatting
    subtotal = invoice_data.subtotal_ht or invoice_data.subtotal or 0
    total_tax = invoice_data.total_tva or invoice_data.tax or 0
    total = invoice_data.total_ttc or invoice_data.total or 0
    
    # Line items aggregation
    line_items = invoice_data.line_items or []
    total_quantity = sum(item.quantity or 0 for item in line_items)
    
    # Calculate average unit price (weighted by quantity)
    total_value = sum((item.quantity or 0) * (item.unit_price or 0) for item in line_items)
    avg_unit_price = total_value / total_quantity if total_quantity > 0 else 0
    
    # Line descriptions (concatenated)
    line_descriptions = []
    for item in line_items:
        if item.description:
            line_descriptions.append(item.description)
    designation_lines = " | ".join(line_descriptions) if line_descriptions else ""
    
    # VAT per line (concatenated rates)
    vat_rates = []
    for item in line_items:
        if item.tva_rate is not None:
            vat_rates.append(f"{item.tva_rate:.1f}%")
    tva_par_ligne = " | ".join(set(vat_rates)) if vat_rates else ""  # Remove duplicates
    
    # Payment information
    payment_method = invoice_data.payment_method or ""
    payment_terms = invoice_data.payment_terms or ""
    
    # Generate complete row with all required fields
    row = [
        invoice_data.invoice_number or "",                              # Numéro_Facture
        invoice_data.date or "",                                        # Date_Émission
        invoice_data.due_date or "",                                    # Date_Échéance
        f"{subtotal:.2f}".replace('.', ','),                          # Montant_HT
        f"{total_tax:.2f}".replace('.', ','),                         # Montant_TVA
        f"{total:.2f}".replace('.', ','),                             # Montant_TTC
        vendor_name,                                                    # Fournisseur_Nom
        vendor_siret,                                                   # Fournisseur_SIRET
        vendor_siren,                                                   # Fournisseur_SIREN
        vendor_tva,                                                     # Fournisseur_TVA
        vendor_address,                                                 # Fournisseur_Adresse
        vendor_iban,                                                    # Fournisseur_IBAN
        customer_name,                                                  # Client_Nom
        customer_siret,                                                 # Client_SIRET
        customer_siren,                                                 # Client_SIREN
        customer_tva,                                                   # Client_TVA
        customer_address,                                               # Client_Adresse
        designation_lines,                                              # Désignation_Lignes
        f"{total_quantity:.2f}".replace('.', ','),                    # Quantité_Total
        f"{avg_unit_price:.2f}".replace('.', ','),                    # Prix_Unitaire_Moyen
        tva_par_ligne,                                                  # TVA_Par_Ligne
        payment_method,                                                 # Moyen_Paiement
        payment_terms,                                                  # Conditions_Paiement
        invoice_data.order_number or "",                                # Numéro_Commande
        invoice_data.contract_number or "",                             # Numéro_Contrat
        invoice_data.project_reference or "",                           # Référence_Projet
        invoice_data.delivery_date or "",                               # Date_Livraison
        invoice_data.delivery_address or "",                            # Adresse_Livraison
        invoice_data.notes or ""                                        # Notes
    ]
    
    writer.writerow(row)
    
    # Return as download
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{invoice_id}.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


@router.get("/{invoice_id}/json")
async def export_json(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export invoice as JSON with French structure"""
    
    # Get real invoice from database
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db)
    
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
    json_data = {
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
            json_data["amounts"]["vat_breakdown"][rate_key] = {
                "base": tva_item["base_imposable"],
                "vat": tva_item["montant_tva"]
            }
    
    # Return as download
    return StreamingResponse(
        io.BytesIO(json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')),
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{invoice_id}.json",
            "Content-Type": "application/json; charset=utf-8"
        }
    )


# French accounting software exports

@router.get("/{invoice_id}/sage")
async def export_sage(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export invoice to Sage PNM format"""
    
    # Get real invoice from database
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db)
    
    # Export to Sage PNM format
    sage_content = export_to_sage_pnm(invoice_data)
    
    return StreamingResponse(
        io.BytesIO(sage_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{invoice_id}_sage.pnm",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )


@router.get("/{invoice_id}/ebp")
async def export_ebp(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export invoice to EBP ASCII format"""
    
    # Get real invoice from database
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db)
    
    # Export to EBP ASCII format
    ebp_content = export_to_ebp_ascii(invoice_data)
    
    return StreamingResponse(
        io.BytesIO(ebp_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{invoice_id}_ebp.txt",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )


@router.get("/{invoice_id}/ciel")
async def export_ciel(
    invoice_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export invoice to Ciel XIMPORT format"""
    
    # Get real invoice from database
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db)
    
    # Export to Ciel XIMPORT format
    ciel_content = export_to_ciel_ximport(invoice_data)
    
    return StreamingResponse(
        io.BytesIO(ciel_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{invoice_id}_ciel.txt",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )


@router.get("/{invoice_id}/fec")
async def export_fec(
    invoice_id: str,
    journal_code: str = Query("ACH", description="Code journal (ACH, VTE, etc.)"),
    sequence_number: int = Query(1, description="Numéro séquentiel FEC"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export invoice to FEC format for French tax administration"""
    
    # Get real invoice from database
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db)
    
    # Export to FEC format
    fec_content = export_to_fec(invoice_data, journal_code, sequence_number)
    
    return StreamingResponse(
        io.BytesIO(fec_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{invoice_id}_fec.txt",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )


# Batch export endpoints

@router.post("/batch")
async def export_batch(
    invoice_ids: List[str],
    format: str = Query("csv", description="Format d'export: csv, json, sage, ebp, ciel, fec"),
    journal_code: str = Query("ACH", description="Code journal pour FEC"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export multiple invoices in specified format"""
    
    valid_formats = ["csv", "json", "sage", "ebp", "ciel", "fec"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Format invalide. Formats supportés: {', '.join(valid_formats)}"
        )
    
    # Get multiple invoices from database
    invoices = [await get_real_invoice_data(invoice_id, current_user.id, db) for invoice_id in invoice_ids]
    
    # CRITICAL: Deduplicate invoices to prevent accounting errors
    try:
        from core.duplicate_detector import DuplicateDetector
        duplicate_detector = DuplicateDetector(db)
        
        # Ensure no duplicate invoices in export batch
        unique_invoices, duplicate_warnings = await duplicate_detector.ensure_unique_invoices_for_export(
            invoices, current_user.id
        )
        
        # Log deduplication if any duplicates were found
        if duplicate_warnings:
            logger.warning(f"Export deduplication: {len(duplicate_warnings)} duplicates removed from batch")
            for warning in duplicate_warnings:
                logger.warning(f"Export duplicate: {warning}")
        
        # Use deduplicated invoices for export
        invoices = unique_invoices
        
        # If no invoices remain after deduplication, return error
        if not invoices:
            raise HTTPException(
                status_code=400,
                detail="❌ Aucune facture unique à exporter après déduplication. Toutes les factures sélectionnées sont des doublons."
            )
        
        logger.info(f"Export proceeding with {len(invoices)} unique invoices")
        
    except Exception as e:
        logger.error(f"Error during export deduplication: {str(e)}")
        # Continue with original invoices if deduplication fails to avoid blocking exports
        logger.warning("Proceeding with original invoice list due to deduplication error")
    
    # After successful export, reset the review status of exported invoices
    # This prevents accumulation of approved invoices
    try:
        from crud.invoice import reset_invoice_review_status
        for invoice_id in invoice_ids:
            await reset_invoice_review_status(db, uuid.UUID(invoice_id), current_user.id)
        await db.commit()
        logger.info(f"Reset review status for {len(invoice_ids)} exported invoices")
    except Exception as e:
        logger.warning(f"Failed to reset invoice review status after export: {str(e)}")
        # Don't fail the export if status reset fails
    
    # Handle accounting software formats that produce single files
    if format == "sage":
        batch_content = export_batch_to_sage_pnm(invoices)
        return StreamingResponse(
            io.BytesIO(batch_content.encode('utf-8')),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=export_sage_{datetime.now().strftime('%Y%m%d')}.pnm",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    elif format == "ebp":
        batch_content = export_batch_to_ebp_ascii(invoices)
        return StreamingResponse(
            io.BytesIO(batch_content.encode('utf-8')),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=export_ebp_{datetime.now().strftime('%Y%m%d')}.txt",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    elif format == "ciel":
        batch_content = export_batch_to_ciel_ximport(invoices)
        return StreamingResponse(
            io.BytesIO(batch_content.encode('utf-8')),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=export_ciel_{datetime.now().strftime('%Y%m%d')}.txt",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    elif format == "fec":
        batch_content = export_batch_to_fec(invoices, journal_code)
        return StreamingResponse(
            io.BytesIO(batch_content.encode('utf-8')),
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=export_fec_{datetime.now().strftime('%Y%m%d')}.txt",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
    elif format == "csv":
        # Generate complete CSV file with all invoices - All required fields
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        
        # Complete CSV headers - All required fields for French accountants
        headers = [
            "Numéro_Facture",
            "Date_Émission", 
            "Date_Échéance",
            "Montant_HT",
            "Montant_TVA", 
            "Montant_TTC",
            "Fournisseur_Nom",
            "Fournisseur_SIRET",
            "Fournisseur_SIREN",
            "Fournisseur_TVA",
            "Fournisseur_Adresse",
            "Fournisseur_IBAN",
            "Client_Nom", 
            "Client_SIRET",
            "Client_SIREN",
            "Client_TVA",
            "Client_Adresse",
            "Désignation_Lignes",
            "Quantité_Total",
            "Prix_Unitaire_Moyen",
            "TVA_Par_Ligne",
            "Moyen_Paiement",
            "Conditions_Paiement",
            "Numéro_Commande",
            "Numéro_Contrat",
            "Référence_Projet",
            "Date_Livraison",
            "Adresse_Livraison",
            "Notes"
        ]
        writer.writerow(headers)
        
        # Write data for each invoice - complete format
        for invoice in invoices:
            vendor = invoice.vendor
            customer = invoice.customer
            
            # Vendor information
            vendor_name = vendor.name if vendor else (invoice.vendor_name or "")
            vendor_siret = vendor.siret_number if vendor else ""
            vendor_siren = vendor.siren_number if vendor else ""
            vendor_tva = vendor.tva_number if vendor else ""
            vendor_iban = invoice.bank_details or ""
            
            # Build complete vendor address 
            vendor_address_parts = []
            if vendor:
                if vendor.address:
                    vendor_address_parts.append(vendor.address)
                if vendor.postal_code and vendor.city:
                    vendor_address_parts.append(f"{vendor.postal_code} {vendor.city}")
                elif vendor.city:
                    vendor_address_parts.append(vendor.city)
                if vendor.country and vendor.country != "France":
                    vendor_address_parts.append(vendor.country)
            else:
                if invoice.vendor_address:
                    vendor_address_parts.append(invoice.vendor_address)
            vendor_address = ", ".join(vendor_address_parts)
            
            # Customer information
            customer_name = customer.name if customer else (invoice.customer_name or "")
            customer_siret = customer.siret_number if customer else ""
            customer_siren = customer.siren_number if customer else ""
            customer_tva = customer.tva_number if customer else ""
            
            # Build complete customer address
            customer_address_parts = []
            if customer:
                if customer.address:
                    customer_address_parts.append(customer.address)
                if customer.postal_code and customer.city:
                    customer_address_parts.append(f"{customer.postal_code} {customer.city}")
                elif customer.city:
                    customer_address_parts.append(customer.city)
                if customer.country and customer.country != "France":
                    customer_address_parts.append(customer.country)
            else:
                if invoice.customer_address:
                    customer_address_parts.append(invoice.customer_address)
            customer_address = ", ".join(customer_address_parts)
            
            # Financial totals with French formatting
            subtotal = invoice.subtotal_ht or invoice.subtotal or 0
            total_tax = invoice.total_tva or invoice.tax or 0
            total = invoice.total_ttc or invoice.total or 0
            
            # Line items aggregation
            line_items = invoice.line_items or []
            total_quantity = sum(item.quantity or 0 for item in line_items)
            
            # Calculate average unit price (weighted by quantity)
            total_value = sum((item.quantity or 0) * (item.unit_price or 0) for item in line_items)
            avg_unit_price = total_value / total_quantity if total_quantity > 0 else 0
            
            # Line descriptions (concatenated)
            line_descriptions = []
            for item in line_items:
                if item.description:
                    line_descriptions.append(item.description)
            designation_lines = " | ".join(line_descriptions) if line_descriptions else ""
            
            # VAT per line (concatenated rates)
            vat_rates = []
            for item in line_items:
                if item.tva_rate is not None:
                    vat_rates.append(f"{item.tva_rate:.1f}%")
            tva_par_ligne = " | ".join(set(vat_rates)) if vat_rates else ""  # Remove duplicates
            
            # Payment information
            payment_method = invoice.payment_method or ""
            payment_terms = invoice.payment_terms or ""
            
            # Generate complete row with all required fields
            row = [
                invoice.invoice_number or "",                              # Numéro_Facture
                invoice.date or "",                                        # Date_Émission
                invoice.due_date or "",                                    # Date_Échéance
                f"{subtotal:.2f}".replace('.', ','),                      # Montant_HT
                f"{total_tax:.2f}".replace('.', ','),                     # Montant_TVA
                f"{total:.2f}".replace('.', ','),                         # Montant_TTC
                vendor_name,                                               # Fournisseur_Nom
                vendor_siret,                                              # Fournisseur_SIRET
                vendor_siren,                                              # Fournisseur_SIREN
                vendor_tva,                                                # Fournisseur_TVA
                vendor_address,                                            # Fournisseur_Adresse
                vendor_iban,                                               # Fournisseur_IBAN
                customer_name,                                             # Client_Nom
                customer_siret,                                            # Client_SIRET
                customer_siren,                                            # Client_SIREN
                customer_tva,                                              # Client_TVA
                customer_address,                                          # Client_Adresse
                designation_lines,                                         # Désignation_Lignes
                f"{total_quantity:.2f}".replace('.', ','),               # Quantité_Total
                f"{avg_unit_price:.2f}".replace('.', ','),               # Prix_Unitaire_Moyen
                tva_par_ligne,                                             # TVA_Par_Ligne
                payment_method,                                            # Moyen_Paiement
                payment_terms,                                             # Conditions_Paiement
                invoice.order_number or "",                                # Numéro_Commande
                invoice.contract_number or "",                             # Numéro_Contrat
                invoice.project_reference or "",                           # Référence_Projet
                invoice.delivery_date or "",                               # Date_Livraison
                invoice.delivery_address or "",                            # Adresse_Livraison
                invoice.notes or ""                                        # Notes
            ]
            
            writer.writerow(row)
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=export_factures_{datetime.now().strftime('%Y%m%d')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    
    elif format == "json":
        # Generate single JSON file with all invoices
        invoices_data = []
        for i, invoice in enumerate(invoices):
            invoice_json = {
                "numero_facture": invoice.invoice_number,
                "date_facture": invoice.date,
                "date_echeance": invoice.due_date,
                "fournisseur": {
                    "nom": invoice.vendor.name if invoice.vendor else (invoice.vendor_name or None),
                    "siret": invoice.vendor.siret_number if invoice.vendor else None,
                    "tva": invoice.vendor.tva_number if invoice.vendor else None,
                } if invoice.vendor else {
                    "nom": invoice.vendor_name or None,
                    "siret": None,
                    "tva": None,
                },
                "client": {
                    "nom": invoice.customer.name if invoice.customer else (invoice.customer_name or None),
                    "siret": invoice.customer.siret_number if invoice.customer else None,
                    "tva": invoice.customer.tva_number if invoice.customer else None,
                } if invoice.customer else {
                    "nom": invoice.customer_name or None,
                    "siret": None,
                    "tva": None,
                },
                "totaux": {
                    "sous_total_ht": invoice.subtotal_ht or invoice.subtotal or 0,
                    "total_tva": invoice.total_tva or invoice.tax or 0,
                    "total_ttc": invoice.total_ttc or invoice.total or 0,
                    "devise": invoice.currency or "EUR"
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
                    for item in (invoice.line_items or [])
                ]
            }
            invoices_data.append(invoice_json)
        
        json_content = {
            "export_date": datetime.now().isoformat(),
            "nombre_factures": len(invoices_data),
            "factures": invoices_data
        }
        
        return StreamingResponse(
            io.BytesIO(json.dumps(json_content, indent=2, ensure_ascii=False).encode('utf-8')),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": f"attachment; filename=export_factures_{datetime.now().strftime('%Y%m%d')}.json",
                "Content-Type": "application/json; charset=utf-8"
            }
        )
    
    # If we get here, it's an unsupported format (should not happen due to validation)
    raise HTTPException(status_code=400, detail=f"Format non supporté: {format}")


@router.get("/formats")
async def get_export_formats(
    current_user: User = Depends(get_current_user)
):
    """Get available export formats for French accounting"""
    
    return {
        "formats": [
            {
                "id": "csv",
                "name": "CSV Français",
                "description": "Format CSV complet avec 23 champs incluant SIRET, SIREN, TVA, IBAN et détails lignes",
                "extension": ".csv",
                "accounting_software": ["Excel", "LibreOffice Calc"]
            },
            {
                "id": "json", 
                "name": "JSON Structuré",
                "description": "Format JSON avec terminologie française",
                "extension": ".json",
                "accounting_software": ["API", "Applications personnalisées"]
            },
            {
                "id": "sage",
                "name": "Sage PNM",
                "description": "Format PNM pour logiciels Sage",
                "extension": ".pnm",
                "accounting_software": ["Sage i7", "Sage 100", "Sage Ligne 100"]
            },
            {
                "id": "ebp",
                "name": "EBP ASCII",
                "description": "Format ASCII fixe pour logiciels EBP",
                "extension": ".txt",
                "accounting_software": ["EBP Comptabilité", "EBP Open Line", "EBP Pro"]
            },
            {
                "id": "ciel",
                "name": "Ciel XIMPORT",
                "description": "Format XIMPORT pour logiciels Ciel",
                "extension": ".txt",
                "accounting_software": ["Ciel Comptabilité", "Ciel Compta Evolution"]
            },
            {
                "id": "fec",
                "name": "FEC (Fichier des Écritures Comptables)",
                "description": "Format obligatoire pour l'administration fiscale française",
                "extension": ".txt",
                "accounting_software": ["Contrôle fiscal", "Audit comptable", "DGFiP"]
            }
        ],
        "french_compliance": {
            "tva_rates": [0.0, 2.1, 5.5, 10.0, 20.0],
            "mandatory_fields": [
                "SIREN/SIRET",
                "Numéro TVA français",
                "Adresses complètes",
                "Clauses de pénalités de retard",
                "Indemnité forfaitaire 40€"
            ],
            "supported_formats": [
                "Dates françaises (DD/MM/YYYY)",
                "Montants avec virgule décimale",
                "Codes NAF/APE",
                "Plan comptable général français"
            ]
        }
    }


# Approved invoice export endpoints (for review workflow)

@router.get("/approved/{invoice_id}/{format}")
async def export_approved_invoice(
    invoice_id: str,
    format: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export approved invoice in specified format (only for reviewed/approved invoices)"""
    
    valid_formats = ["csv", "json", "sage", "ebp", "ciel", "fec"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Format invalide. Formats supportés: {', '.join(valid_formats)}"
        )
    
    # Get invoice data (must be approved)
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db, require_approved=True)
    
    # Generate export based on format
    if format == "csv":
        return await export_csv_content(invoice_data, invoice_id)
    elif format == "json":
        return await export_json_content(invoice_data, invoice_id)
    elif format == "sage":
        return await export_sage_content(invoice_data, invoice_id)
    elif format == "ebp":
        return await export_ebp_content(invoice_data, invoice_id)
    elif format == "ciel":
        return await export_ciel_content(invoice_data, invoice_id)
    elif format == "fec":
        return await export_fec_content(invoice_data, invoice_id)


async def export_csv_content(invoice_data: InvoiceData, invoice_id: str):
    """Generate CSV export content"""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Write headers
    writer.writerow(["Champ", "Valeur"])
    
    # Basic information
    writer.writerow(["Numéro de facture", invoice_data.invoice_number or ""])
    writer.writerow(["Date", invoice_data.date or ""])
    writer.writerow(["Date d'échéance", invoice_data.due_date or ""])
    
    # Vendor information
    if invoice_data.vendor:
        writer.writerow(["Fournisseur - Nom", invoice_data.vendor.name or ""])
        writer.writerow(["Fournisseur - SIRET", invoice_data.vendor.siret_number or ""])
        writer.writerow(["Fournisseur - TVA", invoice_data.vendor.tva_number or ""])
    
    # Financial totals
    subtotal = invoice_data.subtotal_ht or invoice_data.subtotal or 0
    total_tax = invoice_data.total_tva or invoice_data.tax or 0
    total = invoice_data.total_ttc or invoice_data.total or 0
    
    writer.writerow(["Sous-total HT", f"{subtotal:.2f}".replace('.', ',')])
    writer.writerow(["Total TVA", f"{total_tax:.2f}".replace('.', ',')])
    writer.writerow(["Total TTC", f"{total:.2f}".replace('.', ',')])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_approuvee_{invoice_id}.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


async def export_json_content(invoice_data: InvoiceData, invoice_id: str):
    """Generate JSON export content"""
    json_data = {
        "numero_facture": invoice_data.invoice_number,
        "date_facture": invoice_data.date,
        "statut": "approuve",
        "fournisseur": {
            "nom": invoice_data.vendor.name if invoice_data.vendor else None,
            "siret": invoice_data.vendor.siret_number if invoice_data.vendor else None,
            "tva": invoice_data.vendor.tva_number if invoice_data.vendor else None,
        },
        "totaux": {
            "sous_total_ht": invoice_data.subtotal_ht,
            "total_tva": invoice_data.total_tva,
            "total_ttc": invoice_data.total_ttc,
        },
        "conformite_francaise": invoice_data.is_french_compliant
    }
    
    return StreamingResponse(
        io.BytesIO(json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')),
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_approuvee_{invoice_id}.json",
        }
    )


async def export_sage_content(invoice_data: InvoiceData, invoice_id: str):
    """Generate Sage export content"""
    sage_content = export_to_sage_pnm(invoice_data)
    return StreamingResponse(
        io.BytesIO(sage_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_approuvee_{invoice_id}_sage.pnm",
        }
    )


async def export_ebp_content(invoice_data: InvoiceData, invoice_id: str):
    """Generate EBP export content"""
    ebp_content = export_to_ebp_ascii(invoice_data)
    return StreamingResponse(
        io.BytesIO(ebp_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_approuvee_{invoice_id}_ebp.txt",
        }
    )


async def export_ciel_content(invoice_data: InvoiceData, invoice_id: str):
    """Generate Ciel export content"""
    ciel_content = export_to_ciel_ximport(invoice_data)
    return StreamingResponse(
        io.BytesIO(ciel_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_approuvee_{invoice_id}_ciel.txt",
        }
    )


async def export_fec_content(invoice_data: InvoiceData, invoice_id: str):
    """Generate FEC export content"""
    fec_content = export_to_fec(invoice_data, "ACH", 1)
    return StreamingResponse(
        io.BytesIO(fec_content.encode('utf-8')),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=facture_approuvee_{invoice_id}_fec.txt",
        }
    )
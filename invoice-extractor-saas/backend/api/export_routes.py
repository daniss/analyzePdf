from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import json
import csv
import io
import zipfile
import uuid
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
        if not extracted_data_dict or "invoice_data" not in extracted_data_dict:
            raise HTTPException(status_code=404, detail="Invoice data not found")
        
        invoice_data_dict = extracted_data_dict["invoice_data"]
        
        # Convert back to InvoiceData object
        invoice_data = InvoiceData(**invoice_data_dict)
        return invoice_data
        
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
    """Export invoice as CSV with French formatting"""
    
    # Get real invoice from database
    invoice_data = await get_real_invoice_data(invoice_id, current_user.id, db)
    
    # Create French-formatted CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')  # French CSV uses semicolon
    
    # Write headers
    writer.writerow(["Champ", "Valeur"])
    
    # Basic information
    writer.writerow(["Numéro de facture", invoice_data.invoice_number or ""])
    writer.writerow(["Date", invoice_data.date or ""])
    writer.writerow(["Date d'échéance", invoice_data.due_date or ""])
    
    # Vendor information
    if invoice_data.vendor:
        writer.writerow(["Fournisseur - Nom", invoice_data.vendor.name or ""])
        writer.writerow(["Fournisseur - Adresse", invoice_data.vendor.address or ""])
        writer.writerow(["Fournisseur - SIREN", invoice_data.vendor.siren_number or ""])
        writer.writerow(["Fournisseur - SIRET", invoice_data.vendor.siret_number or ""])
        writer.writerow(["Fournisseur - TVA", invoice_data.vendor.tva_number or ""])
    else:
        # Use legacy fields if vendor object not available
        writer.writerow(["Fournisseur - Nom", invoice_data.vendor_name or ""])
        writer.writerow(["Fournisseur - Adresse", invoice_data.vendor_address or ""])
    
    # Customer information
    if invoice_data.customer:
        writer.writerow(["Client - Nom", invoice_data.customer.name or ""])
        writer.writerow(["Client - Adresse", invoice_data.customer.address or ""])
        writer.writerow(["Client - SIREN", invoice_data.customer.siren_number or ""])
        writer.writerow(["Client - SIRET", invoice_data.customer.siret_number or ""])
        writer.writerow(["Client - TVA", invoice_data.customer.tva_number or ""])
    else:
        # Use legacy fields if customer object not available
        writer.writerow(["Client - Nom", invoice_data.customer_name or ""])
        writer.writerow(["Client - Adresse", invoice_data.customer_address or ""])
        writer.writerow(["Client - SIREN", ""])
        writer.writerow(["Client - SIRET", ""])
        writer.writerow(["Client - TVA", ""])
    
    # Financial totals (French format with comma) - handle None values
    subtotal = invoice_data.subtotal_ht or invoice_data.subtotal or 0
    total_tax = invoice_data.total_tva or invoice_data.tax or 0
    total = invoice_data.total_ttc or invoice_data.total or 0
    
    writer.writerow(["Sous-total HT", f"{subtotal:.2f}".replace('.', ',')])
    writer.writerow(["Total TVA", f"{total_tax:.2f}".replace('.', ',')])
    writer.writerow(["Total TTC", f"{total:.2f}".replace('.', ',')])
    
    # Line items
    writer.writerow(["", ""])  # Empty row
    writer.writerow(["Articles", ""])
    if invoice_data.line_items:
        for i, item in enumerate(invoice_data.line_items, 1):
            writer.writerow([f"Article {i} - Description", item.description or ""])
            writer.writerow([f"Article {i} - Quantité", str(item.quantity or 0).replace('.', ',')])
            writer.writerow([f"Article {i} - Prix unitaire HT", f"{item.unit_price or 0:.2f}".replace('.', ',')])
            writer.writerow([f"Article {i} - Total HT", f"{item.total or 0:.2f}".replace('.', ',')])
            
            # Handle None tax rate
            if item.tva_rate is not None:
                writer.writerow([f"Article {i} - Taux TVA", f"{item.tva_rate:.1f}%"])
            else:
                writer.writerow([f"Article {i} - Taux TVA", "0.0%"])
    
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
    
    # Convert to French-formatted JSON
    json_data = {
        "numero_facture": invoice_data.invoice_number,
        "date_facture": invoice_data.date,
        "date_echeance": invoice_data.due_date,
        "fournisseur": {
            "nom": invoice_data.vendor.name if invoice_data.vendor else None,
            "adresse": invoice_data.vendor.address if invoice_data.vendor else None,
            "code_postal": invoice_data.vendor.postal_code if invoice_data.vendor else None,
            "ville": invoice_data.vendor.city if invoice_data.vendor else None,
            "siren": invoice_data.vendor.siren_number if invoice_data.vendor else None,
            "siret": invoice_data.vendor.siret_number if invoice_data.vendor else None,
            "numero_tva": invoice_data.vendor.tva_number if invoice_data.vendor else None,
            "code_naf": invoice_data.vendor.naf_code if invoice_data.vendor else None,
            "forme_juridique": invoice_data.vendor.legal_form if invoice_data.vendor else None
        },
        "client": {
            "nom": invoice_data.customer.name if invoice_data.customer else None,
            "adresse": invoice_data.customer.address if invoice_data.customer else None,
            "siren": invoice_data.customer.siren_number if invoice_data.customer else None
        },
        "articles": [
            {
                "description": item.description,
                "quantite": item.quantity,
                "unite": item.unit,
                "prix_unitaire_ht": item.unit_price,
                "total_ht": item.total,
                "taux_tva": item.tva_rate,
                "montant_tva": item.tva_amount
            }
            for item in invoice_data.line_items
        ],
        "totaux": {
            "sous_total_ht": invoice_data.subtotal_ht,
            "total_tva": invoice_data.total_tva,
            "total_ttc": invoice_data.total_ttc,
            "devise": invoice_data.currency
        },
        "tva_par_taux": [
            {
                "taux": tva.rate,
                "base_ht": tva.taxable_amount,
                "montant_tva": tva.tva_amount
            }
            for tva in invoice_data.tva_breakdown
        ],
        "conditions_paiement": {
            "delai": invoice_data.payment_terms,
            "penalites_retard": invoice_data.late_payment_penalties,
            "frais_recouvrement": invoice_data.recovery_fees
        },
        "conformite_francaise": invoice_data.is_french_compliant
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
    
    # Create ZIP file with all exports
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        if format == "sage":
            batch_content = export_batch_to_sage_pnm(invoices)
            zip_file.writestr(f"export_sage_{datetime.now().strftime('%Y%m%d')}.pnm", 
                            batch_content.encode('utf-8'))
        elif format == "ebp":
            batch_content = export_batch_to_ebp_ascii(invoices)
            zip_file.writestr(f"export_ebp_{datetime.now().strftime('%Y%m%d')}.txt", 
                            batch_content.encode('utf-8'))
        elif format == "ciel":
            batch_content = export_batch_to_ciel_ximport(invoices)
            zip_file.writestr(f"export_ciel_{datetime.now().strftime('%Y%m%d')}.txt", 
                            batch_content.encode('utf-8'))
        elif format == "fec":
            batch_content = export_batch_to_fec(invoices, journal_code)
            zip_file.writestr(f"export_fec_{datetime.now().strftime('%Y%m%d')}.txt", 
                            batch_content.encode('utf-8'))
        else:
            # Individual exports for CSV/JSON
            for i, (invoice_id, invoice) in enumerate(zip(invoice_ids, invoices)):
                if format == "csv":
                    # Generate CSV content (simplified)
                    csv_content = f"Facture,{invoice.invoice_number}\\nTotal,{invoice.total_ttc}"
                    zip_file.writestr(f"facture_{invoice_id}.csv", csv_content.encode('utf-8'))
                elif format == "json":
                    # Generate JSON content
                    json_content = json.dumps(invoice.dict(), indent=2, ensure_ascii=False)
                    zip_file.writestr(f"facture_{invoice_id}.json", json_content.encode('utf-8'))
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=export_{format}_{datetime.now().strftime('%Y%m%d')}.zip"
        }
    )


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
                "description": "Format CSV avec séparateur point-virgule et formatage français",
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
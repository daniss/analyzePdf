from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import json
import csv
import io
from typing import List

from api.auth import get_current_user
from schemas.invoice import InvoiceData

router = APIRouter()


@router.get("/{invoice_id}/csv")
async def export_csv(
    invoice_id: str,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Get invoice from database
    # Mock data for now
    invoice_data = InvoiceData(
        invoice_number="INV-001",
        date="2024-01-01",
        vendor_name="Acme Corp",
        vendor_address="123 Main St",
        customer_name="Customer Inc",
        customer_address="456 Oak Ave",
        line_items=[],
        subtotal=1000.00,
        tax=100.00,
        total=1100.00
    )
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(["Field", "Value"])
    
    # Write invoice data
    writer.writerow(["Invoice Number", invoice_data.invoice_number])
    writer.writerow(["Date", invoice_data.date])
    writer.writerow(["Vendor Name", invoice_data.vendor_name])
    writer.writerow(["Vendor Address", invoice_data.vendor_address])
    writer.writerow(["Customer Name", invoice_data.customer_name])
    writer.writerow(["Customer Address", invoice_data.customer_address])
    writer.writerow(["Subtotal", invoice_data.subtotal])
    writer.writerow(["Tax", invoice_data.tax])
    writer.writerow(["Total", invoice_data.total])
    
    # Return as download
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_id}.csv"}
    )


@router.get("/{invoice_id}/json")
async def export_json(
    invoice_id: str,
    current_user: dict = Depends(get_current_user)
):
    # TODO: Get invoice from database
    # Mock data for now
    invoice_data = {
        "invoice_number": "INV-001",
        "date": "2024-01-01",
        "vendor": {
            "name": "Acme Corp",
            "address": "123 Main St"
        },
        "customer": {
            "name": "Customer Inc",
            "address": "456 Oak Ave"
        },
        "line_items": [],
        "subtotal": 1000.00,
        "tax": 100.00,
        "total": 1100.00
    }
    
    # Return as download
    return StreamingResponse(
        io.BytesIO(json.dumps(invoice_data, indent=2).encode()),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_id}.json"}
    )


@router.post("/batch")
async def export_batch(
    invoice_ids: List[str],
    format: str = "csv",
    current_user: dict = Depends(get_current_user)
):
    if format not in ["csv", "json"]:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    # TODO: Get multiple invoices and export as zip
    return {"message": f"Batch export of {len(invoice_ids)} invoices initiated"}
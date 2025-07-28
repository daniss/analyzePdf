#!/usr/bin/env python3
"""
Create a test invoice PDF with real SIRET numbers that will pass INSEE validation
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from datetime import datetime

def create_real_siret_invoice():
    """Create invoice with real SIRET numbers from INSEE database"""
    
    filename = "facture_siret_reels_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".pdf"
    
    # Real SIRET numbers we found from INSEE API
    real_carrefour_siret = "40422352100018"  # Real Carrefour establishment
    real_bouygues_siret = "57201524600182"   # Real Bouygues establishment
    
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "FACTURE N° 2025-TEST-REAL-SIRET")
    
    # Date
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 80, f"Date: {datetime.now().strftime('%d %B %Y')}")
    c.drawString(50, height - 95, f"Échéance: {datetime.now().strftime('%d %B %Y')}")
    
    # Supplier (Carrefour - Real SIRET)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 130, "FOURNISSEUR:")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 150, "CARREFOUR")
    c.drawString(50, height - 165, "33 Avenue Émile Zola")
    c.drawString(50, height - 180, "92100 Boulogne-Billancourt")
    c.drawString(50, height - 195, "FRANCE")
    c.drawString(50, height - 215, f"SIREN: {real_carrefour_siret[:9]}")
    c.drawString(50, height - 230, f"SIRET: {real_carrefour_siret}")
    c.drawString(50, height - 245, f"N° TVA: FR32{real_carrefour_siret[:9]}")
    
    # Client (Bouygues - Real SIRET)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 280, "CLIENT:")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 300, "BOUYGUES")
    c.drawString(50, height - 315, "32 Avenue Hoche")
    c.drawString(50, height - 330, "75008 Paris")
    c.drawString(50, height - 345, "FRANCE")
    c.drawString(50, height - 365, f"SIREN: {real_bouygues_siret[:9]}")
    c.drawString(50, height - 380, f"SIRET: {real_bouygues_siret}")
    c.drawString(50, height - 395, f"N° TVA: FR45{real_bouygues_siret[:9]}")
    
    # Invoice details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 430, "DÉTAIL DE LA FACTURE:")
    
    # Table header
    c.setFont("Helvetica-Bold", 9)
    y = height - 450
    c.drawString(50, y, "Description")
    c.drawString(200, y, "Qté")
    c.drawString(250, y, "Prix HT")
    c.drawString(300, y, "TVA")
    c.drawString(350, y, "Total HT")
    c.drawString(420, y, "Total TTC")
    
    # Table content
    c.setFont("Helvetica", 9)
    items = [
        ("Services informatiques", "1", "5000,00 €", "20,0%", "5 000,00 €", "6 000,00 €"),
        ("Formation", "2", "1000,00 €", "20,0%", "2 000,00 €", "2 400,00 €"),
    ]
    
    y = height - 470
    for item in items:
        c.drawString(50, y, item[0])
        c.drawString(200, y, item[1])
        c.drawString(250, y, item[2])
        c.drawString(300, y, item[3])
        c.drawString(350, y, item[4])
        c.drawString(420, y, item[5])
        y -= 20
    
    # Totals
    c.setFont("Helvetica-Bold", 10)
    y = height - 530
    c.drawString(50, y, "RÉCAPITULATIF TVA:")
    c.drawString(50, y - 15, "Base HT à 20,0%: 7 000,00 €")
    c.drawString(50, y - 30, "TVA à 20,0%: 1 400,00 €")
    
    c.drawString(50, y - 50, "TOTAL HT: 7 000,00 €")
    c.drawString(50, y - 65, "TOTAL TVA: 1 400,00 €")
    c.drawString(50, y - 80, "TOTAL TTC: 8 400,00 €")
    
    # Payment terms
    c.setFont("Helvetica", 8)
    c.drawString(50, y - 110, "Modalités de paiement: 30 jours net")
    c.drawString(50, y - 125, "En cas de retard de paiement, des pénalités de retard seront appliquées.")
    
    c.save()
    
    print(f"✅ Created invoice with REAL SIRET numbers: {filename}")
    print(f"   Fournisseur SIRET: {real_carrefour_siret} (Real Carrefour)")
    print(f"   Client SIRET: {real_bouygues_siret} (Real Bouygues)")
    print(f"   This invoice should pass INSEE validation with 'VALID' status!")
    
    return filename

if __name__ == "__main__":
    create_real_siret_invoice()
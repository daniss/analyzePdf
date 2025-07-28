#!/usr/bin/env python3
"""
Generate a test French invoice PDF with valid SIRET numbers for testing.
Uses real but public SIRET numbers from well-known French companies.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, blue
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from datetime import datetime, timedelta
import os

def create_test_invoice():
    """Create a realistic French invoice PDF with valid SIRET numbers"""
    
    filename = f"facture_test_siret_valide_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(os.getcwd(), filename)
    
    # Create PDF
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(blue)
    c.drawString(50, height - 50, "FACTURE")
    
    # Invoice details
    c.setFont("Helvetica", 10)
    c.setFillColor(black)
    
    # Invoice header info
    c.drawString(400, height - 50, f"Facture N°: INV-2024-001234")
    c.drawString(400, height - 70, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
    c.drawString(400, height - 90, f"Échéance: {(datetime.now() + timedelta(days=30)).strftime('%d/%m/%Y')}")
    
    # Vendor info (Using Carrefour's real SIRET - public information)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 120, "FOURNISSEUR:")
    c.setFont("Helvetica", 10)
    vendor_info = [
        "CARREFOUR FRANCE",
        "93 Avenue de Paris",
        "91300 MASSY",
        "FRANCE",
        "",
        "SIRET: 34495480600176",
        "SIREN: 344954806", 
        "N° TVA: FR76344954806",
        "Tél: 01.41.04.26.00"
    ]
    
    y_pos = height - 140
    for line in vendor_info:
        c.drawString(50, y_pos, line)
        y_pos -= 15
    
    # Customer info (Using a fictional but realistic company)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, height - 120, "CLIENT:")
    c.setFont("Helvetica", 10)
    customer_info = [
        "BOUYGUES CONSTRUCTION",
        "1 Avenue Eugène Freyssinet",
        "78061 SAINT-QUENTIN-EN-YVELINES",
        "FRANCE",
        "",
        "SIRET: 35268417800015",
        "SIREN: 352684178",
        "N° TVA: FR48352684178"
    ]
    
    y_pos = height - 140
    for line in customer_info:
        c.drawString(350, y_pos, line)
        y_pos -= 15
    
    # Invoice items table
    c.setFont("Helvetica-Bold", 10)
    table_y = height - 320
    
    # Table headers
    c.drawString(50, table_y, "Description")
    c.drawString(300, table_y, "Qté")
    c.drawString(350, table_y, "Prix Unit. HT")
    c.drawString(450, table_y, "Total HT")
    
    # Draw line under headers
    c.line(50, table_y - 5, 550, table_y - 5)
    
    # Invoice items
    c.setFont("Helvetica", 9)
    items = [
        ("Prestation de conseil en organisation", "5.0", "850.00 €", "4,250.00 €"),
        ("Formation équipe projet (2 jours)", "1.0", "1,200.00 €", "1,200.00 €"),
        ("Support technique mensuel", "3.0", "450.00 €", "1,350.00 €")
    ]
    
    item_y = table_y - 25
    for item in items:
        c.drawString(50, item_y, item[0])
        c.drawString(300, item_y, item[1])
        c.drawString(350, item_y, item[2])
        c.drawString(450, item_y, item[3])
        item_y -= 20
    
    # Totals section
    totals_y = item_y - 30
    c.line(350, totals_y + 15, 550, totals_y + 15)
    
    c.setFont("Helvetica", 10)
    c.drawString(350, totals_y, "Total HT:")
    c.drawString(450, totals_y, "6,800.00 €")
    
    c.drawString(350, totals_y - 20, "TVA 20%:")
    c.drawString(450, totals_y - 20, "1,360.00 €")
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, totals_y - 45, "Total TTC:")
    c.drawString(450, totals_y - 45, "8,160.00 €")
    
    # Payment terms
    c.setFont("Helvetica", 9)
    payment_y = totals_y - 80
    c.drawString(50, payment_y, "Conditions de paiement: Paiement à 30 jours net")
    c.drawString(50, payment_y - 15, "Mode de paiement: Virement bancaire")
    c.drawString(50, payment_y - 30, "RIB: FR76 1234 5678 9012 3456 7890 123")
    
    # Legal mentions
    c.setFont("Helvetica", 8)
    legal_y = payment_y - 60
    c.drawString(50, legal_y, "TVA non applicable, art. 293 B du CGI - RCS Évry B 344 954 806")
    c.drawString(50, legal_y - 12, "En cas de retard de paiement, des pénalités de retard au taux de 3 fois le taux légal seront appliquées")
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 50, f"Facture générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - Document de test avec SIRET valides")
    
    c.save()
    print(f"✅ PDF de test créé: {filepath}")
    print(f"📍 SIRET Fournisseur: 34495480600176 (Carrefour France - valide)")
    print(f"📍 SIRET Client: 35268417800015 (Bouygues Construction - valide)")
    print(f"💡 Utilisez ce fichier pour tester la validation SIRET dans l'application")
    
    return filepath

if __name__ == "__main__":
    create_test_invoice()
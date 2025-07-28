#!/usr/bin/env python3
"""
Create a fresh PDF with the same content as the problematic one
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

def create_fresh_pdf():
    """Create a fresh PDF that mimics the problematic one"""
    
    output_path = "/tmp/fresh_test_invoice.pdf"
    
    # Create PDF with ReportLab (same library as original)
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    # Add the same content as the problematic invoice
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 80, "FACTURE")
    
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 80, "Facture N°: INV-2024-001234")
    c.drawString(400, height - 100, "Date: 27/07/2025")
    c.drawString(400, height - 120, "Échéance: 26/08/2025")
    
    c.drawString(50, height - 150, "FOURNISSEUR:")
    c.drawString(50, height - 170, "TechSolutions SARL")
    c.drawString(50, height - 190, "123 Rue de la Tech")
    c.drawString(50, height - 210, "75001 Paris")
    c.drawString(50, height - 230, "N° SIRET: 34495480600176")
    c.drawString(50, height - 250, "N° TVA: FR12345678901")
    
    c.drawString(350, height - 150, "CLIENT:")
    c.drawString(350, height - 170, "DataCorp SAS")
    c.drawString(350, height - 190, "456 Avenue des Données")
    c.drawString(350, height - 210, "69000 Lyon")
    c.drawString(350, height - 230, "N° SIRET: 98765432100019")
    c.drawString(350, height - 250, "N° TVA: FR98765432109")
    
    # Add line items
    y_pos = height - 320
    c.drawString(50, y_pos, "DÉSIGNATION")
    c.drawString(300, y_pos, "QTÉ")
    c.drawString(350, y_pos, "PRIX UNIT. HT")
    c.drawString(450, y_pos, "TOTAL HT")
    
    y_pos -= 30
    c.drawString(50, y_pos, "Développement API REST")
    c.drawString(300, y_pos, "5.0")
    c.drawString(350, y_pos, "850.00 €")
    c.drawString(450, y_pos, "4,250.00 €")
    
    y_pos -= 20
    c.drawString(50, y_pos, "Intégration base de données")
    c.drawString(300, y_pos, "1.0")
    c.drawString(350, y_pos, "1,200.00 €")
    c.drawString(450, y_pos, "1,200.00 €")
    
    y_pos -= 20
    c.drawString(50, y_pos, "Tests et documentation")
    c.drawString(300, y_pos, "3.0")
    c.drawString(350, y_pos, "450.00 €")
    c.drawString(450, y_pos, "1,350.00 €")
    
    # Add totals
    y_pos -= 50
    c.drawString(350, y_pos, "Total HT:")
    c.drawString(450, y_pos, "6,800.00 €")
    
    y_pos -= 20
    c.drawString(350, y_pos, "TVA 20.0%:")
    c.drawString(450, y_pos, "1,360.00 €")
    
    y_pos -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(350, y_pos, "Total TTC:")
    c.drawString(450, y_pos, "8,160.00 €")
    
    # Add footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 100, "Conditions de paiement: 30 jours")
    c.drawString(50, 80, "TVA non applicable, art. 293 B du CGI")
    c.drawString(50, 60, "Facture acquittée le _____ par _____")
    
    c.save()
    
    file_size = os.path.getsize(output_path)
    print(f"✅ Created fresh PDF: {output_path}")
    print(f"📏 Size: {file_size} bytes ({file_size/1024:.1f} KB)")
    
    return output_path

if __name__ == "__main__":
    print("🔧 Creating fresh PDF to test if issue is file-specific...")
    create_fresh_pdf()
    print("🎯 Test this file in the frontend to see if it works!")
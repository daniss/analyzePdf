#!/usr/bin/env python3
"""
Generate 5 different French PDF invoices for testing ComptaFlow
Each invoice will test different aspects of the extraction system
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from datetime import datetime, timedelta
import os

def create_invoice_1_simple():
    """Simple single-item invoice - Basic test case"""
    filename = "facture_01_simple.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=20*mm)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                fontSize=20, textColor=colors.darkblue, alignment=TA_CENTER)
    story.append(Paragraph("FACTURE", title_style))
    story.append(Spacer(1, 10*mm))
    
    # Vendor info
    vendor_style = ParagraphStyle('Vendor', parent=styles['Normal'], fontSize=11)
    story.append(Paragraph("<b>BOULANGERIE ARTISANALE MARTIN</b>", vendor_style))
    story.append(Paragraph("15 Rue de la Paix", vendor_style))
    story.append(Paragraph("75001 PARIS", vendor_style))
    story.append(Paragraph("SIRET: 123 456 789 01234", vendor_style))
    story.append(Paragraph("TVA: FR12123456789", vendor_style))
    story.append(Paragraph("Tél: 01 42 36 48 60", vendor_style))
    story.append(Spacer(1, 8*mm))
    
    # Customer info
    story.append(Paragraph("<b>Facturé à:</b>", vendor_style))
    story.append(Paragraph("RESTAURANT LE PETIT BISTROT", vendor_style))
    story.append(Paragraph("42 Avenue des Champs-Élysées", vendor_style))
    story.append(Paragraph("75008 PARIS", vendor_style))
    story.append(Paragraph("SIRET: 987 654 321 09876", vendor_style))
    story.append(Spacer(1, 8*mm))
    
    # Invoice details
    invoice_data = [
        ["N° Facture:", "F2024-001"],
        ["Date:", "15/01/2024"],
        ["Échéance:", "15/02/2024"]
    ]
    
    invoice_table = Table(invoice_data, colWidths=[40*mm, 60*mm])
    invoice_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 10*mm))
    
    # Items table
    items_data = [
        ["Désignation", "Qté", "Prix Unit. HT", "Total HT"],
        ["Pain de campagne (lot de 50)", "10", "45,00 €", "450,00 €"]
    ]
    
    items_table = Table(items_data, colWidths=[80*mm, 20*mm, 30*mm, 30*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(items_table)
    story.append(Spacer(1, 8*mm))
    
    # Totals
    totals_data = [
        ["", "", "Sous-total HT:", "450,00 €"],
        ["", "", "TVA 20%:", "90,00 €"],
        ["", "", "<b>Total TTC:</b>", "<b>540,00 €</b>"]
    ]
    
    totals_table = Table(totals_data, colWidths=[80*mm, 20*mm, 30*mm, 30*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (2, -1), (3, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (2, -1), (3, -1), 2, colors.black),
    ]))
    story.append(totals_table)
    
    # Payment terms
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("<b>Conditions de paiement:</b> 30 jours net", vendor_style))
    story.append(Paragraph("RIB: FR14 2004 1010 0505 0001 3M02 606", vendor_style))
    
    doc.build(story)
    return filename

def create_invoice_2_complex():
    """Complex multi-item invoice with multiple TVA rates"""
    filename = "facture_02_complexe.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=15*mm)
    story = []
    styles = getSampleStyleSheet()
    
    # Header with logo placeholder
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                fontSize=18, textColor=colors.darkred, alignment=TA_CENTER)
    story.append(Paragraph("FACTURE DE VENTE", title_style))
    story.append(Spacer(1, 8*mm))
    
    # Vendor info - Service company
    vendor_style = ParagraphStyle('Vendor', parent=styles['Normal'], fontSize=10)
    story.append(Paragraph("<b>CONSULTANTS & ASSOCIÉS SAS</b>", vendor_style))
    story.append(Paragraph("Zone d'Activité de la Défense", vendor_style))
    story.append(Paragraph("Tour Areva - 1 Place Jean Millier", vendor_style))
    story.append(Paragraph("92400 COURBEVOIE", vendor_style))
    story.append(Paragraph("SIRET: 789 123 456 78901", vendor_style))
    story.append(Paragraph("TVA Intracommunautaire: FR89789123456", vendor_style))
    story.append(Paragraph("RCS Nanterre B 789 123 456", vendor_style))
    story.append(Paragraph("Capital social: 250 000 €", vendor_style))
    story.append(Spacer(1, 6*mm))
    
    # Customer info - with complex address
    story.append(Paragraph("<b>Client:</b>", vendor_style))
    story.append(Paragraph("GROUPE INDUSTRIEL FRANÇAIS", vendor_style))
    story.append(Paragraph("Service Comptabilité - Bât. C", vendor_style))
    story.append(Paragraph("123 Boulevard de la République", vendor_style))
    story.append(Paragraph("BP 4567", vendor_style))
    story.append(Paragraph("69003 LYON CEDEX 03", vendor_style))
    story.append(Paragraph("SIRET: 456 789 123 45678", vendor_style))
    story.append(Paragraph("TVA: FR45456789123", vendor_style))
    story.append(Spacer(1, 6*mm))
    
    # Invoice details with complex numbering
    invoice_data = [
        ["N° Facture:", "2024-CONS-00142"],
        ["Date d'émission:", "23/01/2024"],
        ["Date d'échéance:", "22/03/2024"],
        ["Bon de commande:", "BC-2024-001789"],
        ["Référence projet:", "PROJ-GIF-2024-01"]
    ]
    
    invoice_table = Table(invoice_data, colWidths=[45*mm, 65*mm])
    invoice_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 8*mm))
    
    # Complex items table with multiple TVA rates
    items_data = [
        ["Réf.", "Désignation", "Qté", "Prix Unit. HT", "TVA", "Total HT"],
        ["CONS-001", "Audit comptable annuel", "1", "8 500,00 €", "20%", "8 500,00 €"],
        ["CONS-002", "Formation équipe comptable (2j)", "1", "3 200,00 €", "20%", "3 200,00 €"],
        ["SOFT-001", "Licence logiciel comptable", "1", "1 850,00 €", "20%", "1 850,00 €"],
        ["DOC-001", "Documentation technique", "5", "125,00 €", "5,5%", "625,00 €"],
        ["TRANS-001", "Frais de déplacement", "1", "284,50 €", "10%", "284,50 €"],
        ["FORM-001", "Supports de formation", "20", "15,75 €", "5,5%", "315,00 €"]
    ]
    
    items_table = Table(items_data, colWidths=[18*mm, 70*mm, 12*mm, 25*mm, 12*mm, 25*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6*mm))
    
    # Complex totals with multiple TVA rates
    totals_data = [
        ["", "", "", "", "Sous-total HT:", "14 774,50 €"],
        ["", "", "", "", "TVA 20% (13 550,00 €):", "2 710,00 €"],
        ["", "", "", "", "TVA 10% (284,50 €):", "28,45 €"],
        ["", "", "", "", "TVA 5,5% (940,00 €):", "51,70 €"],
        ["", "", "", "", "Total TVA:", "2 790,15 €"],
        ["", "", "", "", "<b>TOTAL TTC:</b>", "<b>17 564,65 €</b>"]
    ]
    
    totals_table = Table(totals_data, colWidths=[18*mm, 70*mm, 12*mm, 25*mm, 25*mm, 25*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (4, 0), (5, -1), 'RIGHT'),
        ('FONTNAME', (4, -1), (5, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LINEABOVE', (4, -1), (5, -1), 2, colors.black),
        ('BACKGROUND', (4, -1), (5, -1), colors.lightblue),
    ]))
    story.append(totals_table)
    
    # Complex payment terms
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("<b>Modalités de paiement:</b>", vendor_style))
    story.append(Paragraph("• Paiement à 60 jours fin de mois par virement bancaire", vendor_style))
    story.append(Paragraph("• Escompte 2% si paiement sous 8 jours", vendor_style))
    story.append(Paragraph("• Pénalités de retard: 3 fois le taux légal", vendor_style))
    story.append(Paragraph("• Indemnité forfaitaire pour frais de recouvrement: 40 €", vendor_style))
    story.append(Paragraph("<b>IBAN:</b> FR14 3000 2005 5000 0157 8414 Z02", vendor_style))
    story.append(Paragraph("<b>BIC:</b> CRLYFRPP", vendor_style))
    
    doc.build(story)
    return filename

def create_invoice_3_foreign():
    """Invoice with foreign elements and special formatting"""
    filename = "facture_03_international.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=20*mm)
    story = []
    styles = getSampleStyleSheet()
    
    # Bilingual header
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                fontSize=16, textColor=colors.purple, alignment=TA_CENTER)
    story.append(Paragraph("FACTURE / INVOICE", title_style))
    story.append(Spacer(1, 8*mm))
    
    # French company with international activity
    vendor_style = ParagraphStyle('Vendor', parent=styles['Normal'], fontSize=10)
    story.append(Paragraph("<b>EXPORT SOLUTIONS FRANCE SARL</b>", vendor_style))
    story.append(Paragraph("Parc d'Activités de Roissy", vendor_style))
    story.append(Paragraph("14 Rue du Commerce International", vendor_style))
    story.append(Paragraph("95700 ROISSY-EN-FRANCE", vendor_style))
    story.append(Paragraph("SIRET: 654 321 987 65432", vendor_style))
    story.append(Paragraph("N° TVA: FR65654321987", vendor_style))
    story.append(Paragraph("N° EORI: FR654321987654321", vendor_style))
    story.append(Spacer(1, 6*mm))
    
    # Foreign customer
    story.append(Paragraph("<b>Sold to / Vendu à:</b>", vendor_style))
    story.append(Paragraph("DEUTSCHE IMPORT GMBH", vendor_style))
    story.append(Paragraph("Hauptstraße 156", vendor_style))
    story.append(Paragraph("D-80331 MÜNCHEN", vendor_style))
    story.append(Paragraph("DEUTSCHLAND", vendor_style))
    story.append(Paragraph("USt-ID: DE123456789", vendor_style))
    story.append(Spacer(1, 6*mm))
    
    # Invoice details with export info
    invoice_data = [
        ["N° Facture / Invoice No.:", "EXP-2024-0089"],
        ["Date:", "28/01/2024"],
        ["Incoterm:", "DDP München"],
        ["Mode de transport:", "Route / Road"],
        ["Délai de paiement:", "30 jours / 30 days"]
    ]
    
    invoice_table = Table(invoice_data, colWidths=[50*mm, 60*mm])
    invoice_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 8*mm))
    
    # Items with export complexity
    items_data = [
        ["Code HS", "Désignation / Description", "Origine", "Qté", "Prix Unit.", "Total HT"],
        ["8471.30.00", "Ordinateurs portables professionnels", "France", "25", "1 200,00 €", "30 000,00 €"],
        ["8528.72.10", "Écrans LCD 24 pouces", "France", "25", "340,00 €", "8 500,00 €"],
        ["8471.60.60", "Claviers sans fil ergonomiques", "France", "25", "89,00 €", "2 225,00 €"],
        ["8471.60.70", "Souris optiques", "France", "25", "45,00 €", "1 125,00 €"],
        ["SERV-001", "Installation et configuration", "France", "1", "2 850,00 €", "2 850,00 €"],
        ["FORM-001", "Formation utilisateurs (3j)", "France", "1", "4 200,00 €", "4 200,00 €"]
    ]
    
    items_table = Table(items_data, colWidths=[20*mm, 60*mm, 15*mm, 12*mm, 22*mm, 22*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.purple),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6*mm))
    
    # Totals for export (TVA 0% for EU)
    totals_data = [
        ["", "", "", "", "Sous-total HT:", "48 900,00 €"],
        ["", "", "", "", "TVA 0% (Livraison UE):", "0,00 €"],
        ["", "", "", "", "<b>Total TTC:</b>", "<b>48 900,00 €</b>"],
        ["", "", "", "", "Frais de port:", "450,00 €"],
        ["", "", "", "", "<b>TOTAL GÉNÉRAL:</b>", "<b>49 350,00 €</b>"]
    ]
    
    totals_table = Table(totals_data, colWidths=[20*mm, 60*mm, 15*mm, 12*mm, 22*mm, 22*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (4, 0), (5, -1), 'RIGHT'),
        ('FONTNAME', (4, -1), (5, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LINEABOVE', (4, -1), (5, -1), 2, colors.black),
    ]))
    story.append(totals_table)
    
    # Export specific information
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("<b>Informations export / Export information:</b>", vendor_style))
    story.append(Paragraph("• Livraison intracommunautaire - TVA 0% (art. 262 ter I CGI)", vendor_style))
    story.append(Paragraph("• EU delivery - VAT 0% according to French tax law", vendor_style))
    story.append(Paragraph("• Poids total / Total weight: 187 kg", vendor_style))
    story.append(Paragraph("• N° de suivi / Tracking: FR2024012800089", vendor_style))
    
    doc.build(story)
    return filename

def create_invoice_4_special_cases():
    """Invoice with special formatting and edge cases"""
    filename = "facture_04_cas_speciaux.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=15*mm)
    story = []
    styles = getSampleStyleSheet()
    
    # Stylized header
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                fontSize=22, textColor=colors.darkgreen, alignment=TA_CENTER)
    story.append(Paragraph("F A C T U R E", title_style))
    story.append(Spacer(1, 6*mm))
    
    # Service company with special characters
    vendor_style = ParagraphStyle('Vendor', parent=styles['Normal'], fontSize=10)
    story.append(Paragraph("<b>CHÂTEAU & ASSOCIÉS S.A.S.</b>", vendor_style))
    story.append(Paragraph("Spécialiste en œnologie & gastronomie", vendor_style))
    story.append(Paragraph("15, Allée François-Mitterrand", vendor_style))
    story.append(Paragraph("33000 BORDEAUX", vendor_style))
    story.append(Paragraph("SIRET: 321 654 987 32165", vendor_style))
    story.append(Paragraph("TVA: FR32321654987", vendor_style))
    story.append(Paragraph("Tél: 05.56.44.33.22 - Fax: 05.56.44.33.23", vendor_style))
    story.append(Paragraph("contact@chateau-associes.fr", vendor_style))
    story.append(Spacer(1, 6*mm))
    
    # Customer with apostrophes and special chars
    story.append(Paragraph("<b>Destinataire:</b>", vendor_style))
    story.append(Paragraph("RESTAURANT L'ÉTOILE D'OR", vendor_style))
    story.append(Paragraph("Chef: M. Jean-François O'BRIEN", vendor_style))
    story.append(Paragraph("25 Rue Saint-Honoré", vendor_style))
    story.append(Paragraph("75001 PARIS 1er", vendor_style))
    story.append(Paragraph("SIRET: 159 753 486 15975", vendor_style))
    story.append(Spacer(1, 6*mm))
    
    # Invoice with special numbering
    invoice_data = [
        ["Facture N°:", "CH&A-2024/01-156-BIS"],
        ["Date d'émission:", "31/01/2024"],
        ["Date de service:", "15-16/01/2024"],
        ["Échéance:", "29/02/2024"],
        ["Commande:", "L'ÉTOILE-CMD-2024-001"]
    ]
    
    invoice_table = Table(invoice_data, colWidths=[40*mm, 60*mm])
    story.append(invoice_table)
    story.append(Spacer(1, 8*mm))
    
    # Complex items with decimals and fractions
    items_data = [
        ["Libellé", "Unité", "Qté", "P.U. HT", "Remise", "Net HT"],
        ["Dégustation & conseil œnologique", "h", "6,5", "150,00 €", "10%", "877,50 €"],
        ["Sélection vins Bordeaux AOC (douzaine)", "u", "3", "285,75 €", "0%", "857,25 €"],
        ["Consultation menu & accords mets-vins", "forfait", "1", "450,00 €", "15%", "382,50 €"],
        ["Frais de déplacement (A/R Paris-Bordeaux)", "km", "1 134", "0,65 €", "0%", "737,10 €"],
        ["Rapport d'expertise (32 pages)", "u", "1", "125,00 €", "0%", "125,00 €"]
    ]
    
    items_table = Table(items_data, colWidths=[65*mm, 15*mm, 15*mm, 20*mm, 15*mm, 20*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6*mm))
    
    # Totals with complex calculations
    totals_data = [
        ["", "", "", "", "Sous-total HT:", "2 979,35 €"],
        ["", "", "", "", "Remise globale 5%:", "-148,97 €"],
        ["", "", "", "", "Net commercial HT:", "2 830,38 €"],
        ["", "", "", "", "TVA 20,0%:", "566,08 €"],
        ["", "", "", "", "<b>TOTAL TTC:</b>", "<b>3 396,46 €</b>"],
        ["", "", "", "", "Dont éco-contribution:", "2,50 €"]
    ]
    
    totals_table = Table(totals_data, colWidths=[65*mm, 15*mm, 15*mm, 20*mm, 20*mm, 20*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (4, 0), (5, -1), 'RIGHT'),
        ('FONTNAME', (4, -1), (5, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LINEABOVE', (4, -1), (5, -1), 2, colors.black),
    ]))
    story.append(totals_table)
    
    # Special conditions
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("<b>Conditions particulières:</b>", vendor_style))
    story.append(Paragraph("✓ Prestation réalisée selon cahier des charges n°2024-CdC-001", vendor_style))
    story.append(Paragraph("✓ Garantie satisfaction: remboursement intégral si non-conformité", vendor_style))
    story.append(Paragraph("✓ Clause de confidentialité: engagement sur les recettes & fournisseurs", vendor_style))
    story.append(Paragraph("RIB: FR76 1470 7000 0012 3456 7890 189 (Crédit Agricole d'Aquitaine)", vendor_style))
    
    doc.build(story)
    return filename

def create_invoice_5_scan_simulation():
    """Invoice designed to simulate a scanned document with quality issues"""
    filename = "facture_05_scan_difficile.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=25*mm)
    story = []
    styles = getSampleStyleSheet()
    
    # Slightly rotated title to simulate scan issues
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], 
                                fontSize=18, textColor=colors.black, alignment=TA_CENTER)
    story.append(Paragraph("FACTURE", title_style))
    story.append(Spacer(1, 10*mm))
    
    # Vendor with old-style formatting
    vendor_style = ParagraphStyle('Vendor', parent=styles['Normal'], fontSize=9)
    story.append(Paragraph("ÉTABLISSEMENTS MARTIN & FILS", vendor_style))
    story.append(Paragraph("Entreprise familiale depuis 1952", vendor_style))
    story.append(Paragraph("Zone Industrielle du Pont-Neuf", vendor_style))
    story.append(Paragraph("Rue de l'Industrie - BP 234", vendor_style))
    story.append(Paragraph("42000 SAINT-ÉTIENNE Cedex 2", vendor_style))
    story.append(Paragraph("Tél: 04-77-25-36-47 Fax: 04-77-25-36-48", vendor_style))
    story.append(Paragraph("SIRET : 147 258 369 14725", vendor_style))
    story.append(Paragraph("TVA FR14147258369", vendor_style))
    story.append(Spacer(1, 8*mm))
    
    # Customer with formatting variations
    story.append(Paragraph("Facturé à:", vendor_style))
    story.append(Paragraph("STE RENOVATION MODERNE", vendor_style))
    story.append(Paragraph("M. DUBOIS Pierre", vendor_style))
    story.append(Paragraph("154, avenue du Général de Gaulle", vendor_style))
    story.append(Paragraph("69100 VILLEURBANNE", vendor_style))
    story.append(Paragraph("SIRET: 789456123 00015", vendor_style))
    story.append(Spacer(1, 8*mm))
    
    # Invoice details with inconsistent formatting
    story.append(Paragraph("Facture no: 2024-0456", vendor_style))
    story.append(Paragraph("Du: 22 janvier 2024", vendor_style))
    story.append(Paragraph("Échéance: 21/03/2024", vendor_style))
    story.append(Spacer(1, 8*mm))
    
    # Items table with alignment issues (simulating scan problems)
    items_data = [
        ["Réf", "Désignation", "Qté", "PU HT", "Total HT"],
        ["MT-001", "Tubes acier galvanisé Ø40mm (6m)", "125", "28,75", "3 593,75"],
        ["MT-002", "Raccords coudés 90° galvanisés", "67", "12,50", "837,50"],
        ["MT-003", "Boulonnerie inox (lot assortiment)", "8", "45,80", "366,40"],
        ["MT-004", "Peinture antirouille (pot 5L)", "12", "67,25", "807,00"],
        ["MAIN001", "Main d'œuvre installation (h)", "24", "55,00", "1 320,00"],
        ["TRANS", "Transport et livraison", "1", "185,00", "185,00"]
    ]
    
    items_table = Table(items_data, colWidths=[20*mm, 80*mm, 15*mm, 18*mm, 22*mm])
    items_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6*mm))
    
    # Totals with spacing issues
    story.append(Paragraph("                                     Sous-total HT: 7 109,65 €", vendor_style))
    story.append(Paragraph("                                     TVA 20%:         1 421,93 €", vendor_style))
    story.append(Paragraph("                                     ──────────────────────────", vendor_style))
    story.append(Paragraph("                                     TOTAL TTC:      8 531,58 €", vendor_style))
    story.append(Spacer(1, 8*mm))
    
    # Payment information with old formatting
    story.append(Paragraph("Règlement: chèque ou virement sous 60 jours", vendor_style))
    story.append(Paragraph("Banque: Crédit Mutuel Loire Atlantique Centre", vendor_style))
    story.append(Paragraph("IBAN: FR14 1558 9000 0123 4567 8901 234", vendor_style))
    story.append(Paragraph("Retard de paiement: pénalités au taux BCE + 10 points", vendor_style))
    
    doc.build(story)
    return filename

def main():
    """Generate all test invoices"""
    # Create directory for test invoices
    os.makedirs("/home/danis/code/projectpdf/invoice-extractor-saas/test_invoices", exist_ok=True)
    os.chdir("/home/danis/code/projectpdf/invoice-extractor-saas/test_invoices")
    
    print("🧾 Génération des factures de test...")
    
    files = []
    
    print("1. Facture simple (cas basique)...")
    files.append(create_invoice_1_simple())
    
    print("2. Facture complexe (multi-TVA)...")
    files.append(create_invoice_2_complex())
    
    print("3. Facture internationale...")
    files.append(create_invoice_3_foreign())
    
    print("4. Facture cas spéciaux...")
    files.append(create_invoice_4_special_cases())
    
    print("5. Facture scan difficile...")
    files.append(create_invoice_5_scan_simulation())
    
    print(f"\n✅ {len(files)} factures générées avec succès:")
    for i, file in enumerate(files, 1):
        print(f"   {i}. {file}")
    
    print(f"\n📁 Fichiers disponibles dans: {os.getcwd()}")
    print("\n🧪 Vous pouvez maintenant tester ces factures dans ComptaFlow!")

if __name__ == "__main__":
    main()
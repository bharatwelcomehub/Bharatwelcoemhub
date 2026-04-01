# =======================================
# Exit Documents Generator
# Generates Exit Agreement, Handover Report, Settlement Sheet, Exit Certificate
# =======================================

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, 
    PageBreak
)
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Register Devanagari font
try:
    pdfmetrics.registerFont(TTFont('NotoDevanagari', '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf'))
    MARATHI_FONT = 'NotoDevanagari'
except:
    MARATHI_FONT = 'Helvetica'

# Colors
NAVY_BLUE = "#1B365D"
GOLD = "#B8860B"
DARK_GRAY = "#333333"
MEDIUM_GRAY = "#666666"
LIGHT_GRAY = "#F5F5F5"
RED = "#C41E3A"

class ExitDocumentCanvas(canvas.Canvas):
    """Canvas with headers and footers for exit documents"""
    def __init__(self, *args, doc_title="Exit Document", **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self.doc_title = doc_title

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header()
            self.draw_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header(self):
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor(GOLD))
            self.setLineWidth(1.5)
            self.line(0.75*inch, A4[1] - 0.5*inch, A4[0] - 0.75*inch, A4[1] - 0.5*inch)
            
            self.setFillColor(colors.HexColor(NAVY_BLUE))
            self.setFont("Helvetica-Bold", 9)
            self.drawString(0.75*inch, A4[1] - 0.4*inch, "PURNABRAMHA")
            
            self.setFillColor(colors.HexColor(RED))
            self.setFont("Helvetica-Bold", 8)
            self.drawRightString(A4[0] - 0.75*inch, A4[1] - 0.4*inch, self.doc_title.upper())

    def draw_footer(self, page_count):
        self.setStrokeColor(colors.HexColor(GOLD))
        self.setLineWidth(1)
        self.line(0.75*inch, 0.6*inch, A4[0] - 0.75*inch, 0.6*inch)
        
        self.setFillColor(colors.HexColor(MEDIUM_GRAY))
        self.setFont("Helvetica", 7)
        self.drawString(0.75*inch, 0.4*inch, "Franchise Exit Document - Manaswini Foods Pvt. Ltd.")
        self.drawRightString(A4[0] - 0.75*inch, 0.4*inch, f"Page {self._pageNumber} of {page_count}")


class ExitAgreementGenerator:
    """Generates all exit-related documents"""
    
    def __init__(self, exit_record: dict, franchise: dict):
        self.exit = exit_record
        self.franchise = franchise
        self.styles = self._get_styles()
        self.today = datetime.now()
        
    def _get_styles(self):
        """Create document styles"""
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            'ExitDocTitle', fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold',
            textColor=colors.HexColor(NAVY_BLUE), spaceAfter=10
        ))
        
        styles.add(ParagraphStyle(
            'ExitDocSubtitle', fontSize=11, alignment=TA_CENTER, fontName='Helvetica',
            textColor=colors.HexColor(MEDIUM_GRAY), spaceAfter=15
        ))
        
        styles.add(ParagraphStyle(
            'ExitSectionHead', fontSize=12, fontName='Helvetica-Bold',
            textColor=colors.HexColor(NAVY_BLUE), spaceBefore=15, spaceAfter=8
        ))
        
        styles.add(ParagraphStyle(
            'ExitClauseHead', fontSize=10, fontName='Helvetica-Bold',
            textColor=colors.HexColor(DARK_GRAY), spaceBefore=10, spaceAfter=4
        ))
        
        styles.add(ParagraphStyle(
            'ExitBodyText', fontSize=10, alignment=TA_JUSTIFY, fontName='Helvetica',
            textColor=colors.HexColor(DARK_GRAY), spaceAfter=6, leading=14
        ))
        
        styles.add(ParagraphStyle(
            'ExitSmallText', fontSize=9, alignment=TA_JUSTIFY, fontName='Helvetica',
            textColor=colors.HexColor(MEDIUM_GRAY), spaceAfter=4
        ))
        
        styles.add(ParagraphStyle(
            'ExitCenterText', fontSize=10, alignment=TA_CENTER, fontName='Helvetica',
            textColor=colors.HexColor(DARK_GRAY), spaceAfter=6
        ))
        
        return styles
    
    def _format_currency(self, amount):
        """Format currency for India"""
        country = self.franchise.get("country", "India")
        if country == "India":
            return f"Rs. {amount:,.2f}"
        else:
            return f"AUD ${amount:,.2f}"
    
    def _add_title_section(self, story, title, subtitle=""):
        """Add document title section"""
        story.append(Spacer(1, 0.5*inch))
        
        # Brand name
        story.append(Paragraph("PURNABRAMHA", self.styles['ExitDocTitle']))
        story.append(Paragraph("पूर्णब्रम्ह", ParagraphStyle(
            'MarathiTitle', fontSize=14, alignment=TA_CENTER, fontName=MARATHI_FONT,
            textColor=colors.HexColor(GOLD), spaceAfter=10
        )))
        
        # Document title
        title_table = Table([[title]], colWidths=[5*inch], rowHeights=[0.4*inch])
        title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(NAVY_BLUE)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
        ]))
        story.append(title_table)
        
        if subtitle:
            story.append(Paragraph(subtitle, self.styles['ExitDocSubtitle']))
        
        story.append(Spacer(1, 0.2*inch))
    
    def _add_signature_section(self, story):
        """Add signature section with Franchisor Signatories, Exit Manager, and Franchisee Directors"""
        sigs = self.exit.get("signatures", {})
        
        story.append(Paragraph("<b>SIGNATURES</b>", self.styles['ExitSectionHead']))
        story.append(Spacer(1, 0.15*inch))

        # ---- SECTION 1: FOR FRANCHISOR (Purnabramha) ----
        story.append(Paragraph("<b>FOR FRANCHISOR — MANASWINI FOODS PRIVATE LIMITED</b>", self.styles['ExitClauseHead']))
        
        franchisor_signatories = sigs.get("franchisor_signatories", [])
        # Fallback to old single franchisor if no new-format signatories
        if not franchisor_signatories and sigs.get("franchisor"):
            old = sigs["franchisor"]
            franchisor_signatories = [{
                "signer_name": old.get("signer_name", ""),
                "signer_designation": old.get("signer_designation", "Director"),
                "signature_date": old.get("signature_date", "")
            }]
        
        if franchisor_signatories:
            for s in franchisor_signatories:
                sig_block = [
                    ["", ""],
                    ["_" * 35, ""],
                    [s.get("signer_name", "[Name]"), ""],
                    [s.get("signer_designation", "Director"), ""],
                    [f"Date: {s.get('signature_date', '____________')[:10]}", "(Seal & Signature)"],
                ]
                t = Table(sig_block, colWidths=[3*inch, 2*inch])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor(MEDIUM_GRAY)),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.1*inch))
        else:
            story.append(Paragraph("_" * 35, self.styles['ExitBodyText']))
            story.append(Paragraph("[Franchisor Signatory — Name & Designation]", self.styles['ExitSmallText']))
            story.append(Paragraph("Date: ____________", self.styles['ExitSmallText']))

        story.append(Spacer(1, 0.2*inch))

        # ---- SECTION 2: EXIT MANAGER (Franchisor Side) ----
        story.append(Paragraph("<b>EXIT MANAGER (FRANCHISOR SIDE)</b>", self.styles['ExitClauseHead']))
        
        exit_manager = sigs.get("exit_manager")
        if exit_manager:
            mgr_block = [
                ["", ""],
                ["_" * 35, ""],
                [exit_manager.get("signer_name", "[Name]"), ""],
                [exit_manager.get("signer_designation", "Exit Manager"), ""],
                [f"Date: {exit_manager.get('signature_date', '____________')[:10]}", "(Signature)"],
            ]
            t = Table(mgr_block, colWidths=[3*inch, 2*inch])
            t.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor(MEDIUM_GRAY)),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(t)
        else:
            story.append(Paragraph("_" * 35, self.styles['ExitBodyText']))
            story.append(Paragraph("[Exit Manager — Name & Role]", self.styles['ExitSmallText']))
            story.append(Paragraph("Date: ____________", self.styles['ExitSmallText']))

        story.append(Spacer(1, 0.25*inch))

        # ---- SECTION 3: FOR FRANCHISEE — Directors ----
        legal_name = self.franchise.get("legal_entity_name", "[FRANCHISEE]")
        story.append(Paragraph(f"<b>FOR FRANCHISEE — {legal_name.upper()}</b>", self.styles['ExitClauseHead']))
        
        franchisee_dirs = sigs.get("franchisee_directors", [])
        # Fallback to old single franchisee if no directors
        if not franchisee_dirs and sigs.get("franchisee"):
            old = sigs["franchisee"]
            franchisee_dirs = [{
                "signer_name": old.get("signer_name", ""),
                "signer_designation": old.get("signer_designation", "Director"),
                "signature_date": old.get("signature_date", "")
            }]
        
        if franchisee_dirs:
            for d in franchisee_dirs:
                dir_block = [
                    ["", ""],
                    ["_" * 35, ""],
                    [d.get("signer_name", "[Name]"), ""],
                    [d.get("signer_designation", "Director"), ""],
                    [f"Date: {d.get('signature_date', '____________')[:10]}", "(Signature)"],
                ]
                t = Table(dir_block, colWidths=[3*inch, 2*inch])
                t.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTNAME', (0, 2), (0, 2), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('TEXTCOLOR', (1, -1), (1, -1), colors.HexColor(MEDIUM_GRAY)),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.1*inch))
        else:
            story.append(Paragraph("_" * 35, self.styles['ExitBodyText']))
            story.append(Paragraph("[Director Name & Designation]", self.styles['ExitSmallText']))
            story.append(Paragraph("Date: ____________", self.styles['ExitSmallText']))
    
    # =======================================
    # EXIT AGREEMENT
    # =======================================
    
    def generate_exit_agreement(self) -> bytes:
        """Generate the Exit Agreement PDF"""
        buffer = BytesIO()
        
        def make_canvas(*args, **kwargs):
            return ExitDocumentCanvas(*args, doc_title="Exit Agreement", **kwargs)
        
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        
        # Title
        self._add_title_section(story, "FRANCHISE EXIT AGREEMENT", 
                               f"Exit ID: {self.exit.get('exit_id', '')}")
        
        # Parties
        story.append(Paragraph(f"""
        This Franchise Exit Agreement (\"Agreement\") is entered into on <b>{self.today.strftime('%d %B %Y')}</b>
        """, self.styles['ExitBodyText']))
        
        story.append(Paragraph("<b>BETWEEN:</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph(f"""
        <b>MANASWINI FOODS PRIVATE LIMITED</b> (Franchisor), having its registered office at 
        17/N, Bhagyalakshmi Square, HSR Layout, Bengaluru, Karnataka 560102, India
        """, self.styles['ExitBodyText']))
        
        story.append(Paragraph("<b>AND</b>", self.styles['ExitCenterText']))
        
        story.append(Paragraph(f"""
        <b>{self.franchise.get('legal_entity_name', '[FRANCHISEE NAME]')}</b> (Franchisee), operating the 
        franchise at {self.franchise.get('address', '')}, {self.franchise.get('city', '')}, 
        {self.franchise.get('state', '')} - {self.franchise.get('pincode', '')}, {self.franchise.get('country', 'India')}
        """, self.styles['ExitBodyText']))
        
        # WHEREAS
        story.append(Paragraph("<b>WHEREAS:</b>", self.styles['ExitSectionHead']))
        
        whereas_clauses = [
            f"A. The Franchisee has been operating a Purnabramha franchise under Franchise Code: <b>{self.exit.get('franchise_code', '')}</b>",
            f"B. The Parties have mutually agreed to terminate the franchise relationship with effect from <b>{self.exit.get('effective_date', '')}</b>",
            f"C. The reason for exit is: <b>{self._get_exit_reason_text()}</b>",
            "D. Both Parties wish to formalize the exit process and ensure a clean separation"
        ]
        
        for clause in whereas_clauses:
            story.append(Paragraph(clause, self.styles['ExitBodyText']))
        
        story.append(Paragraph("<b>NOW THEREFORE, THE PARTIES AGREE AS FOLLOWS:</b>", self.styles['ExitSectionHead']))
        
        # Clause 1 - Effective Date
        story.append(Paragraph("<b>1. EFFECTIVE DATE OF CLOSURE</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph(f"""
        The franchise agreement dated {self.franchise.get('agreement_start_date', '[DATE]')} shall stand 
        terminated with effect from <b>{self.exit.get('effective_date', '[DATE]')}</b> (\"Closure Date\").
        """, self.styles['ExitBodyText']))
        
        # Clause 2 - Asset Transfer
        story.append(Paragraph("<b>2. TRANSFER OF PHYSICAL ASSETS TO FRANCHISEE</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph("""
        The Franchisor hereby confirms that all physical assets and inventory at the franchise premises 
        shall be transferred to the Franchisee \"AS IS\" condition. This includes:
        """, self.styles['ExitBodyText']))
        
        assets_list = [
            "• Kitchen equipment and appliances",
            "• Furniture and fixtures",
            "• Utensils, crockery, and machinery",
            "• Remaining food inventory and raw materials",
            "• Packaging materials",
            "• All local operational assets"
        ]
        
        for asset in assets_list:
            story.append(Paragraph(asset, self.styles['ExitSmallText']))
        
        story.append(Paragraph("""
        The Franchisee acknowledges receiving these assets in their present condition and releases 
        the Franchisor from any liability regarding the condition of such assets.
        """, self.styles['ExitBodyText']))
        
        # Clause 3 - Brand Retention
        story.append(Paragraph("<b>3. RETENTION OF BRAND & INTELLECTUAL PROPERTY BY FRANCHISOR</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph("""
        The Franchisee acknowledges and confirms that the following shall remain the exclusive 
        property of the Franchisor:
        """, self.styles['ExitBodyText']))
        
        brand_assets = [
            "• Brand name \"PURNABRAMHA\" and \"पूर्णब्रम्ह\"",
            "• All logos, trademarks, and service marks",
            "• Domain names and websites (purnabramha.com and related)",
            "• Mobile applications and software",
            "• Social media handles and accounts",
            "• Digital listings (Google Business, Zomato, Swiggy, etc.)",
            "• All branding materials using the Purnabramha identity",
            "• Proprietary recipes and operational procedures"
        ]
        
        for asset in brand_assets:
            story.append(Paragraph(asset, self.styles['ExitSmallText']))
        
        story.append(Paragraph("""
        The Franchisee agrees to immediately cease using the Purnabramha brand, name, or any 
        associated intellectual property from the Closure Date.
        """, self.styles['ExitBodyText']))
        
        # Clause 4 - Financial Settlement
        story.append(Paragraph("<b>4. FINANCIAL SETTLEMENT</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph("""
        All financial matters shall be settled as per the Financial Settlement Sheet attached hereto. 
        Both Parties acknowledge that:
        """, self.styles['ExitBodyText']))
        
        story.append(Paragraph("""
        a) All staff salaries for the current month shall be cleared<br/>
        b) Shop rental for the current month shall be settled<br/>
        c) All vendor payments shall be cleared<br/>
        d) All utility bills shall be paid<br/>
        e) Working capital balance, if any, shall be distributed as per agreement
        """, self.styles['ExitBodyText']))
        
        # Clause 5 - Non-Compete
        story.append(Paragraph("<b>5. NON-COMPETE CLAUSE</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph("""
        The Franchisee agrees not to operate any business that directly competes with Purnabramha 
        (Maharashtrian cuisine restaurant) within a radius of 5 kilometers from the closed franchise 
        location for a period of 2 years from the Closure Date.
        """, self.styles['ExitBodyText']))
        
        # Clause 6 - Confidentiality
        story.append(Paragraph("<b>6. CONFIDENTIALITY</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph("""
        The Franchisee agrees to maintain confidentiality of all proprietary information, including 
        recipes, operational procedures, and business information, for a period of 5 years from 
        the Closure Date.
        """, self.styles['ExitBodyText']))
        
        # Clause 7 - Release
        story.append(Paragraph("<b>7. MUTUAL RELEASE</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph("""
        Upon completion of all obligations under this Agreement, both Parties release each other 
        from any further claims, demands, or liabilities arising from the franchise relationship.
        """, self.styles['ExitBodyText']))
        
        # Clause 8 - Governing Law
        story.append(Paragraph("<b>8. GOVERNING LAW</b>", self.styles['ExitClauseHead']))
        story.append(Paragraph("""
        This Agreement shall be governed by the laws of India. Any disputes shall be subject to 
        the exclusive jurisdiction of the courts in Bengaluru, Karnataka.
        """, self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.5*inch))
        
        # Signatures
        self._add_signature_section(story)
        
        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _get_exit_reason_text(self):
        """Get readable exit reason"""
        reasons = {
            "losses": "Continuous Operational Losses",
            "voluntary": "Voluntary Closure by Franchisee",
            "mutual_decision": "Mutual Decision",
            "breach": "Breach of Agreement",
            "other": "Other Reasons"
        }
        reason = self.exit.get("exit_reason", "other")
        text = reasons.get(reason, reason)
        details = self.exit.get("exit_reason_details", "")
        if details:
            text += f" - {details}"
        return text
    
    # =======================================
    # HANDOVER REPORT
    # =======================================
    
    def generate_handover_report(self) -> bytes:
        """Generate the Asset Handover Report PDF"""
        buffer = BytesIO()
        
        def make_canvas(*args, **kwargs):
            return ExitDocumentCanvas(*args, doc_title="Handover Report", **kwargs)
        
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        
        # Title
        self._add_title_section(story, "ASSET HANDOVER REPORT",
                               f"Franchise: {self.exit.get('franchise_code', '')}")
        
        # Details
        story.append(Paragraph(f"""
        <b>Handover Date:</b> {self.today.strftime('%d %B %Y')}<br/>
        <b>Franchise Code:</b> {self.exit.get('franchise_code', '')}<br/>
        <b>Franchise Name:</b> {self.exit.get('franchise_name', '')}<br/>
        <b>Location:</b> {self.franchise.get('address', '')}, {self.franchise.get('city', '')}
        """, self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.2*inch))
        
        asset_data = self.exit.get("asset_handover", {})
        
        # Asset categories
        categories = [
            ("KITCHEN EQUIPMENT", "kitchen_equipment"),
            ("FURNITURE & FIXTURES", "furniture_fixtures"),
            ("UTENSILS & MACHINERY", "utensils_machinery"),
            ("FOOD INVENTORY", "food_inventory"),
            ("PACKAGING MATERIALS", "packaging_materials"),
            ("OTHER ASSETS", "other_assets")
        ]
        
        for cat_name, cat_key in categories:
            story.append(Paragraph(f"<b>{cat_name}</b>", self.styles['ExitClauseHead']))
            
            items = asset_data.get(cat_key, [])
            if items:
                table_data = [["Item", "Quantity", "Condition", "Remarks"]]
                for item in items:
                    table_data.append([
                        item.get("name", ""),
                        str(item.get("quantity", "")),
                        item.get("condition", ""),
                        item.get("remarks", "")
                    ])
                
                asset_table = Table(table_data, colWidths=[2*inch, 1*inch, 1.2*inch, 1.8*inch])
                asset_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(NAVY_BLUE)),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(MEDIUM_GRAY)),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(asset_table)
            else:
                story.append(Paragraph("No items recorded", self.styles['ExitSmallText']))
            
            story.append(Spacer(1, 0.1*inch))
        
        # Condition Notes
        if asset_data.get("condition_notes"):
            story.append(Paragraph("<b>GENERAL CONDITION NOTES:</b>", self.styles['ExitClauseHead']))
            story.append(Paragraph(asset_data.get("condition_notes", ""), self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Acknowledgment
        story.append(Paragraph("<b>ACKNOWLEDGMENT</b>", self.styles['ExitSectionHead']))
        story.append(Paragraph("""
        Both Parties hereby acknowledge that the above assets have been inspected and handed over 
        to the Franchisee in the condition as described above. The Franchisee accepts these assets 
        \"AS IS\" and releases the Franchisor from any claims regarding the condition of these assets.
        """, self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Signatures
        self._add_signature_section(story)
        
        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer.getvalue()
    
    # =======================================
    # SETTLEMENT SHEET
    # =======================================
    
    def generate_settlement_sheet(self) -> bytes:
        """Generate the Financial Settlement Sheet PDF"""
        buffer = BytesIO()
        
        def make_canvas(*args, **kwargs):
            return ExitDocumentCanvas(*args, doc_title="Settlement Sheet", **kwargs)
        
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        
        # Title
        self._add_title_section(story, "FINANCIAL SETTLEMENT SHEET",
                               f"Franchise: {self.exit.get('franchise_code', '')}")
        
        settlement = self.exit.get("financial_settlement", {})
        
        # Settlement details table
        story.append(Paragraph("<b>SETTLEMENT DETAILS</b>", self.styles['ExitSectionHead']))
        
        settlement_data = [
            ["Description", "Amount"],
            ["Working Capital Balance (Credit)", self._format_currency(settlement.get("working_capital_balance", 0))],
            ["", ""],
            ["DEDUCTIONS:", ""],
            ["Staff Salary (Current Month)", f"(-) {self._format_currency(settlement.get('staff_salary_current', 0))}"],
            ["Shop Rental (Current Month)", f"(-) {self._format_currency(settlement.get('shop_rental_current', 0))}"],
            ["Vendor Payments", f"(-) {self._format_currency(settlement.get('vendor_payments', 0))}"],
            ["Utility Bills", f"(-) {self._format_currency(settlement.get('utility_bills', 0))}"],
            ["Other Dues", f"(-) {self._format_currency(settlement.get('other_dues', 0))}"],
            ["", ""],
            ["NET SETTLEMENT AMOUNT", self._format_currency(settlement.get("total_settlement", 0))]
        ]
        
        settlement_table = Table(settlement_data, colWidths=[4*inch, 2*inch])
        settlement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(NAVY_BLUE)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor(MEDIUM_GRAY)),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(LIGHT_GRAY)),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor(NAVY_BLUE)),
        ]))
        story.append(settlement_table)
        
        story.append(Spacer(1, 0.2*inch))
        
        # Settlement notes
        if settlement.get("settlement_notes"):
            story.append(Paragraph("<b>NOTES:</b>", self.styles['ExitClauseHead']))
            story.append(Paragraph(settlement.get("settlement_notes", ""), self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Settlement status
        total = settlement.get("total_settlement", 0)
        if total > 0:
            story.append(Paragraph(f"""
            <b>Settlement Status:</b> The Franchisor shall pay {self._format_currency(total)} to the 
            Franchisee within 7 working days of signing this settlement sheet.
            """, self.styles['ExitBodyText']))
        elif total < 0:
            story.append(Paragraph(f"""
            <b>Settlement Status:</b> The Franchisee owes {self._format_currency(abs(total))} to the 
            Franchisor. This amount shall be settled before the exit process is completed.
            """, self.styles['ExitBodyText']))
        else:
            story.append(Paragraph("""
            <b>Settlement Status:</b> No amounts are due to either party. The financial settlement 
            is considered complete.
            """, self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Acknowledgment
        story.append(Paragraph("<b>ACKNOWLEDGMENT</b>", self.styles['ExitSectionHead']))
        story.append(Paragraph("""
        Both Parties have reviewed the above financial settlement and confirm that the amounts are 
        accurate and accepted. Upon signing, both Parties agree that this settlement is final and 
        binding.
        """, self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Signatures
        self._add_signature_section(story)
        
        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer.getvalue()
    
    # =======================================
    # EXIT CERTIFICATE
    # =======================================
    
    def generate_exit_certificate(self) -> bytes:
        """Generate the Exit Completion Certificate PDF"""
        buffer = BytesIO()
        
        def make_canvas(*args, **kwargs):
            return ExitDocumentCanvas(*args, doc_title="Exit Certificate", **kwargs)
        
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        story = []
        
        # Decorative border
        story.append(Spacer(1, 0.3*inch))
        
        # Certificate header
        header_table = Table([["FRANCHISE EXIT COMPLETION CERTIFICATE"]], 
                            colWidths=[6*inch], rowHeights=[0.5*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(NAVY_BLUE)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 16),
        ]))
        story.append(header_table)
        
        story.append(Spacer(1, 0.1*inch))
        
        # Marathi title
        story.append(Paragraph("फ्रँचाइज एक्झिट पूर्णता प्रमाणपत्र", ParagraphStyle(
            'MarathiCert', fontSize=14, alignment=TA_CENTER, fontName=MARATHI_FONT,
            textColor=colors.HexColor(GOLD), spaceAfter=20
        )))
        
        # Certificate number
        story.append(Paragraph(f"""
        <b>Certificate No:</b> CERT-{self.exit.get('exit_id', '')}<br/>
        <b>Date of Issue:</b> {self.today.strftime('%d %B %Y')}
        """, self.styles['ExitCenterText']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Certificate body
        story.append(Paragraph("<b>THIS IS TO CERTIFY THAT:</b>", self.styles['ExitSectionHead']))
        
        story.append(Paragraph(f"""
        The franchise agreement between <b>MANASWINI FOODS PRIVATE LIMITED</b> (Franchisor) and 
        <b>{self.franchise.get('legal_entity_name', '[FRANCHISEE]')}</b> (Franchisee) for the 
        Purnabramha franchise located at:
        """, self.styles['ExitBodyText']))
        
        story.append(Paragraph(f"""
        <b>{self.franchise.get('address', '')}, {self.franchise.get('city', '')}, 
        {self.franchise.get('state', '')} - {self.franchise.get('pincode', '')}, 
        {self.franchise.get('country', 'India')}</b>
        """, self.styles['ExitCenterText']))
        
        story.append(Paragraph(f"""
        Operating under Franchise Code: <b>{self.exit.get('franchise_code', '')}</b>
        """, self.styles['ExitCenterText']))
        
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("""
        has been <b>formally and completely closed</b> with effect from the date mentioned below, 
        and the following conditions have been fulfilled:
        """, self.styles['ExitBodyText']))
        
        # Completion checklist
        completion_items = [
            "✓ The Franchise Agreement has been formally terminated",
            "✓ All physical assets and inventory have been transferred to the Franchisee",
            "✓ Brand name, intellectual property, and digital assets remain with the Franchisor",
            "✓ All financial settlements have been completed",
            "✓ No financial liabilities remain between the Parties",
            "✓ All compliance requirements have been fulfilled"
        ]
        
        for item in completion_items:
            story.append(Paragraph(item, ParagraphStyle(
                'CheckItem', fontSize=10, fontName='Helvetica',
                textColor=colors.HexColor(DARK_GRAY), spaceAfter=4, leftIndent=20
            )))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Key dates
        story.append(Paragraph("<b>KEY DATES:</b>", self.styles['ExitClauseHead']))
        
        dates_data = [
            ["Original Agreement Date:", self.franchise.get("agreement_start_date", "N/A")],
            ["Exit Initiation Date:", self.exit.get("initiated_at", "N/A")[:10] if self.exit.get("initiated_at") else "N/A"],
            ["Effective Closure Date:", self.exit.get("effective_date", "N/A")],
            ["Certificate Issue Date:", self.today.strftime('%d %B %Y')]
        ]
        
        dates_table = Table(dates_data, colWidths=[2.5*inch, 3*inch])
        dates_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(dates_table)
        
        story.append(Spacer(1, 0.3*inch))
        
        # Final declaration
        story.append(Paragraph("""
        Both Parties confirm that all obligations under the franchise agreement and exit agreement 
        have been fulfilled, and neither Party has any further claims against the other in relation 
        to the franchise operations.
        """, self.styles['ExitBodyText']))
        
        story.append(Spacer(1, 0.3*inch))
        
        # Signatures
        self._add_signature_section(story)
        
        story.append(Spacer(1, 0.3*inch))
        
        # Footer note
        story.append(Paragraph("""
        This certificate is issued by Manaswini Foods Private Limited as a formal record of the 
        franchise exit completion. This document serves as proof that the franchise relationship 
        has been terminated in accordance with the agreed terms and conditions.
        """, self.styles['ExitSmallText']))
        
        doc.build(story, canvasmaker=make_canvas)
        buffer.seek(0)
        return buffer.getvalue()

# =======================================
# Comprehensive Franchise Agreement Generator
# Generates 60+ page professional FOCO Agreements
# Supports India and Australia models
# =======================================

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, 
    PageBreak, ListFlowable, ListItem, KeepTogether
)
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import logging
import os

logger = logging.getLogger(__name__)

# Register Devanagari font for Marathi text
try:
    # Try Noto Sans Devanagari first
    pdfmetrics.registerFont(TTFont('NotoDevanagari', '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('NotoDevanagari-Bold', '/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf'))
    MARATHI_FONT = 'NotoDevanagari'
    MARATHI_FONT_BOLD = 'NotoDevanagari-Bold'
except:
    try:
        # Fallback to Lohit
        pdfmetrics.registerFont(TTFont('LohitDevanagari', '/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf'))
        MARATHI_FONT = 'LohitDevanagari'
        MARATHI_FONT_BOLD = 'LohitDevanagari'
    except:
        MARATHI_FONT = 'Helvetica'
        MARATHI_FONT_BOLD = 'Helvetica-Bold'

# =======================================
# CONSTANTS
# =======================================

FRANCHISE_TENURE_YEARS = 7
REVENUE_SHARE_PERCENTAGE = 15
WORKING_CAPITAL_THRESHOLD = 50
MONTHLY_SERVICE_CONTRACT = 10000
CONFIDENTIALITY_SURVIVAL_YEARS = 2
NON_COMPETE_RADIUS_KM = 25
NON_COMPETE_POST_TERM_YEARS = 2

# Professional Color Palette - Clean and Elegant
NAVY_BLUE = "#1B365D"
GOLD = "#B8860B"  
DARK_GRAY = "#333333"
MEDIUM_GRAY = "#666666"
LIGHT_GRAY = "#F5F5F5"

# =======================================
# HELPER FUNCTIONS
# =======================================

def format_currency(amount, country="India"):
    """Format currency based on country"""
    if country == "India":
        return f"₹{amount:,.0f}"
    elif country == "Australia":
        return f"AUD ${amount:,.2f}"
    else:
        return f"${amount:,.2f}"

def format_currency_words(amount, country="India"):
    """Convert amount to words"""
    def num_to_words(num):
        ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
                "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
                "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
        
        if num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + (" " + ones[num % 10] if num % 10 else "")
        elif num < 1000:
            return ones[num // 100] + " Hundred" + (" and " + num_to_words(num % 100) if num % 100 else "")
        elif num < 100000:
            return num_to_words(num // 1000) + " Thousand" + (" " + num_to_words(num % 1000) if num % 1000 else "")
        elif num < 10000000:
            return num_to_words(num // 100000) + " Lakh" + (" " + num_to_words(num % 100000) if num % 100000 else "")
        else:
            return num_to_words(num // 10000000) + " Crore" + (" " + num_to_words(num % 10000000) if num % 10000000 else "")
    
    if country == "India":
        return f"{num_to_words(int(amount))} Rupees Only"
    elif country == "Australia":
        return f"{num_to_words(int(amount))} Australian Dollars Only"
    else:
        return f"{num_to_words(int(amount))} Dollars Only"

def get_ordinal(n):
    """Get ordinal suffix for a number"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + suffix

# =======================================
# PAGE NUMBER HANDLER - CLEAN PROFESSIONAL STYLE
# =======================================

class NumberedCanvas(canvas.Canvas):
    """Canvas with clean, professional headers and footers"""
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

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
            # Simple elegant header line
            self.setStrokeColor(colors.HexColor(GOLD))
            self.setLineWidth(1.5)
            self.line(0.75*inch, A4[1] - 0.5*inch, A4[0] - 0.75*inch, A4[1] - 0.5*inch)
            
            # Brand name - left
            self.setFillColor(colors.HexColor(NAVY_BLUE))
            self.setFont("Helvetica-Bold", 9)
            self.drawString(0.75*inch, A4[1] - 0.4*inch, "PURNABRAMHA")
            
            # Confidential - right
            self.setFillColor(colors.HexColor(MEDIUM_GRAY))
            self.setFont("Helvetica", 8)
            self.drawRightString(A4[0] - 0.75*inch, A4[1] - 0.4*inch, "CONFIDENTIAL")

    def draw_footer(self, page_count):
        # Footer line
        self.setStrokeColor(colors.HexColor(GOLD))
        self.setLineWidth(1)
        self.line(0.75*inch, 0.6*inch, A4[0] - 0.75*inch, 0.6*inch)
        
        # Footer text
        self.setFillColor(colors.HexColor(MEDIUM_GRAY))
        self.setFont("Helvetica", 7)
        self.drawString(0.75*inch, 0.4*inch, "Franchise Agreement - Manaswini Foods Pvt. Ltd.")
        
        # Page number - right
        self.setFont("Helvetica", 8)
        self.drawRightString(A4[0] - 0.75*inch, 0.4*inch, f"Page {self._pageNumber} of {page_count}")

# =======================================
# STYLE DEFINITIONS
# =======================================

def get_styles():
    """Create clean, professional paragraph styles"""
    styles = getSampleStyleSheet()
    
    # Title styles - Clean and Professional
    styles.add(ParagraphStyle(
        'AgrMainTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor(NAVY_BLUE)
    ))
    
    styles.add(ParagraphStyle(
        'AgrSubTitle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=15,
        fontName='Helvetica-Oblique',
        textColor=colors.HexColor(MEDIUM_GRAY)
    ))
    
    # Section headings - Professional Navy Blue
    styles.add(ParagraphStyle(
        'AgrSectionHeading',
        parent=styles['Heading1'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor(NAVY_BLUE)
    ))
    
    styles.add(ParagraphStyle(
        'AgrSubSectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        spaceBefore=12,
        spaceAfter=6,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor(DARK_GRAY)
    ))
    
    styles.add(ParagraphStyle(
        'AgrClauseHeading',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=8,
        spaceAfter=4,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor(DARK_GRAY)
    ))
    
    # Body text styles
    styles.add(ParagraphStyle(
        'AgrBodyText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        'AgrBodyTextIndent',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=14,
        leftIndent=20,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        'AgrBulletText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
        leading=13,
        leftIndent=30,
        bulletIndent=15,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        'AgrSmallText',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=4,
        alignment=TA_JUSTIFY,
        leading=12,
        fontName='Helvetica'
    ))
    
    # Special styles
    styles.add(ParagraphStyle(
        'AgrCenterBold',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=10
    ))
    
    styles.add(ParagraphStyle(
        'AgrRecital',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14,
        leftIndent=0,
        fontName='Helvetica'
    ))
    
    styles.add(ParagraphStyle(
        'AgrScheduleTitle',
        parent=styles['Heading1'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceBefore=15,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor(NAVY_BLUE)
    ))
    
    styles.add(ParagraphStyle(
        'AgrTableHeader',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        'AgrSignatureText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        fontName='Helvetica'
    ))
    
    return styles

# =======================================
# MAIN AGREEMENT GENERATOR CLASS
# =======================================

class FranchiseAgreementGenerator:
    """Generates comprehensive franchise agreements"""
    
    def __init__(self, franchise_data: dict):
        self.data = franchise_data
        self.country = franchise_data.get("country", "India")
        self.is_india = self.country == "India"
        self.is_australia = self.country == "Australia"
        self.styles = get_styles()
        self.story = []
        
        # Extract key data
        self.franchise_code = franchise_data.get("franchise_code", "")
        self.franchise_name = franchise_data.get("franchise_name", "")
        self.legal_entity_name = franchise_data.get("legal_entity_name", "")
        self.franchise_type = franchise_data.get("franchise_type", "Sanskriti")
        self.franchise_fee = franchise_data.get("franchise_fee", 0)
        self.working_capital = franchise_data.get("working_capital", 900000)
        self.revenue_share = franchise_data.get("revenue_share_percentage", 15)
        self.service_fee = franchise_data.get("service_contract_fee", 10000)
        self.directors = franchise_data.get("directors", [])
        self.setup_costs = franchise_data.get("setup_costs", {})
        self.address = franchise_data.get("address", "")
        self.city = franchise_data.get("city", "")
        self.state = franchise_data.get("state", "")
        self.pincode = franchise_data.get("pincode", "")
        
        # Dates
        self.today = datetime.now()
        self.agreement_date = self.today.strftime("%d %B %Y")
        self.ops_start = franchise_data.get("operations_start_date", "")
        self.agreement_start = franchise_data.get("agreement_start_date", self.ops_start)
        self.agreement_end = franchise_data.get("agreement_end_date", "")
        
        # Calculate total setup costs
        self.total_setup = sum([
            self.setup_costs.get("shop_security_deposit", 0),
            self.setup_costs.get("first_month_rent", 0),
            self.setup_costs.get("initial_salary_fund", 0),
            self.setup_costs.get("initial_grocery_cost", 0)
        ])
        
        # Set franchisor details based on country
        self._set_franchisor_details()
        
    def _set_franchisor_details(self):
        """Set franchisor details based on country"""
        if self.is_india:
            self.franchisor_name = "MANASWINI FOODS PRIVATE LIMITED"
            self.franchisor_short = "MFPL"
            self.franchisor_address = "17/N, Bhagyalakshmi Square, 18th Cross Rd, Sector 3, HSR Layout, Bengaluru, Karnataka 560102, India"
            self.franchisor_cin = "U55101KA2016PTC091234"
            self.jurisdiction = self.city or "Bengaluru"
            self.governing_law = "India"
            self.arbitration_act = "Arbitration and Conciliation Act 1996"
        elif self.is_australia:
            self.franchisor_name = "PURNABRAMHA LLC PTY LTD"
            self.franchisor_short = "PB LLC"
            self.franchisor_address = "Level 1, 123 Collins Street, Melbourne VIC 3000, Australia"
            self.franchisor_cin = "ACN 123 456 789"
            self.jurisdiction = self.city or "Perth"
            self.governing_law = "Western Australia"
            self.arbitration_act = "Commercial Arbitration Act 2012 (WA)"
        else:
            self.franchisor_name = "PURNABRAMHA INTERNATIONAL LLC"
            self.franchisor_short = "PB INT"
            self.franchisor_address = "International Operations Office"
            self.franchisor_cin = ""
            self.jurisdiction = self.city or self.country
            self.governing_law = self.country
            self.arbitration_act = "applicable arbitration laws"
    
    def generate(self) -> bytes:
        """Generate the complete agreement PDF"""
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build all sections
        self._build_title_page()
        self._build_table_of_contents()
        self._build_parties_section()
        self._build_recitals()
        self._build_definitions()
        self._build_agreement_structure()
        self._build_operational_framework()
        self._build_financial_framework()
        self._build_ip_section()
        self._build_legal_liability()
        self._build_term_termination()
        self._build_dispute_resolution()
        self._build_schedules()
        self._build_annexures()
        self._build_signature_section()
        
        # Build PDF with custom canvas for page numbers
        doc.build(self.story, canvasmaker=NumberedCanvas)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _add_section_heading(self, text: str, number: str = ""):
        """Add a clean section heading"""
        if number:
            full_text = f"{number}. {text}"
        else:
            full_text = text
        self.story.append(Paragraph(full_text, self.styles['AgrSectionHeading']))
    
    def _add_subsection_heading(self, text: str, number: str = ""):
        """Add a subsection heading"""
        if number:
            full_text = f"{number} {text}"
        else:
            full_text = text
        self.story.append(Paragraph(full_text, self.styles['AgrSubSectionHeading']))
    
    def _add_clause(self, text: str, number: str = ""):
        """Add a clause heading"""
        if number:
            full_text = f"{number} {text}"
        else:
            full_text = text
        self.story.append(Paragraph(full_text, self.styles['AgrClauseHeading']))
    
    def _add_body(self, text: str, indent: bool = False):
        """Add body text"""
        style = self.styles['AgrBodyTextIndent'] if indent else self.styles['AgrBodyText']
        self.story.append(Paragraph(text, style))
    
    def _add_bullet(self, text: str):
        """Add a bullet point"""
        self.story.append(Paragraph(f"• {text}", self.styles['AgrBulletText']))
    
    def _add_spacer(self, height: float = 0.15):
        """Add vertical space"""
        self.story.append(Spacer(1, height*inch))
    
    def _add_page_break(self):
        """Add a page break"""
        self.story.append(PageBreak())
    
    # =======================================
    # SECTION BUILDERS
    # =======================================
    
    def _build_title_page(self):
        """Build a clean, professional title page"""
        
        self._add_spacer(0.8)
        
        # Brand Name - Large and Clean
        self.story.append(Paragraph(
            "PURNABRAMHA",
            ParagraphStyle('BrandTitle', fontSize=28, alignment=TA_CENTER,
                          fontName='Helvetica-Bold', textColor=colors.HexColor(NAVY_BLUE),
                          spaceAfter=8)
        ))
        
        # Marathi Name with proper font
        self.story.append(Paragraph(
            "पूर्णब्रम्ह",
            ParagraphStyle('MarathiBrand', fontSize=18, alignment=TA_CENTER,
                          fontName=MARATHI_FONT_BOLD, textColor=colors.HexColor(GOLD),
                          spaceAfter=5)
        ))
        
        # English tagline
        self.story.append(Paragraph(
            "The Largest Authentic Maharashtrian Restaurant Chain",
            ParagraphStyle('Tagline', fontSize=10, alignment=TA_CENTER,
                          fontName='Helvetica-Oblique', textColor=colors.HexColor(MEDIUM_GRAY),
                          spaceAfter=20)
        ))
        
        # Simple horizontal line
        line_table = Table([[""]], colWidths=[3*inch], rowHeights=[2])
        line_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(GOLD)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        self.story.append(line_table)
        
        self._add_spacer(0.5)
        
        # Main Title Box
        title_table = Table([["FRANCHISE AGREEMENT"]], colWidths=[5*inch], rowHeights=[0.5*inch])
        title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(NAVY_BLUE)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 18),
        ]))
        self.story.append(title_table)
        
        self._add_spacer(0.15)
        
        # Subtitle
        self.story.append(Paragraph(
            "(FOCO Model - Franchise Owned, Company Operated)",
            ParagraphStyle('FocoSubtitle', fontSize=10, alignment=TA_CENTER,
                          fontName='Helvetica', textColor=colors.HexColor(DARK_GRAY),
                          spaceAfter=5)
        ))
        
        # Marathi subtitle with proper font
        self.story.append(Paragraph(
            "फ्रँचाइज मालकी - कंपनी संचालित मॉडेल",
            ParagraphStyle('MarathiSubtitle', fontSize=9, alignment=TA_CENTER,
                          fontName=MARATHI_FONT, textColor=colors.HexColor(MEDIUM_GRAY),
                          spaceAfter=20)
        ))
        
        self._add_spacer(0.2)
        
        # Agreement Reference
        self.story.append(Paragraph(
            f"<b>Agreement Reference:</b> FA-{self.franchise_code}-{self.today.strftime('%Y%m%d')}",
            ParagraphStyle('RefStyle', fontSize=10, alignment=TA_CENTER,
                          fontName='Helvetica', textColor=colors.HexColor(DARK_GRAY),
                          spaceAfter=20)
        ))
        
        # Parties section - Clean table format
        parties_data = [
            [Paragraph("<b>BETWEEN</b>", ParagraphStyle('BetweenStyle', fontSize=11, 
                      alignment=TA_CENTER, textColor=colors.HexColor(NAVY_BLUE)))],
            [""],
            [Paragraph(f"<b>{self.franchisor_name}</b>", ParagraphStyle('PartyStyle', fontSize=11, 
                      alignment=TA_CENTER, textColor=colors.HexColor(DARK_GRAY)))],
            [Paragraph("(hereinafter referred to as the \"FRANCHISOR\")", ParagraphStyle('PartyDesc', 
                      fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor(MEDIUM_GRAY)))],
            [""],
            [Paragraph("<b>AND</b>", ParagraphStyle('AndStyle', fontSize=11, 
                      alignment=TA_CENTER, textColor=colors.HexColor(GOLD)))],
            [""],
            [Paragraph(f"<b>{self.legal_entity_name or '[FRANCHISEE ENTITY NAME]'}</b>", 
                      ParagraphStyle('PartyStyle2', fontSize=11, alignment=TA_CENTER, 
                      textColor=colors.HexColor(DARK_GRAY)))],
            [Paragraph("(hereinafter referred to as the \"FRANCHISEE\")", ParagraphStyle('PartyDesc2', 
                      fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor(MEDIUM_GRAY)))]
        ]
        
        parties_table = Table(parties_data, colWidths=[5*inch])
        parties_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(MEDIUM_GRAY)),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(LIGHT_GRAY)),
        ]))
        self.story.append(parties_table)
        
        self._add_spacer(0.3)
        
        # Franchise details - Clean table
        details_data = [
            ["Franchise Code:", self.franchise_code],
            ["Franchise Type:", self.franchise_type],
            ["Location:", f"{self.city}, {self.state}, {self.country}"],
            ["Agreement Date:", self.agreement_date],
            ["Term:", f"{FRANCHISE_TENURE_YEARS} Years"]
        ]
        
        details_table = Table(details_data, colWidths=[1.5*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor(DARK_GRAY)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        self.story.append(details_table)
        
        self._add_spacer(0.5)
        
        # Confidential notice - Simple and professional
        conf_table = Table([["CONFIDENTIAL DOCUMENT"]], colWidths=[3*inch], rowHeights=[0.3*inch])
        conf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(NAVY_BLUE)),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        self.story.append(conf_table)
        
        # Marathi confidential with proper font
        self._add_spacer(0.1)
        self.story.append(Paragraph(
            "गोपनीय दस्तावेज",
            ParagraphStyle('MarathiConf', fontSize=10, alignment=TA_CENTER,
                          fontName=MARATHI_FONT, textColor=colors.HexColor(MEDIUM_GRAY),
                          spaceAfter=10)
        ))
        
        self.story.append(Paragraph(
            "This document contains proprietary and confidential information. "
            "Unauthorized copying, distribution, or disclosure is strictly prohibited.",
            ParagraphStyle('ConfNotice', fontSize=8, alignment=TA_CENTER,
                          fontName='Helvetica', textColor=colors.HexColor(MEDIUM_GRAY))
        ))
        
        self._add_page_break()
    
    def _build_table_of_contents(self):
        """Build table of contents"""
        self.story.append(Paragraph("TABLE OF CONTENTS", self.styles['AgrMainTitle']))
        self._add_spacer(0.3)
        
        toc_items = [
            ("1.", "DEFINITIONS", "3"),
            ("2.", "AGREEMENT STRUCTURE & BUSINESS TRANSFER", "8"),
            ("3.", "OPERATIONAL STRUCTURE & CONTROL FRAMEWORK", "14"),
            ("4.", "FINANCIAL FRAMEWORK, PROFIT SHARE & EXIT", "24"),
            ("5.", "INTELLECTUAL PROPERTY & CONFIDENTIALITY", "34"),
            ("6.", "LEGAL LIABILITY, INSURANCE & COMPLIANCE", "40"),
            ("7.", "TERM, RENEWAL & TERMINATION", "46"),
            ("8.", "DISPUTE RESOLUTION & MISCELLANEOUS", "55"),
            ("", "", ""),
            ("", "SCHEDULES", ""),
            ("A.", "Business Asset & Goodwill Valuation", "60"),
            ("B.", "Bank Account & Financial Control Structure", "62"),
            ("C.", "Royalty, Profit Share & Honorarium Matrix", "62"),
            ("D.", "Operational Control & SOP Framework", "63"),
            ("E.", "Visa & Staff Deployment Plan", "64"),
            ("F.", "Exit & Sale Valuation Protocol", "64"),
            ("G.", "Confidential Information & IP Document List", "65"),
            ("H.", "Non-Compete Zones", "65"),
            ("", "", ""),
            ("", "ANNEXURES", ""),
            ("A.", "Shop Deposit - Refund & Exit Understanding", "67"),
        ]
        
        toc_data = []
        for num, title, page in toc_items:
            if num == "" and title == "":
                toc_data.append(["", "", ""])
            elif title == "SCHEDULES" or title == "ANNEXURES":
                toc_data.append([Paragraph(f"<b>{title}</b>", self.styles['AgrSmallText']), "", ""])
            else:
                toc_data.append([num, title, page])
        
        toc_table = Table(toc_data, colWidths=[0.5*inch, 4.5*inch, 0.5*inch])
        toc_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (1, 0), (1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ]))
        self.story.append(toc_table)
        
        self._add_page_break()
    
    def _build_parties_section(self):
        """Build the parties identification section"""
        self.story.append(Paragraph("FRANCHISE AGREEMENT BETWEEN THE PARTIES", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self._add_body(f"THIS AGREEMENT (the \"Agreement\") is made on this <b>{self.agreement_date}</b>")
        self._add_spacer(0.1)
        
        self.story.append(Paragraph("<b>BETWEEN:</b>", self.styles['AgrClauseHeading']))
        
        # Franchisor details
        if self.is_australia:
            franchisor_text = f"""
            <b>M/s. {self.franchisor_name}</b>, a company incorporated under the Corporations Act 2001 
            ({self.franchisor_cin}) (which expression shall, unless repugnant to the meaning and context thereof, 
            be deemed to mean and include its successors and assignees), having its registered office at 
            {self.franchisor_address}, through its authorized Directors (the "<b>FRANCHISOR</b>" or "<b>PURNABRAMHA LLC PTY LTD</b>" 
            or "<b>PB LLC</b>") of the <b>ONE PART</b>;
            """
        else:
            franchisor_text = f"""
            <b>M/s. {self.franchisor_name}</b>, a company incorporated under the provisions of the Companies Act, 2013 
            (CIN: {self.franchisor_cin}) (which expression shall, unless repugnant to the meaning and context thereof, 
            be deemed to mean and include its successors and assignees), having its registered office at 
            {self.franchisor_address}, through its Directors Mrs. Jayanti Pranav Kathale and Mr. Sandeep Gadhwal 
            (the "<b>FRANCHISOR</b>" or "<b>MFPL</b>" or "<b>PURNABRAMHA</b>") of the <b>ONE PART</b>;
            """
        self._add_body(franchisor_text)
        
        self._add_spacer(0.1)
        self.story.append(Paragraph("<b>AND</b>", self.styles['AgrCenterBold']))
        self._add_spacer(0.1)
        
        # Franchisee details
        directors_names = ", ".join([d.get("name", "") for d in self.directors if d.get("name")])
        full_address = f"{self.address}, {self.city}, {self.state} - {self.pincode}, {self.country}"
        
        if self.is_australia:
            franchisee_text = f"""
            <b>M/s. {self.legal_entity_name or '[FRANCHISEE ENTITY NAME]'}</b>, a company incorporated under the 
            Corporations Act 2001, having its registered office at {full_address}, hereinafter referred to as the 
            "<b>FRANCHISEE</b>" through its Directors/Partners {directors_names or '[DIRECTOR NAMES]'} 
            (which expression shall, unless repugnant to the subject or context thereof, include its successors and assigns) 
            of the <b>OTHER PART</b>.
            """
        else:
            franchisee_text = f"""
            <b>M/s. {self.legal_entity_name or '[FRANCHISEE ENTITY NAME]'}</b>, a company incorporated under the 
            provisions of the Companies Act, 2013, having its registered office at {full_address}, hereinafter referred 
            to as the "<b>FRANCHISEE</b>" through its Directors/Partners {directors_names or '[DIRECTOR NAMES]'} 
            (which expression shall, unless repugnant to the subject or context thereof, include its successors and assigns) 
            of the <b>OTHER PART</b>.
            """
        self._add_body(franchisee_text)
        
        self._add_spacer(0.15)
        self._add_body("The Franchisor and Franchisee herein shall be collectively referred to as \"<b>Parties</b>\" and individually referred to as \"<b>Party</b>\".")
        
        self._add_spacer(0.2)
    
    def _build_recitals(self):
        """Build the WHEREAS/Recitals section"""
        self.story.append(Paragraph("<b>WHEREAS:</b>", self.styles['AgrSectionHeading']))
        
        recitals = [
            f"Trade Mark No. 2675785 - \"Purnabramha - The Largest Authentic Maharashtrian Restaurant\" is the trademark registered under Manaswini Foods Pvt Ltd, India.",
            
            "The Franchisor Company has developed and owns the Purnabramha brand concept, proprietary recipes, operational systems, standard operating procedures, and all related intellectual property.",
            
            f"Purnabramha operates under the FOCO (Franchise Owned - Company Operated) model, wherein the Franchisee invests capital and owns the franchise unit while the Franchisor manages all operations. The franchise model includes {self.franchise_type} format restaurants.",
            
            "The Franchisor has established a reputation for quality, authenticity, and operational excellence in the restaurant industry, particularly in authentic Maharashtrian cuisine.",
            
            f"The Franchisee through its authorized officer has approached the Franchisor and has requested for a Franchise of the 'Purnabramha' brand at the location: {self.address}, {self.city}.",
            
            f"The Franchisor, after due diligence and assessment, is permitting the Franchisee to invest in and own a franchise unit while the Franchisor operates and manages the business in accordance with the terms set forth herein.",
            
            "Both Parties acknowledge that this Agreement constitutes a legally binding document that governs their relationship for the duration of the franchise term and sets out the rights, obligations, and responsibilities of each Party."
        ]
        
        for i, recital in enumerate(recitals, 1):
            alpha = chr(64 + i)  # A, B, C...
            self._add_body(f"<b>{alpha}.</b> {recital}")
        
        self._add_spacer(0.2)
        self._add_body("<b>NOW THEREFORE,</b> in consideration of the mutual covenants, promises, and agreements contained herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:")
        
        self._add_page_break()
    
    def _build_definitions(self):
        """Build the Definitions section"""
        self._add_section_heading("DEFINITIONS", "1")
        
        self._add_body("In this Agreement, unless the context otherwise requires, the following terms shall have the meanings assigned to them below:")
        self._add_spacer(0.1)
        
        definitions = [
            ("1.1", "\"Agreement\"", "means this Franchise Agreement, including all Schedules, Annexures, and any amendment/addendum as the same may be supplemented, amended, restated, or replaced from time to time with the written consent of both Parties."),
            
            ("1.2", "\"Effective Date\"", f"shall mean the date of execution of this Agreement, deemed to be {self.agreement_start or self.agreement_date}, or the date on which all conditions precedent have been satisfied, whichever is later."),
            
            ("1.3", "\"Franchisor\"", f"means {self.franchisor_name}, its successors, and assigns, being the owner of the Purnabramha brand and intellectual property."),
            
            ("1.4", "\"Franchisee\"", f"means {self.legal_entity_name or '[FRANCHISEE ENTITY NAME]'}, its successors, and permitted assigns, being the investor and owner of the franchise unit."),
            
            ("1.5", "\"Brand\" or \"Purnabramha Brand\"", "means the trade name, trademark, service mark, logo, trade dress, and all associated branding elements owned by or licensed to the Franchisor."),
            
            ("1.6", "\"Intellectual Property\" or \"IP\"", "means all patents, trademarks, service marks, trade names, copyrights, trade secrets, recipes, processes, methods, systems, software, documentation, and all other proprietary rights owned by or licensed to the Franchisor."),
            
            ("1.7", "\"Franchise Premises\"", f"means the only authorized location for operating the Franchise business: {self.address}, {self.city}, {self.state} - {self.pincode}, {self.country}."),
            
            ("1.8", "\"Franchise Fee\"", f"means the non-refundable fee of {format_currency(self.franchise_fee, self.country)} ({format_currency_words(self.franchise_fee, self.country)}) payable by the Franchisee to the Franchisor for the grant of the franchise rights."),
            
            ("1.9", "\"FOCO Model\"", "means Franchise Owned - Company Operated, the business model wherein the Franchisee invests capital and owns the franchise unit while the Franchisor manages and operates all aspects of the business."),
            
            ("1.10", "\"Working Capital\"", f"means the operational fund of {format_currency(self.working_capital, self.country)} ({format_currency_words(self.working_capital, self.country)}) to be maintained by the Franchisee for operational efficiency during franchise operations."),
            
            ("1.11", "\"Gross Revenue\"", "means all revenue generated from the operation of the Franchise Premises from whatever source, including but not limited to sales of food, beverages, merchandise, and services, without any deductions."),
            
            ("1.12", "\"Net Revenue\"", "means Gross Revenue less all operational expenses including rent, staff salaries, raw materials, utilities, marketing expenses, taxes, and other approved operational costs."),
        ]
        
        if self.is_australia:
            definitions.extend([
                ("1.13", "\"Royalty\"", f"means the fee payable to Manaswini Foods Pvt Ltd (India) calculated as a percentage of Gross Revenue as specified in Schedule C."),
                
                ("1.14", "\"Profit Share\"", f"means the distribution of Net Profit between the Parties, with {100 - self.revenue_share}% allocated to the Franchisor and {self.revenue_share}% allocated to the Franchisee."),
                
                ("1.15", "\"Director Operational Honorarium\"", "means the monthly payment to directors of Purnabramha LLC Pty Ltd who are actively involved in on-ground operations at the Franchise Premises."),
                
                ("1.16", "\"Loss Exit Condition\"", "means the condition under which the Franchisee may request termination due to continuous operational losses as specified in Clause 4.4."),
                
                ("1.17", "\"Operational Takeover\"", "means the right of the Franchisor to assume complete operational control of the Franchise Premises under specified circumstances."),
            ])
        else:
            definitions.extend([
                ("1.13", "\"Revenue Share\"", f"means {self.revenue_share}% of Net Revenue payable to the Franchisee after deduction of all operational expenses."),
                
                ("1.14", "\"Service Contract Fee\"", f"means the monthly fee of {format_currency(self.service_fee, self.country)} payable for central management services provided by the Franchisor."),
                
                ("1.15", "\"Minimum Guarantee\"", "means the minimum return on investment guaranteed to the Franchisee, subject to conditions specified in the financial framework."),
            ])
        
        # Common definitions
        definitions.extend([
            ("1.16" if self.is_india else "1.18", "\"Term\"", f"means a period of {FRANCHISE_TENURE_YEARS} ({get_ordinal(FRANCHISE_TENURE_YEARS).replace(str(FRANCHISE_TENURE_YEARS), '')}Seven) years from the Effective Date."),
            
            ("1.17" if self.is_india else "1.19", "\"Confidential Information\"", "means all proprietary information, trade secrets, business information, recipes, processes, customer data, financial information, and any other information that is not publicly available and is disclosed by one Party to the other."),
            
            ("1.18" if self.is_india else "1.20", "\"Standard Operating Procedures\" or \"SOPs\"", "means the detailed operational guidelines, procedures, and standards established by the Franchisor for the operation of all Purnabramha restaurants."),
        ])
        
        for num, term, definition in definitions:
            self._add_clause(f"{num} {term}")
            self._add_body(definition, indent=True)
        
        self._add_spacer(0.15)
        self._add_subsection_heading("INTERPRETATION RULES", "1.19" if self.is_india else "1.21")
        
        interpretation_rules = [
            ("Gender & Number:", "Words importing one gender shall include all genders, and words importing the singular shall include the plural and vice versa."),
            ("Headings:", "Clause headings are for convenience only and shall not affect interpretation."),
            ("References:", "References to clauses, schedules, and annexures are to those in this Agreement unless otherwise stated."),
            (f"{self.governing_law} Law:", f"This Agreement shall be interpreted in accordance with the laws of {self.governing_law}."),
        ]
        
        for title, text in interpretation_rules:
            self._add_bullet(f"<b>{title}</b> {text}")
        
        self._add_page_break()
    
    def _build_agreement_structure(self):
        """Build Section 2 - Agreement Structure & Business Transfer"""
        self._add_section_heading("AGREEMENT STRUCTURE & BUSINESS TRANSFER", "2")
        
        # 2.1 Nature of Agreement
        self._add_subsection_heading("NATURE OF THIS AGREEMENT", "2.1")
        
        self._add_clause("2.1.1 Dual Framework")
        self._add_body("This Agreement establishes a dual framework consisting of:")
        
        self._add_bullet("<b>(a) Franchise Grant:</b> The licensing of the Purnabramha brand, intellectual property, operational systems, and the right to operate a restaurant under the Purnabramha name at the designated Franchise Premises.")
        
        if self.is_australia:
            self._add_bullet("<b>(b) Business Purchase:</b> The acquisition by the Franchisee of business assets, goodwill, and operational continuity of an existing or new Purnabramha restaurant, with the Franchisor retaining complete operational control.")
        else:
            self._add_bullet("<b>(b) FOCO Investment:</b> The investment by the Franchisee in the franchise unit, with the Franchisor retaining complete operational control and management of the restaurant.")
        
        self._add_clause("2.1.2 Binding Nature")
        self._add_body("This Agreement constitutes a legally binding contract between the Parties. Both Parties acknowledge that they have read, understood, and agreed to all terms and conditions contained herein. The Agreement shall be binding upon the Parties, their successors, heirs, legal representatives, and permitted assigns.")
        
        # 2.2 Total Business Acquisition Value
        self._add_subsection_heading("TOTAL BUSINESS ACQUISITION VALUE", "2.2")
        
        self._add_clause("2.2.1 Franchise Fee (Non-Refundable)")
        self._add_body(f"""
        The Franchisee shall pay to the Franchisor a non-refundable Franchise Fee of <b>{format_currency(self.franchise_fee, self.country)}</b> 
        ({format_currency_words(self.franchise_fee, self.country)}). This Franchise Fee grants the Franchisee the following rights and benefits:
        """)
        
        fee_benefits = [
            "Brand usage rights for the agreed territory and Franchise Premises",
            "Access to proprietary recipes, ingredients specifications, and cooking methods",
            "Comprehensive training programs for launch and ongoing operations",
            "Standard Operating Procedures (SOPs) and operations manual",
            "Vendor network access and approved supplier lists",
            "Marketing materials, brand guidelines, and promotional support",
            "Technology systems including POS, inventory management, and reporting tools",
            "Pre-launch support and grand opening assistance"
        ]
        
        for benefit in fee_benefits:
            self._add_bullet(benefit)
        
        self._add_clause("2.2.2 Exclusions from Franchise Fee")
        self._add_body("The Franchise Fee does NOT include the following, which shall be the separate responsibility of the Franchisee:")
        
        exclusions = [
            "Interior design, fit-out, and furniture",
            "Kitchen equipment and appliances",
            "Licenses, permits, and regulatory approvals",
            "Rent deposits and advance rent payments",
            "Staff salary reserves and working capital",
            "Initial inventory and raw materials",
            "Legal and professional fees"
        ]
        
        for excl in exclusions:
            self._add_bullet(excl)
        
        if self.is_australia:
            self._add_clause("2.2.3 Business Assets & Goodwill (Schedule-Based Valuation)")
            self._add_body("The detailed breakdown of business assets and goodwill valuation is provided in <b>Schedule A</b> of this Agreement. The Franchisee acknowledges reviewing and accepting the valuation methodology and amounts specified therein.")
        
        # 2.3 Working Capital
        self._add_subsection_heading("WORKING CAPITAL REQUIREMENT", "2.3")
        
        self._add_clause("2.3.1 Minimum Working Capital")
        self._add_body(f"""
        The Franchisee shall maintain a minimum Working Capital of <b>{format_currency(self.working_capital, self.country)}</b> 
        ({format_currency_words(self.working_capital, self.country)}) throughout the Term of this Agreement. This Working Capital 
        is essential for ensuring smooth operational efficiency and meeting day-to-day business requirements.
        """)
        
        self._add_clause("2.3.2 Purpose of Working Capital")
        self._add_body("The Working Capital shall be utilized for:")
        
        wc_purposes = [
            "Day-to-day operational expenses",
            "Inventory procurement and restocking",
            "Staff salary disbursements",
            "Utility payments and rent",
            "Marketing and promotional activities",
            "Emergency repairs and maintenance",
            "Seasonal variations and business fluctuations"
        ]
        
        for purpose in wc_purposes:
            self._add_bullet(purpose)
        
        # 2.4 Setup Costs
        if self.total_setup > 0:
            self._add_subsection_heading("SETUP COSTS", "2.4")
            
            self._add_clause("2.4.1 Initial Setup Costs (Franchisee Responsibility)")
            self._add_body("The following setup costs shall be borne by the Franchisee prior to commencement of operations:")
            
            setup_table_data = [
                ["Item", "Amount"],
                ["Shop Security Deposit", format_currency(self.setup_costs.get("shop_security_deposit", 0), self.country)],
                ["First Month Rent", format_currency(self.setup_costs.get("first_month_rent", 0), self.country)],
                ["Initial Salary Fund", format_currency(self.setup_costs.get("initial_salary_fund", 0), self.country)],
                ["Initial Grocery & Raw Materials", format_currency(self.setup_costs.get("initial_grocery_cost", 0), self.country)],
                ["<b>Total Setup Costs</b>", f"<b>{format_currency(self.total_setup, self.country)}</b>"]
            ]
            
            setup_table = Table(setup_table_data, colWidths=[3.5*inch, 2*inch])
            setup_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
            ]))
            self.story.append(setup_table)
            self._add_spacer(0.15)
        
        # 2.5 Payment Terms
        self._add_subsection_heading("PAYMENT TERMS", "2.5")
        
        self._add_clause("2.5.1 Payment Schedule")
        self._add_body("All fees and payments under this Agreement shall be made according to the following schedule:")
        
        self._add_bullet("<b>Franchise Fee:</b> Payable in full upon execution of this Agreement")
        self._add_bullet("<b>Setup Costs:</b> Payable prior to commencement of operations")
        self._add_bullet("<b>Working Capital:</b> To be deposited before operational handover")
        
        self._add_clause("2.5.2 Non-Refundability of Fees")
        self._add_body("""
        The Franchisee acknowledges and agrees that:
        <br/><br/>
        <b>(a)</b> The Franchise Fee is non-refundable under all circumstances, including but not limited to termination, 
        cancellation, or non-performance of the Agreement.<br/><br/>
        <b>(b)</b> Any deposits paid shall be subject to the refund provisions specified in Annexure A.<br/><br/>
        <b>(c)</b> The Franchisee has conducted independent due diligence and has not relied solely on representations 
        made by the Franchisor in making this investment decision.
        """)
        
        # 2.6 Conditions Precedent
        self._add_subsection_heading("CONDITIONS PRECEDENT", "2.6")
        
        self._add_body("The following conditions must be satisfied before the operational handover of the Franchise Premises:")
        
        conditions = [
            ("2.6.1", "Complete Payment", "All fees, deposits, and setup costs as specified in this Agreement have been paid in full."),
            ("2.6.2", "Execution of Agreement", "This Agreement has been duly executed by authorized representatives of both Parties."),
            ("2.6.3", "KYC & Corporate Documents", "All required KYC documents, corporate registrations, and identity verifications have been provided and verified."),
            ("2.6.4", "Lease Documentation", "Valid lease agreement or sublease documentation for the Franchise Premises has been executed."),
            ("2.6.5", "Licenses & Permits", "All required business licenses, food safety permits, and regulatory approvals have been obtained."),
            ("2.6.6", "Insurance", "All required insurance policies as specified in Clause 6.2 have been obtained and are in effect."),
            ("2.6.7", "Training Completion", "Key personnel have completed the mandatory training programs conducted by the Franchisor."),
        ]
        
        for num, title, text in conditions:
            self._add_clause(f"{num} {title}")
            self._add_body(text, indent=True)
        
        self._add_page_break()
    
    def _build_operational_framework(self):
        """Build Section 3 - Operational Structure & Control Framework"""
        self._add_section_heading("OPERATIONAL STRUCTURE & CONTROL FRAMEWORK", "3")
        
        # 3.1 Operational Authority
        self._add_subsection_heading("OPERATIONAL AUTHORITY GRANTED TO " + self.franchisor_short, "3.1")
        
        self._add_clause("3.1.1 Exclusive Operational Control")
        self._add_body(f"""
        Under the FOCO (Franchise Owned - Company Operated) model, {self.franchisor_name} shall have <b>exclusive and 
        complete operational control</b> over the Franchise Premises. This includes, but is not limited to:
        """)
        
        control_areas = [
            "Menu development, pricing, and food quality standards",
            "Staff recruitment, training, scheduling, and management",
            "Vendor selection, procurement, and supply chain management",
            "Financial management, accounting, and reporting",
            "Marketing, promotions, and brand communications",
            "Technology systems, POS, and digital infrastructure",
            "Quality assurance, audits, and compliance monitoring",
            "Customer service standards and complaint resolution"
        ]
        
        for area in control_areas:
            self._add_bullet(area)
        
        self._add_clause("3.1.2 Rationale for Operational Control")
        self._add_body("""
        The Franchisor retains operational control to ensure:
        <br/><br/>
        <b>(a)</b> Consistent brand standards and customer experience across all Purnabramha locations<br/>
        <b>(b)</b> Quality assurance in food preparation and service delivery<br/>
        <b>(c)</b> Efficient operations and cost management<br/>
        <b>(d)</b> Protection of proprietary recipes and trade secrets<br/>
        <b>(e)</b> Compliance with all applicable laws and regulations
        """)
        
        self._add_clause("3.1.3 No Interference Clause")
        self._add_body("""
        The Franchisee expressly agrees not to interfere with the day-to-day operations of the Franchise Premises. 
        Any concerns or suggestions from the Franchisee shall be communicated through designated channels and 
        shall be considered by the Franchisor at its sole discretion.
        """)
        
        # 3.2 Staffing & HR Management
        self._add_subsection_heading("STAFFING & HUMAN RESOURCE MANAGEMENT", "3.2")
        
        self._add_clause("3.2.1 Hiring Authority")
        self._add_body(f"""
        {self.franchisor_short} shall have sole and exclusive authority over all staffing matters, including:
        """)
        
        hr_matters = [
            "Recruitment, selection, and hiring of all staff",
            "Setting job descriptions, qualifications, and compensation",
            "Training, development, and performance management",
            "Disciplinary actions, terminations, and HR policies",
            "Work schedules, shifts, and leave management"
        ]
        
        for matter in hr_matters:
            self._add_bullet(matter)
        
        if self.is_australia:
            self._add_clause("3.2.2 Visa & Overseas Staff")
            self._add_body("""
            For international staff requiring work visas, the Franchisor shall coordinate with appropriate 
            immigration authorities. The Franchisee may be required to provide sponsorship documentation 
            where legally necessary, subject to separate arrangements.
            """)
        
        self._add_clause("3.2.3 Franchisee Prohibition on Staffing")
        self._add_body("""
        The Franchisee shall NOT:
        <br/><br/>
        <b>(a)</b> Directly hire, fire, or discipline any staff at the Franchise Premises<br/>
        <b>(b)</b> Make any commitments or promises to staff regarding employment terms<br/>
        <b>(c)</b> Interfere with staff duties or give operational instructions to staff<br/>
        <b>(d)</b> Solicit or attempt to recruit Purnabramha staff for other ventures
        """)
        
        # 3.3 Menu Rights & Control
        self._add_subsection_heading("MENU RIGHTS & CONTROL", "3.3")
        
        self._add_clause("3.3.1 Menu Ownership")
        self._add_body("""
        The menu, including all recipes, food preparations, presentation standards, and ingredient specifications, 
        is the exclusive property of the Franchisor. The Franchisee acknowledges that the menu represents 
        significant intellectual property and trade secrets.
        """)
        
        self._add_clause("3.3.2 Menu Changes")
        self._add_body("""
        The Franchisor reserves the right to modify the menu at any time, including:
        <br/><br/>
        <b>(a)</b> Adding new items or removing existing items<br/>
        <b>(b)</b> Modifying recipes, ingredients, or preparation methods<br/>
        <b>(c)</b> Adjusting portion sizes or presentation<br/>
        <b>(d)</b> Introducing seasonal or promotional items<br/>
        <b>(e)</b> Adapting the menu for local preferences or regulations
        """)
        
        self._add_clause("3.3.3 Franchisee Restrictions")
        self._add_body("""
        The Franchisee shall NOT make any modifications to the menu without prior written approval from the 
        Franchisor. This includes adding, removing, or altering any menu items, recipes, or presentations.
        """)
        
        # 3.4 Pricing Control
        self._add_subsection_heading("PRICING CONTROL", "3.4")
        
        self._add_clause("3.4.1 Exclusive Pricing Rights")
        self._add_body("""
        The Franchisor shall have exclusive authority over all pricing decisions, including:
        <br/><br/>
        <b>(a)</b> Menu pricing for all food and beverage items<br/>
        <b>(b)</b> Promotional pricing and discount structures<br/>
        <b>(c)</b> Delivery and takeaway pricing<br/>
        <b>(d)</b> Seasonal pricing adjustments<br/>
        <b>(e)</b> Bundle and combo pricing
        """)
        
        # 3.5 Supply Chain & Vendor Management
        self._add_subsection_heading("SUPPLY CHAIN & VENDOR MANAGEMENT", "3.5")
        
        self._add_clause("3.5.1 Sole Authority")
        self._add_body("""
        The Franchisor shall have sole authority over supply chain management, including vendor selection, 
        contract negotiation, and procurement decisions. The Franchisee shall not engage directly with 
        vendors without prior written approval.
        """)
        
        self._add_clause("3.5.2 Local Vendor Usage")
        self._add_body("""
        While the Franchisor may approve the use of local vendors for certain items, all such arrangements 
        must be pre-approved and meet the quality standards established by the Franchisor.
        """)
        
        # 3.6 Quality Assurance
        self._add_subsection_heading("QUALITY ASSURANCE & AUDITS", "3.6")
        
        self._add_clause("3.6.1 Regular Audits")
        self._add_body("""
        The Franchisor shall conduct regular quality audits of the Franchise Premises to ensure compliance 
        with brand standards. These audits may be announced or unannounced and shall cover:
        """)
        
        audit_areas = [
            "Food quality and safety standards",
            "Hygiene and cleanliness",
            "Customer service standards",
            "Operational efficiency",
            "Brand compliance and presentation",
            "Inventory management"
        ]
        
        for area in audit_areas:
            self._add_bullet(area)
        
        self._add_clause("3.6.2 Immediate Correction Measures")
        self._add_body("""
        Any deficiencies identified during audits shall be corrected immediately. Repeated violations may 
        result in penalties, operational takeover, or termination of this Agreement.
        """)
        
        # 3.7 Marketing & Promotions
        self._add_subsection_heading("MARKETING & PROMOTIONS", "3.7")
        
        self._add_clause("3.7.1 Control of Branding")
        self._add_body("""
        All marketing, advertising, and promotional activities shall be controlled by the Franchisor. This includes:
        <br/><br/>
        <b>(a)</b> Brand messaging and communication<br/>
        <b>(b)</b> Social media presence and digital marketing<br/>
        <b>(c)</b> Local advertising and promotions<br/>
        <b>(d)</b> Public relations and media interactions<br/>
        <b>(e)</b> Sponsorships and partnerships
        """)
        
        self._add_clause("3.7.2 Franchisee Restrictions")
        self._add_body("""
        The Franchisee shall not engage in any marketing or promotional activities without prior written 
        approval from the Franchisor. This includes social media posts, local advertisements, and any 
        public communications using the Purnabramha brand.
        """)
        
        # 3.8 Bank Account & Financial Control
        self._add_subsection_heading("BANK ACCOUNT & FINANCIAL CONTROL", "3.8")
        
        self._add_clause("3.8.1 Sole Signatory Rights")
        self._add_body(f"""
        {self.franchisor_short} shall be the sole signatory and operator of the business bank account associated 
        with the Franchise Premises. All revenue shall be collected in this account, and all operational 
        expenses shall be paid from this account.
        """)
        
        self._add_clause("3.8.2 Franchisee Rights (View Access Only)")
        self._add_body("""
        The Franchisee shall have read-only access to bank statements and financial reports. The Franchisee 
        shall NOT have transaction or withdrawal rights on the business bank account.
        """)
        
        # 3.9 Monthly Reporting
        self._add_subsection_heading("MONTHLY REPORTING & P&L FRAMEWORK", "3.9")
        
        self._add_clause("3.9.1 Reports to be Generated")
        self._add_body(f"""
        {self.franchisor_short} shall generate and provide the following reports to the Franchisee on a monthly basis:
        """)
        
        reports = [
            "Profit & Loss Statement",
            "Revenue breakdown by category",
            "Expense breakdown by category",
            "Inventory report",
            "Staff cost analysis",
            "Customer feedback summary"
        ]
        
        for report in reports:
            self._add_bullet(report)
        
        self._add_clause("3.9.2 Franchisee Access")
        self._add_body("""
        The Franchisee shall have access to the reporting dashboard and shall receive monthly reports within 
        15 days of the end of each calendar month.
        """)
        
        # 3.10 SOP Compliance
        self._add_subsection_heading("SOP COMPLIANCE", "3.10")
        
        self._add_clause("3.10.1 Mandatory SOP Adherence")
        self._add_body("""
        The Franchise Premises shall operate in strict adherence to the Standard Operating Procedures (SOPs) 
        established by the Franchisor. These SOPs cover all aspects of operations including food preparation, 
        customer service, hygiene, safety, and administrative procedures.
        """)
        
        self._add_clause("3.10.2 SOP Breach Consequences")
        self._add_body("""
        Breaches of SOPs may result in:
        <br/><br/>
        <b>(a)</b> Formal warning and mandatory corrective action<br/>
        <b>(b)</b> Financial penalties as specified in the SOP manual<br/>
        <b>(c)</b> Operational takeover by the Franchisor<br/>
        <b>(d)</b> Termination of this Agreement for repeated or severe breaches
        """)
        
        # 3.11 Franchisee Obligations
        self._add_subsection_heading("FRANCHISEE OBLIGATIONS", "3.11")
        
        self._add_body("The Franchisee shall:")
        
        obligations = [
            ("Ensure Availability of Capital", "Maintain adequate Working Capital and meet all financial commitments as per this Agreement."),
            ("Cooperate Fully", f"Cooperate fully with all instructions and directives from {self.franchisor_short}."),
            ("Avoid Interference", "Not interfere with staff or daily operations at the Franchise Premises."),
            ("Pay Fees on Time", "Pay all royalties, fees, and other amounts due under this Agreement on time."),
            ("Allow Audit Access", "Provide full access for audits and participate in audit reviews as required."),
            ("Maintain Brand Confidentiality", "Protect all confidential information and trade secrets of the Franchisor."),
            ("Avoid Competing Businesses", "Not engage in any competing business during the Term and for a period thereafter."),
            ("Attend Review Meetings", "Attend major review meetings and strategy sessions as required by the Franchisor."),
            ("Support Marketing", "Support marketing initiatives and brand promotion activities as directed."),
        ]
        
        for i, (title, text) in enumerate(obligations, 1):
            self._add_clause(f"3.11.{i} {title}")
            self._add_body(text, indent=True)
        
        self._add_page_break()
    
    def _build_financial_framework(self):
        """Build Section 4 - Financial Framework"""
        self._add_section_heading("FINANCIAL FRAMEWORK, PROFIT SHARE, LOSS EXIT & BUSINESS SALE MECHANISM", "4")
        
        if self.is_australia:
            # Australian Model - 80/20 Profit Share
            self._add_subsection_heading("PROFIT SHARE STRUCTURE (80% – 20%)", "4.1")
            
            self._add_clause("4.1.1 Profit Definition")
            self._add_body("""
            "Net Profit" for the purpose of profit sharing shall mean Gross Revenue less all operational expenses 
            including but not limited to rent, staff salaries, raw materials, utilities, marketing, royalties to MFPL, 
            taxes, and all other approved operating costs.
            """)
            
            self._add_clause("4.1.2 Profit Share Ratio")
            self._add_body(f"""
            The Net Profit of the Franchise Premises shall be distributed as follows:
            <br/><br/>
            <b>Franchisor (Purnabramha LLC Pty Ltd):</b> {100 - self.revenue_share}%<br/>
            <b>Franchisee:</b> {self.revenue_share}%
            """)
            
            self._add_clause("4.1.3 Timing of Distribution")
            self._add_body("""
            Profit distribution shall be calculated and paid on a monthly basis, within 20 days of the end of 
            each calendar month, subject to the availability of audited financial statements.
            """)
            
            self._add_clause("4.1.4 No Profit Distribution During Loss")
            self._add_body("""
            During months where the Franchise Premises operates at a loss, no profit distribution shall be made. 
            Losses shall be carried forward and offset against future profits before any distribution is made.
            """)
            
            # 4.2 Director Operational Honorarium
            self._add_subsection_heading("DIRECTOR OPERATIONAL HONORARIUM", "4.2")
            
            self._add_clause("4.2.1 Amount")
            self._add_body("""
            Directors of Purnabramha LLC Pty Ltd who are actively involved in on-ground operations at the Franchise 
            Premises shall be entitled to a monthly Director Operational Honorarium as specified in Schedule C.
            """)
            
            self._add_clause("4.2.2 Requirements")
            self._add_body("""
            The Honorarium is payable only when the director is physically present and actively engaged in 
            operations for a minimum number of days per month as specified in the operational guidelines.
            """)
            
            self._add_clause("4.2.3 Suspension of Honorarium")
            self._add_body("""
            The Honorarium may be suspended during:
            <br/><br/>
            <b>(a)</b> Periods of operational loss<br/>
            <b>(b)</b> Non-compliance with operational requirements<br/>
            <b>(c)</b> As otherwise determined by mutual agreement
            """)
            
            # 4.3 Royalty Payment
            self._add_subsection_heading("ROYALTY PAYMENT TO MFPL (INDIA)", "4.3")
            
            self._add_clause("4.3.1 Royalty Rate")
            self._add_body("""
            A royalty shall be payable to Manaswini Foods Pvt Ltd (MFPL), India, calculated as a percentage 
            of Gross Revenue as specified in Schedule C. This royalty is in consideration for the use of 
            intellectual property, brand, recipes, and ongoing support from the parent company.
            """)
            
            self._add_clause("4.3.2 Payment Due Date")
            self._add_body("""
            Royalty payments shall be due on the 15th of each month for the preceding month's revenue.
            """)
            
            self._add_clause("4.3.3 Currency Conversion")
            self._add_body("""
            Royalty payments to MFPL shall be made in Indian Rupees (INR), converted at the prevailing 
            exchange rate on the date of payment.
            """)
            
        else:
            # Indian Model - Revenue Share
            self._add_subsection_heading("REVENUE MODEL AND FINANCIAL STRUCTURE", "4.1")
            
            self._add_clause("4.1.1 Revenue Collection")
            self._add_body(f"""
            All revenue from the Franchise Premises shall be collected in official company accounts operated 
            by {self.franchisor_name}. The Franchisor shall maintain detailed records of all revenue and 
            transactions.
            """)
            
            self._add_clause("4.1.2 Revenue Share")
            self._add_body(f"""
            After deduction of all operational expenses, the Franchisee shall receive a Revenue Share of 
            <b>{self.revenue_share}% of Net Revenue</b>. This Revenue Share shall be calculated and paid 
            on a monthly basis.
            """)
            
            self._add_clause("4.1.3 Operational Expenses")
            self._add_body("""
            Operational expenses that shall be deducted before calculating Revenue Share include:
            """)
            
            expenses = ["Rent", "Staff Salaries", "Grocery & Supplies", "Utilities", "Maintenance", 
                       "Marketing", "Taxes & GST", "Operations Cost", "Service Contract Fee"]
            
            for expense in expenses:
                self._add_bullet(expense)
            
            # 4.2 Service Contract Fee - COMPREHENSIVE JUSTIFICATION
            self._add_subsection_heading("SERVICE CONTRACT FEE", "4.2")
            
            self._add_clause("4.2.1 Monthly Fee")
            self._add_body(f"""
            Every franchise center shall pay a monthly Service Contract Fee of <b>{format_currency(self.service_fee, self.country)}</b> 
            ({format_currency_words(self.service_fee, self.country)}) per month. This fee is <b>mandatory, 
            non-negotiable</b>, and essential for maintaining chain-level standards and facilitating overall growth.
            """)
            
            self._add_clause("4.2.2 WHY SERVICE CONTRACT - Detailed Justification")
            self._add_body("""
            The Monthly Service Contract Fee covers all brand-level systems, compliance, technology, auditing, 
            operations, digital infrastructure, creative support, and conflict management that every centre 
            benefits from on a daily basis. The Franchisee acknowledges understanding and consenting to 
            this fee for the following comprehensive reasons:
            """)
            
            self._add_clause("4.2.3 Digital Platforms, Systems & Yearly Subscriptions")
            self._add_body("""
            The fee supports essential digital infrastructure provided to every centre, including:
            """)
            digital_services = [
                "Website hosting & maintenance",
                "Ordering platforms",
                "CRM tools",
                "Digital menu updates",
                "Software subscriptions",
                "Automation & backend management"
            ]
            for svc in digital_services:
                self._add_bullet(svc)
            self._add_body("""
            These platforms necessitate ongoing yearly and monthly payments, the aggregate costs of which 
            are pooled and managed at the brand level.
            """)
            
            self._add_clause("4.2.4 Brand-Level Issue Handling & Conflict Management")
            self._add_body("""
            The fee covers the brand team's daily management of critical issues, including:
            """)
            conflict_services = [
                "Guest escalations",
                "Vendor conflicts",
                "Staff-related discrepancies",
                "Operational emergencies",
                "Inter-centre coordination",
                "Reputation protection on social media"
            ]
            for svc in conflict_services:
                self._add_bullet(svc)
            
            self._add_clause("4.2.5 Legal Documentation, Compliance & Timely Filings")
            self._add_body("""
            Purnabramha provides essential legal and compliance support through this fee:
            """)
            legal_services = [
                "FSSAI, GST, and labour compliance support",
                "Documentation required for malls, councils, and audits",
                "Responses to legal replies, letters, contracts, and notices",
                "Preparation of any urgent document requested by the franchise"
            ]
            for svc in legal_services:
                self._add_bullet(svc)
            
            self._add_clause("4.2.6 Mandatory Restaurant Testing & Quality Audits")
            self._add_body("""
            To ensure compliance with industry standards and regulatory requirements:
            """)
            audit_services = [
                "Water testing",
                "Location hygiene checks",
                "Food sampling compliance",
                "Safety certifications",
                "Timely reports for authorities, malls, events, or partners"
            ]
            for svc in audit_services:
                self._add_bullet(svc)
            
            self._add_clause("4.2.7 Brand Management & Creative Support")
            self._add_body("""
            Strategic brand development and creative asset generation including:
            """)
            brand_services = [
                "Social media branding",
                "Menu designs",
                "Festival creatives",
                "Digital banners",
                "Centre-wise announcements",
                "Seasonal campaigns"
            ]
            for svc in brand_services:
                self._add_bullet(svc)
            
            self._add_clause("4.2.8 Operational Support: Beyond Accounting")
            self._add_body("""
            The Purnabramha team provides operational support that extends far beyond basic accounting:
            """)
            ops_services = [
                "Galla management guidance",
                "Daily sales reconciliation formats",
                "SOP creation & enforcement",
                "Vendor coordination",
                "Staff audits",
                "Training support",
                "Surprise operational checks"
            ]
            for svc in ops_services:
                self._add_bullet(svc)
            
            self._add_clause("4.2.9 Professional Management of All Verticals")
            self._add_body("""
            Comprehensive support across all operational verticals:
            """)
            verticals = ["Dine-in", "Delivery", "Catering", "Events", "Festival Stalls", "Tiffins"]
            for v in verticals:
                self._add_bullet(v)
            
            self._add_clause("4.2.10 Continuous Availability of the Brand Team")
            self._add_body("""
            The Purnabramha head team is continuously available for:
            """)
            team_support = [
                "Calls & Documentation",
                "Branding & Crisis management",
                "Menu development & Pricing reviews",
                "Operations strategy",
                "On-ground guidance"
            ]
            for svc in team_support:
                self._add_bullet(svc)
            
            self._add_clause("4.2.11 Franchisee Consent & Acknowledgment")
            self._add_body("""
            <b>The Franchisee hereby acknowledges and consents that:</b>
            <br/><br/>
            <b>(a)</b> The Monthly Service Contract Fee has been communicated multiple times during the franchise discussion process.<br/>
            <b>(b)</b> The fee is mandatory, non-negotiable, and essential for the professional operation of the franchise.<br/>
            <b>(c)</b> The Franchisee understands the comprehensive services covered by this fee.<br/>
            <b>(d)</b> The Franchisee agrees to pay this fee punctually every month as per this Agreement.
            """)
            
            # 4.3 ROI Calculation Framework - INDIA SPECIFIC
            self._add_subsection_heading("ROI CALCULATION FRAMEWORK (INDIA)", "4.3")
            
            self._add_clause("4.3.1 Investment Structure")
            self._add_body(f"""
            The total investment for this franchise is structured as follows:
            <br/><br/>
            <b>Franchise Fee:</b> {format_currency(self.franchise_fee, self.country)}<br/>
            <b>Working Capital:</b> {format_currency(self.working_capital, self.country)}<br/>
            <b>Setup Costs:</b> {format_currency(self.total_setup, self.country)}<br/>
            <b>Total Investment:</b> {format_currency(self.franchise_fee + self.working_capital + self.total_setup, self.country)}
            """)
            
            self._add_clause("4.3.2 Operational Cost Breakdown (% of Gross Revenue)")
            self._add_body("""
            The typical operational cost structure as a percentage of Gross Revenue is as follows:
            """)
            
            cost_breakdown = [
                ("Food Cost", "25%"),
                ("Marketing", "5%"),
                ("Packaging", "2%"),
                ("Payment Gateway", "1%"),
                ("Commission on Channel Partner", "5%"),
                ("Domestic and Other Expenses", "4%"),
                ("Salary", "15%"),
                ("Rent, Electricity, and Business Tax (REBT)", "12%"),
                ("Utility", "1%"),
                ("Other Miscellaneous", "5%"),
                ("Depreciation", "0.03%"),
                ("Tax", "5%"),
                ("<b>Total Operational Expenses</b>", "<b>80%</b>"),
                ("<b>Net Profit Margin</b>", "<b>20%</b>")
            ]
            
            cost_table_data = [["Expense Category", "Percentage"]]
            for item, pct in cost_breakdown:
                cost_table_data.append([item, pct])
            
            cost_table = Table(cost_table_data, colWidths=[4*inch, 1.5*inch])
            cost_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#27ae60")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
                ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor("#ecf0f1")),
            ]))
            self.story.append(cost_table)
            self._add_spacer(0.2)
            
            self._add_clause("4.3.3 ROI Projection")
            self._add_body("""
            Based on the operational cost structure and projected net profit margin of 20%:
            <br/><br/>
            <b>Projected ROI:</b> Up to 15% of invested capital<br/>
            <b>Capital Recovery Period:</b> 5 Years<br/>
            <b>Post-Recovery Yield:</b> 15% over 2 years<br/>
            <b>Total Investment Horizon:</b> 7 Years
            """)
            
            self._add_clause("4.3.4 Monthly Minimum Guarantee (MG) Calculation")
            self._add_body(f"""
            For an investment of approximately {format_currency(self.franchise_fee + self.working_capital, self.country)}, 
            the monthly Minimum Guarantee (MG) is calculated as follows:
            <br/><br/>
            <b>Formula:</b> (Total Investment × 15% Annual Return) ÷ 12 months<br/>
            <b>Monthly MG:</b> Approximately {format_currency((self.franchise_fee + self.working_capital) * 0.15 / 12, self.country)}<br/><br/>
            <b>Alternative Return:</b> 15% on Revenue Generated (excluding GST, commission of delivery partners), 
            whichever is higher.
            """)
            
            self._add_clause("4.3.5 Important Disclaimer")
            self._add_body("""
            <b>IMPORTANT:</b> The ROI projections provided above are illustrative only and do not constitute 
            a guarantee of returns. Actual results will depend on market conditions, location performance, 
            operational efficiency, and various other factors beyond the control of either Party. The Franchisee 
            acknowledges having conducted independent due diligence before making this investment decision.
            """)
        
        # 4.4 Working Capital Protection (Common) - ENHANCED WITH MG CLAUSE
        self._add_subsection_heading("WORKING CAPITAL / MINIMUM GUARANTEE (MG) PROTECTION CLAUSE", "4.4")
        
        self._add_clause("4.4.1 Threshold Condition - MG Falls Below 50%")
        self._add_body(f"""
        <b>CRITICAL CLAUSE:</b> If the Working Capital / Minimum Guarantee (MG) of the Franchise Premises 
        falls below <b>{WORKING_CAPITAL_THRESHOLD}% (Fifty Percent)</b> of the originally committed Working 
        Capital amount of {format_currency(self.working_capital, self.country)}, the following protective 
        measures shall <b>IMMEDIATELY</b> apply:
        """)
        
        self._add_bullet("<b>Franchisee Revenue Share becomes 0% (ZERO Percent)</b>")
        self._add_bullet("<b>Franchisee Profit Share becomes 0% (ZERO Percent)</b>")
        self._add_bullet("No profit distribution of any kind shall be made to the Franchisee")
        self._add_bullet("All available funds shall be directed towards restoring Working Capital")
        
        self._add_clause("4.4.2 NO TENURE EXTENSION")
        self._add_body(f"""
        <b>IMPORTANT:</b> The Franchisee expressly acknowledges and agrees that:
        <br/><br/>
        <b>(a)</b> If the MG falls below 50%, the franchise tenure shall <b>NOT BE EXTENDED</b> under any circumstances.<br/>
        <b>(b)</b> The period during which the MG remains below 50% shall <b>NOT</b> be added to the tenure.<br/>
        <b>(c)</b> The original tenure of {FRANCHISE_TENURE_YEARS} years remains fixed and unchanged.<br/>
        <b>(d)</b> Both revenue share AND profit share remain suspended until MG is fully restored.
        """)
        
        self._add_clause("4.4.3 Restoration")
        self._add_body(f"""
        This condition shall remain active until the Working Capital / MG is restored to its original 
        committed level of {format_currency(self.working_capital, self.country)}. Only after full restoration 
        shall the normal revenue/profit sharing structure resume from the following month.
        """)
        
        self._add_clause("4.4.4 Franchisee Acknowledgment")
        self._add_body("""
        <b>The Franchisee hereby acknowledges and consents that:</b>
        <br/><br/>
        <b>(a)</b> This clause has been explained in detail during the franchise discussion process.<br/>
        <b>(b)</b> The MG below 50% rule applies equally to both revenue share and profit share.<br/>
        <b>(c)</b> No tenure extension will be granted during the MG deficit period.<br/>
        <b>(d)</b> This clause is essential for protecting the operational viability of the franchise.
        """)
        
        # 4.5 Loss Conditions & Exit
        self._add_subsection_heading("LOSS CONDITIONS & EXIT RIGHTS", "4.5")
        
        self._add_clause("4.5.1 Loss Exit Trigger")
        self._add_body("""
        The Franchisee may request termination of this Agreement if the Franchise Premises operates at a 
        continuous loss for a period of <b>twelve (12) consecutive months</b>, subject to verification and 
        approval by the Franchisor.
        """)
        
        self._add_clause("4.5.2 Verification of Loss")
        self._add_body("""
        Loss shall be verified through:
        <br/><br/>
        <b>(a)</b> Audited financial statements prepared by an independent auditor<br/>
        <b>(b)</b> Review of operational factors contributing to the loss<br/>
        <b>(c)</b> Assessment of whether losses are due to factors within or outside the control of the Parties
        """)
        
        self._add_clause("4.5.3 Non-Qualifying Reasons for Exit")
        self._add_body("""
        The Franchisee CANNOT request exit based on:
        <br/><br/>
        <b>(a)</b> Change of mind or personal circumstances<br/>
        <b>(b)</b> External market conditions or competition<br/>
        <b>(c)</b> Operational issues within the first 12 months<br/>
        <b>(d)</b> Failure to achieve expected returns (as opposed to actual operational losses)
        """)
        
        # 4.6 Sale of Business
        self._add_subsection_heading("SALE OF BUSINESS BY FRANCHISEE (EXIT SALE)", "4.6")
        
        self._add_clause("4.6.1 Pre-Sale Deductions")
        self._add_body("""
        Before any sale proceeds are distributed, the following shall be deducted:
        <br/><br/>
        <b>(a)</b> Any outstanding fees, royalties, or amounts due to the Franchisor<br/>
        <b>(b)</b> Costs associated with the sale process<br/>
        <b>(c)</b> Any operational liabilities or pending obligations
        """)
        
        self._add_clause("4.6.2 Goodwill Gain Split")
        self._add_body("""
        If the sale value exceeds the Franchisee's original investment, the goodwill gain shall be split 
        between the Parties as specified in Schedule F.
        """)
        
        self._add_clause("4.6.3 Constraints on Sale")
        self._add_body("""
        Any sale of the franchise by the Franchisee is subject to:
        <br/><br/>
        <b>(a)</b> Prior written approval from the Franchisor<br/>
        <b>(b)</b> The buyer meeting all qualification criteria established by the Franchisor<br/>
        <b>(c)</b> The buyer executing a new franchise agreement with the Franchisor<br/>
        <b>(d)</b> Full settlement of all outstanding obligations
        """)
        
        # 4.7 Financial Audit Rights
        self._add_subsection_heading("FINANCIAL AUDIT RIGHTS", "4.7")
        
        self._add_clause("4.7.1 Audit Authority & Frequency")
        self._add_body("""
        The Franchisor shall have the right to conduct financial audits at any time, with or without notice. 
        Regular audits shall be conducted at least quarterly to ensure accuracy of financial records.
        """)
        
        self._add_clause("4.7.2 Franchisee Participation Rights")
        self._add_body("""
        The Franchisee shall have the following rights during audits:
        <br/><br/>
        <b>(a)</b> Prior notification of scheduled audits (where reasonably possible)<br/>
        <b>(b)</b> Opportunity to provide clarifications before staff interactions<br/>
        <b>(c)</b> Right to be present during audit review meetings<br/>
        <b>(d)</b> Protection of staff from undue pressure during audits
        """)
        
        self._add_clause("4.7.3 Access to Financial Information")
        self._add_body("""
        The Franchisee shall have access to all financial information related to the Franchise Premises, 
        including bank statements, invoices, expense records, and audit reports.
        """)
        
        # 4.8 Taxation
        self._add_subsection_heading("TAXATION", "4.8")
        
        self._add_clause("4.8.1 Operational Tax Responsibilities")
        self._add_body(f"""
        {self.franchisor_short} shall be responsible for all operational tax compliance, including:
        <br/><br/>
        <b>(a)</b> {"GST registration and filing" if self.is_india else "GST/BAS obligations"}<br/>
        <b>(b)</b> {"TDS deductions and payments" if self.is_india else "PAYG withholding"}<br/>
        <b>(c)</b> {"Professional Tax and other statutory deductions" if self.is_india else "Payroll tax and superannuation"}<br/>
        <b>(d)</b> All other taxes arising from business operations
        """)
        
        self._add_clause("4.8.2 Franchisee's Tax Responsibility")
        self._add_body("""
        The Franchisee shall be responsible for taxes on their share of profits/revenue, including income tax 
        on distributions received from the franchise. The Franchisee shall consult their own tax advisors 
        regarding personal tax obligations.
        """)
        
        self._add_page_break()
    
    def _build_ip_section(self):
        """Build Section 5 - Intellectual Property & Confidentiality"""
        self._add_section_heading("INTELLECTUAL PROPERTY, BRAND PROTECTION, CONFIDENTIALITY & NON-COMPETE", "5")
        
        # 5.1 IP Ownership
        self._add_subsection_heading("INTELLECTUAL PROPERTY OWNERSHIP", "5.1")
        
        self._add_clause("5.1.1 Full Ownership by MFPL")
        self._add_body("""
        All Intellectual Property associated with the Purnabramha brand, including but not limited to trademarks, 
        service marks, trade names, logos, trade dress, recipes, processes, systems, and documentation, is and 
        shall remain the exclusive property of Manaswini Foods Private Limited (MFPL), India.
        """)
        
        self._add_clause("5.1.2 No Transfer of Ownership")
        self._add_body("""
        Nothing in this Agreement shall be construed as transferring any ownership rights in the Intellectual 
        Property to the Franchisee. The Franchisee acquires only a limited, non-exclusive license to use the 
        Intellectual Property in accordance with this Agreement.
        """)
        
        # 5.2 License Grant
        self._add_subsection_heading("LICENSE GRANT", "5.2")
        
        self._add_clause("5.2.1 Limited, Revocable License")
        self._add_body("""
        The Franchisor grants to the Franchisee a limited, non-exclusive, non-transferable, revocable license to:
        <br/><br/>
        <b>(a)</b> Use the Purnabramha brand name and trademarks at the Franchise Premises<br/>
        <b>(b)</b> Use the proprietary systems and processes for operating the restaurant<br/>
        <b>(c)</b> Access and use the standard operating procedures and training materials<br/>
        <b>(d)</b> Use approved marketing materials and brand assets
        """)
        
        self._add_clause("5.2.2 Restrictions")
        self._add_body("""
        The license granted herein is subject to the following restrictions:
        <br/><br/>
        <b>(a)</b> Use only at the designated Franchise Premises<br/>
        <b>(b)</b> Use only in accordance with brand guidelines<br/>
        <b>(c)</b> No sublicensing or assignment without prior written consent<br/>
        <b>(d)</b> Immediate cessation upon termination of this Agreement
        """)
        
        # 5.3 Recipe & Trade Secret Protection
        self._add_subsection_heading("RECIPE & CULINARY TRADE SECRET PROTECTION", "5.3")
        
        self._add_clause("5.3.1 Definition of Culinary IP")
        self._add_body("""
        Culinary Intellectual Property includes:
        <br/><br/>
        <b>(a)</b> All recipes, including ingredients, quantities, and preparation methods<br/>
        <b>(b)</b> Proprietary cooking techniques and processes<br/>
        <b>(c)</b> Food presentation standards and plating guidelines<br/>
        <b>(d)</b> Secret ingredients and proprietary spice blends<br/>
        <b>(e)</b> Menu development methodologies
        """)
        
        self._add_clause("5.3.2 Non-Disclosure of Recipes")
        self._add_body("""
        The Franchisee shall NOT disclose, share, copy, or otherwise disseminate any recipes or culinary 
        trade secrets to any third party. This obligation survives the termination of this Agreement.
        """)
        
        self._add_clause("5.3.3 Penalty for Breach")
        self._add_body(f"""
        Any breach of recipe confidentiality shall result in:
        <br/><br/>
        <b>(a)</b> Immediate termination of this Agreement<br/>
        <b>(b)</b> Liquidated damages of {format_currency(5000000 if self.is_india else 500000, self.country)}<br/>
        <b>(c)</b> Injunctive relief and other legal remedies<br/>
        <b>(d)</b> Recovery of all profits derived from the breach
        """)
        
        # 5.4 Branding & Visual Identity
        self._add_subsection_heading("BRANDING & VISUAL IDENTITY PROTECTION", "5.4")
        
        self._add_clause("5.4.1 Use of Brand Assets")
        self._add_body("""
        All use of brand assets, including logos, signage, marketing materials, and visual elements, must 
        comply with the brand guidelines provided by the Franchisor. No modifications to brand assets are 
        permitted without prior written approval.
        """)
        
        self._add_clause("5.4.2 Prohibitions")
        self._add_body("""
        The Franchisee shall NOT:
        <br/><br/>
        <b>(a)</b> Modify, alter, or create derivative works from brand assets<br/>
        <b>(b)</b> Use the brand for any purpose other than the operation of the Franchise Premises<br/>
        <b>(c)</b> Register or attempt to register any trademarks similar to the Purnabramha brand<br/>
        <b>(d)</b> Contest the validity of the Franchisor's intellectual property rights
        """)
        
        # 5.5 Confidentiality
        self._add_subsection_heading("CONFIDENTIALITY", "5.5")
        
        self._add_clause("5.5.1 Confidential Information Includes")
        self._add_body("""
        Confidential Information under this Agreement includes:
        """)
        
        conf_items = [
            "All recipes, ingredients, and cooking methods",
            "Standard Operating Procedures and operations manuals",
            "Business plans, strategies, and financial projections",
            "Customer data and databases",
            "Vendor contracts and pricing information",
            "Employee information and HR records",
            "Technology systems and software",
            "Any information marked as confidential"
        ]
        
        for item in conf_items:
            self._add_bullet(item)
        
        self._add_clause("5.5.2 Confidentiality Obligations")
        self._add_body("""
        The Franchisee agrees to:
        <br/><br/>
        <b>(a)</b> Maintain strict confidentiality of all Confidential Information<br/>
        <b>(b)</b> Use Confidential Information only for the purposes of this Agreement<br/>
        <b>(c)</b> Not disclose Confidential Information to any third party<br/>
        <b>(d)</b> Implement reasonable security measures to protect Confidential Information<br/>
        <b>(e)</b> Immediately notify the Franchisor of any unauthorized disclosure
        """)
        
        self._add_clause("5.5.3 Post-Term Confidentiality")
        self._add_body(f"""
        The confidentiality obligations under this Agreement shall survive for a period of <b>{CONFIDENTIALITY_SURVIVAL_YEARS} 
        ({get_ordinal(CONFIDENTIALITY_SURVIVAL_YEARS).replace(str(CONFIDENTIALITY_SURVIVAL_YEARS), '')}Two) years</b> 
        from the expiry or termination of this Agreement.
        """)
        
        # 5.6 Non-Compete
        self._add_subsection_heading("NON-COMPETE CLAUSE", "5.6")
        
        self._add_clause("5.6.1 Prohibition During Agreement")
        self._add_body("""
        During the Term of this Agreement, the Franchisee shall NOT:
        <br/><br/>
        <b>(a)</b> Own, operate, manage, or have any interest in a competing restaurant business<br/>
        <b>(b)</b> Provide consulting or advisory services to competing businesses<br/>
        <b>(c)</b> Solicit or attempt to recruit employees of Purnabramha restaurants<br/>
        <b>(d)</b> Divert or attempt to divert customers or business opportunities
        """)
        
        self._add_clause("5.6.2 Post-Term Prohibition")
        self._add_body(f"""
        For a period of <b>{NON_COMPETE_POST_TERM_YEARS} ({get_ordinal(NON_COMPETE_POST_TERM_YEARS).replace(str(NON_COMPETE_POST_TERM_YEARS), '')}Two) years</b> 
        after the termination of this Agreement, the Franchisee shall not engage in any competing business 
        within the geographic area specified in Schedule H.
        """)
        
        self._add_clause("5.6.3 Geographic Range")
        self._add_body(f"""
        The non-compete restriction applies within a radius of <b>{NON_COMPETE_RADIUS_KM} kilometers</b> from 
        the Franchise Premises and any other Purnabramha location.
        """)
        
        self._add_page_break()
    
    def _build_legal_liability(self):
        """Build Section 6 - Legal Liability, Insurance & Compliance"""
        self._add_section_heading("LEGAL LIABILITY, INSURANCE, HEALTH & SAFETY COMPLIANCE & RISK MANAGEMENT", "6")
        
        # 6.1 General Liability
        self._add_subsection_heading("GENERAL LEGAL LIABILITY", "6.1")
        
        self._add_clause("6.1.1 Franchisee as Financial Investor Only")
        self._add_body("""
        Under the FOCO model, the Franchisee's role is that of a financial investor. The Franchisee shall NOT 
        be liable for operational matters including but not limited to employee actions, food safety incidents, 
        customer injuries, or other operational liabilities.
        """)
        
        self._add_clause("6.1.2 Franchisor as Operational Manager")
        self._add_body(f"""
        {self.franchisor_short} as the operational manager shall bear full responsibility for:
        <br/><br/>
        <b>(a)</b> All operational decisions and their consequences<br/>
        <b>(b)</b> Employee actions within the scope of their employment<br/>
        <b>(c)</b> Food safety and hygiene compliance<br/>
        <b>(d)</b> Customer safety and service standards<br/>
        <b>(e)</b> Compliance with all applicable laws and regulations
        """)
        
        # 6.2 Insurance
        self._add_subsection_heading("INSURANCE RESPONSIBILITIES", "6.2")
        
        self._add_clause("6.2.1 Mandatory Insurance")
        self._add_body(f"""
        {self.franchisor_short} shall obtain and maintain the following insurance coverage:
        """)
        
        insurance_types = [
            "Public Liability Insurance - minimum coverage as required by law",
            "Product Liability Insurance - covering food-related incidents",
            "Property Insurance - covering fixtures, fittings, and equipment",
            "Workers' Compensation Insurance - as required by law",
            "Business Interruption Insurance - to cover loss of revenue"
        ]
        
        for ins in insurance_types:
            self._add_bullet(ins)
        
        self._add_clause("6.2.2 Payment of Insurance Premiums")
        self._add_body("""
        Insurance premiums shall be treated as an operational expense and paid from the business operating account.
        """)
        
        self._add_clause("6.2.3 Insurance Lapse")
        self._add_body("""
        In the event of any insurance lapse, the Franchisor shall immediately notify the Franchisee and take 
        steps to reinstate coverage. The Franchisor shall indemnify the Franchisee against any loss arising 
        from the insurance lapse period.
        """)
        
        # 6.3 Health & Safety
        self._add_subsection_heading("HEALTH & SAFETY COMPLIANCE", "6.3")
        
        self._add_clause("6.3.1 Full Responsibility")
        self._add_body(f"""
        {self.franchisor_short} shall have full responsibility for compliance with all health and safety 
        regulations, including {"Occupational Health and Safety Act" if self.is_india else "Work Health and Safety Act (WA)"} 
        and related regulations.
        """)
        
        self._add_clause("6.3.2 Franchisee Role")
        self._add_body("""
        The Franchisee's role in health and safety matters is limited to:
        <br/><br/>
        <b>(a)</b> Reporting any concerns to the Franchisor<br/>
        <b>(b)</b> Not interfering with health and safety procedures<br/>
        <b>(c)</b> Ensuring any visitors brought by the Franchisee comply with safety requirements
        """)
        
        # 6.4 Food Safety
        self._add_subsection_heading("FOOD SAFETY & HYGIENE COMPLIANCE", "6.4")
        
        self._add_clause("6.4.1 Full Food Safety Responsibility")
        self._add_body(f"""
        {self.franchisor_short} shall bear full responsibility for food safety compliance, including:
        <br/><br/>
        <b>(a)</b> {"FSSAI registration and compliance" if self.is_india else "Food Safety Standards Australia New Zealand compliance"}<br/>
        <b>(b)</b> Food handling and storage procedures<br/>
        <b>(c)</b> Kitchen hygiene and cleanliness<br/>
        <b>(d)</b> Staff food safety training<br/>
        <b>(e)</b> Regular food safety audits and inspections
        """)
        
        self._add_clause("6.4.2 Food Safety Supervisor")
        self._add_body("""
        The Franchisor shall ensure that a qualified Food Safety Supervisor is designated and present during 
        all operating hours.
        """)
        
        # 6.5 Indemnity
        self._add_subsection_heading("INDEMNITY", "6.5")
        
        self._add_clause("6.5.1 Franchisor Indemnifies Franchisee")
        self._add_body(f"""
        {self.franchisor_short} shall indemnify and hold harmless the Franchisee from and against all claims, 
        damages, losses, and expenses arising from:
        <br/><br/>
        <b>(a)</b> Operational decisions made by the Franchisor<br/>
        <b>(b)</b> Actions or omissions of employees<br/>
        <b>(c)</b> Food safety or hygiene incidents<br/>
        <b>(d)</b> Customer injuries or claims<br/>
        <b>(e)</b> Non-compliance with any laws or regulations
        """)
        
        self._add_clause("6.5.2 Franchisee Indemnity (Limited)")
        self._add_body("""
        The Franchisee shall indemnify the Franchisor only for claims arising from:
        <br/><br/>
        <b>(a)</b> Breach of this Agreement by the Franchisee<br/>
        <b>(b)</b> Interference by the Franchisee with operations<br/>
        <b>(c)</b> Disclosure of Confidential Information by the Franchisee<br/>
        <b>(d)</b> Actions of the Franchisee outside the scope of this Agreement
        """)
        
        self._add_page_break()
    
    def _build_term_termination(self):
        """Build Section 7 - Term, Renewal & Termination"""
        self._add_section_heading("TERM, RENEWAL, TERMINATION & POST-TERMINATION OBLIGATIONS", "7")
        
        # 7.1 Term
        self._add_subsection_heading("TERM OF AGREEMENT", "7.1")
        
        self._add_clause("7.1.1 Duration")
        self._add_body(f"""
        The Term of this Agreement shall be <b>{FRANCHISE_TENURE_YEARS} ({get_ordinal(FRANCHISE_TENURE_YEARS).replace(str(FRANCHISE_TENURE_YEARS), '')}Seven) years</b> 
        from the Effective Date, unless terminated earlier in accordance with the provisions of this Agreement.
        """)
        
        self._add_clause("7.1.2 Commencement of Operations")
        self._add_body(f"""
        Operations shall commence on or before {self.ops_start or '[OPERATIONS START DATE]'}, subject to 
        satisfaction of all Conditions Precedent.
        """)
        
        # 7.2 Renewal
        self._add_subsection_heading("RENEWAL OF TERM", "7.2")
        
        self._add_clause("7.2.1 Renewal Right")
        self._add_body("""
        At the expiry of the initial Term, the Franchisee may request renewal of this Agreement, subject to:
        <br/><br/>
        <b>(a)</b> The Franchisee being in good standing with no material breaches<br/>
        <b>(b)</b> The Franchisee having met all financial obligations<br/>
        <b>(c)</b> The Franchisor's assessment of operational performance<br/>
        <b>(d)</b> Mutual agreement on renewal terms
        """)
        
        self._add_clause("7.2.2 Renewal Documentation")
        self._add_body("""
        Renewal shall require execution of a new franchise agreement, which may include updated terms, 
        conditions, and fees as determined by the Franchisor.
        """)
        
        # 7.3 Termination
        self._add_subsection_heading("TERMINATION OF AGREEMENT", "7.3")
        
        self._add_clause("7.3.1 Termination by Mutual Consent")
        self._add_body("""
        This Agreement may be terminated at any time by mutual written consent of both Parties, subject to 
        settlement of all outstanding obligations.
        """)
        
        self._add_clause("7.3.2 Termination by Franchisee")
        self._add_body("""
        The Franchisee may terminate this Agreement only under the following strict conditions:
        <br/><br/>
        <b>(a) Loss Exit Clause:</b> Continuous operational losses for 12 consecutive months, verified by independent audit<br/><br/>
        <b>(b) Material Breach by Franchisor:</b> A material breach by the Franchisor that remains uncured for 
        60 days after written notice
        """)
        
        self._add_clause("7.3.3 Termination by Franchisor")
        self._add_body("""
        The Franchisor may terminate this Agreement if the Franchisee:
        <br/><br/>
        <b>(a)</b> Fails to pay any amounts due under this Agreement<br/>
        <b>(b)</b> Breaches any material term of this Agreement<br/>
        <b>(c)</b> Interferes with operations despite warnings<br/>
        <b>(d)</b> Discloses Confidential Information<br/>
        <b>(e)</b> Engages in competing business<br/>
        <b>(f)</b> Commits any act that damages the Purnabramha brand
        """)
        
        # 7.4 Immediate Termination
        self._add_subsection_heading("TERMINATION WITHOUT NOTICE (Immediate Termination)", "7.4")
        
        self._add_body("""
        This Agreement may be terminated immediately without notice in the event of:
        """)
        
        immediate_events = [
            ("Brand Damage", "Any act or omission that causes significant damage to the reputation or goodwill of the Purnabramha brand"),
            ("Criminal Activity", "The Franchisee or its directors/partners being convicted of a criminal offense involving fraud, dishonesty, or moral turpitude"),
            ("Serious Interference", "Serious or repeated interference with operations despite prior warnings"),
            ("Non-Payment", "Failure to pay the franchise purchase balance or working capital as required"),
            ("Insolvency", "The Franchisee becoming insolvent, bankrupt, or entering into liquidation")
        ]
        
        for title, desc in immediate_events:
            self._add_bullet(f"<b>{title}:</b> {desc}")
        
        # 7.5 Cure Periods
        self._add_subsection_heading("CURE PERIODS", "7.5")
        
        self._add_clause("7.5.1 Standard Breach Cure Period")
        self._add_body("""
        For most breaches, the breaching Party shall have <b>30 (Thirty) days</b> from receipt of written 
        notice to cure the breach. Failure to cure within this period shall entitle the non-breaching Party 
        to terminate this Agreement.
        """)
        
        self._add_clause("7.5.2 Breaches Without Cure Period")
        self._add_body("""
        No cure period shall apply for breaches involving:
        <br/><br/>
        <b>(a)</b> Disclosure of Confidential Information<br/>
        <b>(b)</b> Criminal activity<br/>
        <b>(c)</b> Brand damage<br/>
        <b>(d)</b> Insolvency or bankruptcy
        """)
        
        # 7.6 Post-Termination Obligations
        self._add_subsection_heading("POST-TERMINATION OBLIGATIONS", "7.6")
        
        self._add_clause("7.6.1 Removal of Brand and IP")
        self._add_body("""
        Upon termination, the Franchisee shall immediately:
        <br/><br/>
        <b>(a)</b> Cease all use of the Purnabramha brand and trademarks<br/>
        <b>(b)</b> Remove all signage, logos, and brand elements from the premises<br/>
        <b>(c)</b> Cease all marketing and advertising using the Purnabramha name<br/>
        <b>(d)</b> Update all business registrations and licenses to remove the Purnabramha name
        """)
        
        self._add_clause("7.6.2 Return of Confidential Materials")
        self._add_body("""
        The Franchisee shall return or destroy (at the Franchisor's direction) all:
        <br/><br/>
        <b>(a)</b> Operations manuals and SOPs<br/>
        <b>(b)</b> Recipe books and culinary documentation<br/>
        <b>(c)</b> Training materials<br/>
        <b>(d)</b> Software and technology systems<br/>
        <b>(e)</b> Customer databases and records<br/>
        <b>(f)</b> Any other Confidential Information
        """)
        
        self._add_clause("7.6.3 Survival Clauses")
        self._add_body("""
        The following provisions shall survive termination of this Agreement:
        <br/><br/>
        <b>(a)</b> Confidentiality obligations (Clause 5.5)<br/>
        <b>(b)</b> Non-compete obligations (Clause 5.6)<br/>
        <b>(c)</b> Indemnification obligations (Clause 6.5)<br/>
        <b>(d)</b> Dispute resolution provisions (Clause 8)<br/>
        <b>(e)</b> Any accrued payment obligations
        """)
        
        if self.is_australia:
            self._add_subsection_heading("SPECIAL TERMINATION CLAUSE (Perth Model)", "7.7")
            
            self._add_clause("7.7.1 Franchisee Cannot Evict LLC")
            self._add_body("""
            In recognition of the FOCO model and the operational investments made by Purnabramha LLC Pty Ltd, the 
            Franchisee acknowledges and agrees that they cannot evict or remove Purnabramha LLC Pty Ltd from the 
            Franchise Premises except through the termination provisions of this Agreement.
            """)
            
            self._add_clause("7.7.2 LLC Can Continue Operations After Termination")
            self._add_body("""
            Upon termination, Purnabramha LLC Pty Ltd may continue operations at the Franchise Premises for a 
            transition period of up to 90 days to ensure operational continuity and protect brand interests.
            """)
        
        self._add_page_break()
    
    def _build_dispute_resolution(self):
        """Build Section 8 - Dispute Resolution & Miscellaneous"""
        self._add_section_heading("DISPUTE RESOLUTION, GOVERNING LAW, FORCE MAJEURE & MISCELLANEOUS LEGAL PROVISIONS", "8")
        
        # 8.1 Dispute Resolution
        self._add_subsection_heading("DISPUTE RESOLUTION MECHANISM", "8.1")
        
        self._add_clause("8.1.1 Stage 1 — Internal Negotiation")
        self._add_body("""
        In the event of any dispute, the Parties shall first attempt to resolve the matter through good faith 
        negotiation. Senior representatives of both Parties shall meet within <b>14 days</b> of the dispute 
        arising to discuss and attempt resolution.
        """)
        
        self._add_clause("8.1.2 Stage 2 — Mediation")
        self._add_body("""
        If the dispute is not resolved through negotiation within 30 days, the Parties shall submit the 
        dispute to mediation before a mutually agreed mediator. The costs of mediation shall be shared 
        equally between the Parties.
        """)
        
        self._add_clause("8.1.3 Stage 3 — Binding Arbitration")
        self._add_body(f"""
        If mediation fails, the dispute shall be referred to binding arbitration under the {self.arbitration_act}. 
        The arbitration shall be conducted as follows:
        <br/><br/>
        <b>(a)</b> Single arbitrator appointed by mutual consent<br/>
        <b>(b)</b> Venue: {self.jurisdiction}<br/>
        <b>(c)</b> Language: English<br/>
        <b>(d)</b> The decision of the arbitrator shall be final and binding
        """)
        
        # 8.2 Governing Law
        self._add_subsection_heading("GOVERNING LAW", "8.2")
        
        self._add_clause("8.2.1 Jurisdiction")
        self._add_body(f"""
        This Agreement shall be governed by and construed in accordance with the laws of <b>{self.governing_law}</b>.
        """)
        
        self._add_clause("8.2.2 Forum for Litigation")
        self._add_body(f"""
        Subject to the arbitration provisions above, any litigation arising under this Agreement shall be 
        subject to the exclusive jurisdiction of the courts of <b>{self.jurisdiction}</b>.
        """)
        
        # 8.3 Force Majeure
        self._add_subsection_heading("FORCE MAJEURE", "8.3")
        
        self._add_clause("8.3.1 Definition")
        self._add_body("""
        "Force Majeure" means any event beyond the reasonable control of a Party, including but not limited to:
        <br/><br/>
        <b>(a)</b> Natural disasters (earthquake, flood, fire, storm)<br/>
        <b>(b)</b> War, terrorism, civil unrest<br/>
        <b>(c)</b> Government actions, lockdowns, or quarantines<br/>
        <b>(d)</b> Pandemic or epidemic<br/>
        <b>(e)</b> Labor strikes or industrial action (not caused by the Party)
        """)
        
        self._add_clause("8.3.2 Effect of Force Majeure")
        self._add_body("""
        Neither Party shall be liable for failure to perform obligations due to Force Majeure, provided that:
        <br/><br/>
        <b>(a)</b> The affected Party gives prompt notice of the Force Majeure event<br/>
        <b>(b)</b> The affected Party uses reasonable efforts to mitigate the effects<br/>
        <b>(c)</b> Performance resumes as soon as reasonably practicable
        """)
        
        # 8.4 Notices
        self._add_subsection_heading("NOTICES", "8.4")
        
        self._add_clause("8.4.1 Valid Notice")
        self._add_body("""
        All notices under this Agreement shall be in writing and delivered by:
        <br/><br/>
        <b>(a)</b> Registered post or courier<br/>
        <b>(b)</b> Email with delivery confirmation<br/>
        <b>(c)</b> Personal delivery
        """)
        
        self._add_clause("8.4.2 Notice Addresses")
        self._add_body(f"""
        <b>Franchisor:</b><br/>
        {self.franchisor_name}<br/>
        {self.franchisor_address}<br/><br/>
        <b>Franchisee:</b><br/>
        {self.legal_entity_name or '[FRANCHISEE NAME]'}<br/>
        {self.address}, {self.city}, {self.state} - {self.pincode}, {self.country}
        """)
        
        # 8.5 Miscellaneous
        self._add_subsection_heading("MISCELLANEOUS PROVISIONS", "8.5")
        
        misc_clauses = [
            ("8.5.1 Entire Agreement", "This Agreement, together with all Schedules and Annexures, constitutes the entire agreement between the Parties and supersedes all prior negotiations, representations, and agreements."),
            ("8.5.2 Amendment", "This Agreement may only be amended by a written instrument signed by authorized representatives of both Parties."),
            ("8.5.3 Waiver", "No waiver of any breach shall constitute a waiver of any other or subsequent breach. Any waiver must be in writing to be effective."),
            ("8.5.4 Severability", "If any provision of this Agreement is held invalid or unenforceable, the remaining provisions shall continue in full force and effect."),
            ("8.5.5 Assignment", "The Franchisee may not assign this Agreement without the prior written consent of the Franchisor. The Franchisor may assign this Agreement to any affiliate or successor."),
            ("8.5.6 Counterparts", "This Agreement may be executed in counterparts, each of which shall be an original, and all of which together shall constitute one agreement."),
            ("8.5.7 Electronic Signatures", "Electronic signatures shall be valid and binding for the purposes of this Agreement."),
        ]
        
        for num, text in misc_clauses:
            self._add_clause(num)
            self._add_body(text, indent=True)
        
        self._add_page_break()
    
    def _build_schedules(self):
        """Build Schedules A through H"""
        self.story.append(Paragraph("SCHEDULES", self.styles['AgrMainTitle']))
        self._add_spacer(0.3)
        
        # Schedule A - Business Asset Valuation
        self.story.append(Paragraph("SCHEDULE A — BUSINESS ASSET & GOODWILL VALUATION BREAKDOWN", self.styles['AgrScheduleTitle']))
        
        asset_data = [
            ["Category", "Description", "Amount"],
            ["Franchise Fee", "Non-refundable brand license fee", format_currency(self.franchise_fee, self.country)],
            ["Shop Security Deposit", "Refundable security deposit for premises", format_currency(self.setup_costs.get("shop_security_deposit", 0), self.country)],
            ["First Month Rent", "Advance rent payment", format_currency(self.setup_costs.get("first_month_rent", 0), self.country)],
            ["Initial Salary Fund", "Reserve for staff salaries", format_currency(self.setup_costs.get("initial_salary_fund", 0), self.country)],
            ["Initial Inventory", "Raw materials and grocery", format_currency(self.setup_costs.get("initial_grocery_cost", 0), self.country)],
            ["Working Capital", "Operational fund requirement", format_currency(self.working_capital, self.country)],
            ["<b>Total Investment</b>", "", f"<b>{format_currency(self.franchise_fee + self.total_setup + self.working_capital, self.country)}</b>"]
        ]
        
        asset_table = Table(asset_data, colWidths=[2*inch, 2.5*inch, 1.5*inch])
        asset_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
        ]))
        self.story.append(asset_table)
        self._add_spacer(0.3)
        
        # Schedule B - Bank Account Structure
        self.story.append(Paragraph("SCHEDULE B — BANK ACCOUNT & FINANCIAL CONTROL STRUCTURE", self.styles['AgrScheduleTitle']))
        
        self._add_body(f"""
        <b>Account Holder:</b> {self.franchisor_name}<br/>
        <b>Account Purpose:</b> Franchise Operations - {self.franchise_code}<br/>
        <b>Signatory Rights:</b> {self.franchisor_short} (Exclusive)<br/>
        <b>Franchisee Access:</b> View-only access to statements and reports<br/>
        <b>Revenue Collection:</b> All revenue deposited into this account<br/>
        <b>Expense Payments:</b> All operational expenses paid from this account
        """)
        self._add_spacer(0.3)
        
        # Schedule C - Royalty & Profit Share Matrix
        self.story.append(Paragraph("SCHEDULE C — ROYALTY, PROFIT SHARE & HONORARIUM MATRIX", self.styles['AgrScheduleTitle']))
        
        if self.is_australia:
            finance_data = [
                ["Item", "Rate/Amount", "Payable To"],
                ["Royalty to MFPL", "5% of Gross Revenue", "MFPL India"],
                ["Franchisor Profit Share", f"{100 - self.revenue_share}% of Net Profit", self.franchisor_short],
                ["Franchisee Profit Share", f"{self.revenue_share}% of Net Profit", "Franchisee"],
                ["Director Honorarium", "As per operational guidelines", f"{self.franchisor_short} Directors"],
            ]
        else:
            finance_data = [
                ["Item", "Rate/Amount", "Payable To"],
                ["Franchisee Revenue Share", f"{self.revenue_share}% of Net Revenue", "Franchisee"],
                ["Service Contract Fee", f"{format_currency(self.service_fee, self.country)}/month", self.franchisor_short],
                ["Franchisor Share", f"{100 - self.revenue_share}% of Net Revenue", self.franchisor_short],
            ]
        
        finance_table = Table(finance_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
        finance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ]))
        self.story.append(finance_table)
        self._add_spacer(0.3)
        
        # Schedule D - Operational Control
        self.story.append(Paragraph("SCHEDULE D — OPERATIONAL CONTROL & SOP FRAMEWORK", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        The following operational areas are under the exclusive control of the Franchisor:
        """)
        
        ops_areas = [
            "Menu Development & Pricing",
            "Food Quality & Preparation Standards",
            "Staff Recruitment, Training & Management",
            "Vendor Selection & Procurement",
            "Financial Management & Reporting",
            "Marketing & Brand Communications",
            "Technology & POS Systems",
            "Quality Audits & Compliance"
        ]
        
        for area in ops_areas:
            self._add_bullet(area)
        
        self._add_spacer(0.2)
        
        # Schedule E - Staff Deployment (for Australia)
        if self.is_australia:
            self.story.append(Paragraph("SCHEDULE E — VISA & STAFF DEPLOYMENT PLAN", self.styles['AgrScheduleTitle']))
            
            self._add_body("""
            Staff deployment for the Franchise Premises shall be as follows:
            <br/><br/>
            <b>Kitchen Staff:</b> As per operational requirements<br/>
            <b>Service Staff:</b> As per operational requirements<br/>
            <b>Management:</b> Restaurant Manager appointed by PB LLC<br/>
            <b>Visa Sponsorship:</b> Subject to separate arrangements where required
            """)
            self._add_spacer(0.2)
        
        # Schedule F - Exit Valuation
        self.story.append(Paragraph("SCHEDULE F — EXIT & SALE VALUATION PROTOCOL", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        In the event of sale or exit by the Franchisee:
        <br/><br/>
        <b>1. Base Valuation:</b> Original investment amount less depreciation<br/>
        <b>2. Goodwill Addition:</b> Calculated based on average monthly profit for the last 12 months<br/>
        <b>3. Goodwill Split:</b> 50% to Franchisor, 50% to Franchisee (for amounts above original investment)<br/>
        <b>4. Deductions:</b> All outstanding amounts, transfer costs, and liabilities<br/>
        <b>5. Approval:</b> All sales subject to Franchisor approval and buyer qualification
        """)
        self._add_spacer(0.2)
        
        # Schedule G - Confidential Information List
        self.story.append(Paragraph("SCHEDULE G — CONFIDENTIAL INFORMATION & IP DOCUMENT LIST", self.styles['AgrScheduleTitle']))
        
        conf_docs = [
            "Complete Recipe Book with 200+ proprietary recipes",
            "Kitchen Standard Operating Procedures Manual",
            "Service Excellence Handbook",
            "Staff Training Modules and Materials",
            "Vendor Database and Pricing Information",
            "Customer Database and Analytics",
            "Financial Models and Projections",
            "Marketing Strategy Documents",
            "Technology System Documentation"
        ]
        
        for doc in conf_docs:
            self._add_bullet(doc)
        
        self._add_spacer(0.2)
        
        # Schedule H - Non-Compete Zones
        self.story.append(Paragraph("SCHEDULE H — NON-COMPETE ZONES", self.styles['AgrScheduleTitle']))
        
        self._add_body(f"""
        The non-compete restriction applies to the following geographic areas:
        <br/><br/>
        <b>Primary Zone:</b> {NON_COMPETE_RADIUS_KM} km radius from the Franchise Premises at {self.address}, {self.city}<br/>
        <b>Secondary Zones:</b> {NON_COMPETE_RADIUS_KM} km radius from any other Purnabramha location<br/>
        <b>Duration:</b> During the Term and for {NON_COMPETE_POST_TERM_YEARS} years post-termination
        """)
        
        self._add_page_break()
    
    def _build_annexures(self):
        """Build Annexure A"""
        self.story.append(Paragraph("ANNEXURE – A", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("SHOP DEPOSIT – REFUND & EXIT UNDERSTANDING", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure sets out the understanding between the Parties regarding the Shop Security Deposit 
        and the conditions for its refund upon exit or termination.
        """)
        
        self._add_subsection_heading("A.1 DEPOSIT AMOUNT AND PURPOSE")
        
        self._add_body(f"""
        <b>Deposit Amount:</b> {format_currency(self.setup_costs.get("shop_security_deposit", 0), self.country)}<br/>
        <b>Purpose:</b> Security for the lease/tenancy of the Franchise Premises<br/>
        <b>Held By:</b> Landlord/Property Owner (as per lease agreement)
        """)
        
        self._add_subsection_heading("A.2 REFUND CONDITIONS")
        
        self._add_body("""
        The Shop Security Deposit shall be refunded to the Franchisee subject to the following conditions:
        """)
        
        refund_conditions = [
            "All outstanding amounts due to the Franchisor have been paid in full",
            "The premises has been vacated and handed over in good condition",
            "No deductions are required for damages or unpaid rent",
            "All lease/tenancy obligations have been fulfilled",
            "The landlord has released the deposit in accordance with the lease agreement"
        ]
        
        for i, cond in enumerate(refund_conditions, 1):
            self._add_bullet(f"{cond}")
        
        self._add_subsection_heading("A.3 DEPOSIT ADJUSTMENT")
        
        self._add_body("""
        The deposit may be adjusted against:
        <br/><br/>
        <b>(a)</b> Outstanding rent or utility payments<br/>
        <b>(b)</b> Damages to the premises beyond normal wear and tear<br/>
        <b>(c)</b> Any amounts due to the Franchisor under this Agreement<br/>
        <b>(d)</b> Costs of restoring the premises to original condition
        """)
        
        self._add_subsection_heading("A.4 TIMELINE FOR REFUND")
        
        self._add_body("""
        Subject to satisfaction of all conditions, the deposit refund shall be processed within <b>90 days</b> 
        of the effective date of termination and vacation of the premises.
        """)
        
        self._add_subsection_heading("A.5 FRANCHISOR'S ROLE")
        
        self._add_body(f"""
        {self.franchisor_short} shall assist the Franchisee in:
        <br/><br/>
        <b>(a)</b> Coordinating with the landlord for deposit return<br/>
        <b>(b)</b> Providing necessary documentation<br/>
        <b>(c)</b> Facilitating inspection and handover
        """)
        
        self._add_subsection_heading("A.6 ACKNOWLEDGMENT")
        
        self._add_body("""
        Both Parties acknowledge that the deposit refund is subject to third-party (landlord) processes 
        and timelines, and the Franchisor shall not be liable for delays caused by the landlord.
        """)
        
        self._add_page_break()
        
        # Annexure B - Service Contract Understanding
        self.story.append(Paragraph("ANNEXURE – B", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("SERVICE CONTRACT UNDERSTANDING", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure sets out the detailed understanding regarding the Service Contract between the Franchisor 
        and Franchisee for the management and operation of the Franchise Premises.
        """)
        
        self._add_subsection_heading("B.1 SERVICES PROVIDED UNDER SERVICE CONTRACT")
        
        self._add_body("""
        The Franchisor shall provide the following services to the Franchisee under this Service Contract:
        """)
        
        services_list = [
            "<b>Brand Management:</b> Continuous management and protection of the Purnabramha brand identity, including trademark monitoring and brand guideline enforcement",
            "<b>Quality Monitoring:</b> Regular quality audits, mystery shopping programs, and compliance checks to ensure consistent brand standards",
            "<b>Menu Updates:</b> Periodic menu updates, new recipe development, and seasonal menu modifications",
            "<b>Kitchen SOP Systems:</b> Standardized cooking procedures, portion control guidelines, and food preparation standards",
            "<b>Vendor Coordination:</b> Central vendor negotiations, supply chain management, and quality control of supplies",
            "<b>Operations Guidance:</b> Day-to-day operational support, troubleshooting, and best practice implementation",
            "<b>Marketing Support:</b> Marketing strategy development, promotional materials, and campaign coordination",
            "<b>Technology Systems:</b> POS system maintenance, reporting tools, and digital infrastructure support",
            "<b>Training Programs:</b> Ongoing staff training, skill development, and certification programs",
            "<b>Financial Reporting:</b> Monthly P&L statements, financial analysis, and business performance reviews"
        ]
        
        for service in services_list:
            self._add_bullet(service)
        
        self._add_subsection_heading("B.2 SERVICE FEE STRUCTURE")
        
        self._add_body(f"""
        <b>Monthly Service Fee:</b> {format_currency(self.service_fee, self.country)} per month<br/>
        <b>Payment Due Date:</b> 10th of each month for the current month<br/>
        <b>Payment Method:</b> Direct debit from operational account or bank transfer<br/>
        <b>Late Payment Penalty:</b> 2% per week of delay
        """)
        
        self._add_subsection_heading("B.3 SERVICE LEVEL COMMITMENTS")
        
        self._add_body("""
        The Franchisor commits to the following service levels:
        <br/><br/>
        <b>(a)</b> Response to operational queries within 24 hours<br/>
        <b>(b)</b> On-site support visits at least once per quarter<br/>
        <b>(c)</b> Monthly performance review meetings<br/>
        <b>(d)</b> Emergency support available 24/7 for critical issues<br/>
        <b>(e)</b> Quarterly training sessions for staff development
        """)
        
        self._add_subsection_heading("B.4 EXCLUSIONS FROM SERVICE CONTRACT")
        
        self._add_body("""
        The following services are NOT covered under the standard Service Contract and may require additional fees:
        """)
        
        exclusions = [
            "Major equipment repairs or replacements",
            "Legal representation in disputes",
            "Custom marketing campaigns beyond standard programs",
            "Additional training beyond scheduled sessions",
            "Third-party integration services",
            "Franchise expansion consulting"
        ]
        
        for excl in exclusions:
            self._add_bullet(excl)
        
        self._add_page_break()
        
        # Annexure C - Operational Guidelines
        self.story.append(Paragraph("ANNEXURE – C", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("DETAILED OPERATIONAL GUIDELINES", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure provides detailed operational guidelines that govern the day-to-day operations of 
        the Franchise Premises. All operations must comply with these guidelines.
        """)
        
        self._add_subsection_heading("C.1 OPERATING HOURS")
        
        self._add_body("""
        <b>Standard Operating Hours:</b>
        <br/><br/>
        <b>Monday - Thursday:</b> 11:00 AM to 10:00 PM<br/>
        <b>Friday - Saturday:</b> 11:00 AM to 11:00 PM<br/>
        <b>Sunday:</b> 10:00 AM to 10:00 PM<br/><br/>
        Operating hours may be modified for special occasions, festivals, or local requirements with 
        prior approval from the Franchisor.
        """)
        
        self._add_subsection_heading("C.2 STAFF REQUIREMENTS")
        
        self._add_body("""
        Minimum staffing levels must be maintained during operating hours:
        """)
        
        staff_table = [
            ["Role", "Minimum Count", "Shift Coverage"],
            ["Restaurant Manager", "1", "Full operating hours"],
            ["Head Chef", "1", "Kitchen hours"],
            ["Line Cooks", "2-4", "Kitchen hours"],
            ["Service Staff", "3-6", "Dining hours"],
            ["Cashier", "1", "Full operating hours"],
            ["Housekeeping", "1", "Full operating hours"],
        ]
        
        staff_tbl = Table(staff_table, colWidths=[2*inch, 1.5*inch, 2*inch])
        staff_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ]))
        self.story.append(staff_tbl)
        self._add_spacer(0.2)
        
        self._add_subsection_heading("C.3 FOOD SAFETY STANDARDS")
        
        self._add_body("""
        The following food safety standards must be strictly adhered to:
        """)
        
        food_safety = [
            "<b>Temperature Control:</b> Cold foods below 5°C, hot foods above 60°C at all times",
            "<b>Cross-Contamination Prevention:</b> Separate cutting boards and utensils for vegetarian and non-vegetarian items",
            "<b>Personal Hygiene:</b> Hand washing every 30 minutes and before handling food",
            "<b>Food Storage:</b> FIFO (First In, First Out) method for all inventory",
            "<b>Pest Control:</b> Monthly professional pest control and daily kitchen inspections",
            "<b>Cleaning Schedule:</b> Hourly surface sanitization, daily deep cleaning, weekly equipment cleaning",
            "<b>Allergen Management:</b> Clear allergen labeling and separate preparation areas"
        ]
        
        for item in food_safety:
            self._add_bullet(item)
        
        self._add_subsection_heading("C.4 CUSTOMER SERVICE STANDARDS")
        
        self._add_body("""
        Customer service excellence is a cornerstone of the Purnabramha brand:
        """)
        
        customer_service = [
            "<b>Greeting:</b> All customers must be greeted within 30 seconds of entry",
            "<b>Seating:</b> Customers should be seated within 2 minutes during non-peak hours",
            "<b>Order Taking:</b> Orders should be taken within 5 minutes of seating",
            "<b>Food Service:</b> Food should be served within 15-20 minutes of ordering",
            "<b>Bill Settlement:</b> Bill should be presented within 2 minutes of request",
            "<b>Complaint Resolution:</b> All complaints must be escalated to the manager immediately",
            "<b>Feedback Collection:</b> Feedback forms should be offered to all dine-in customers"
        ]
        
        for item in customer_service:
            self._add_bullet(item)
        
        self._add_page_break()
        
        # Annexure D - ROI Calculations Framework
        self.story.append(Paragraph("ANNEXURE – D", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("ROI CALCULATIONS & FINANCIAL PROJECTIONS FRAMEWORK", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure provides a framework for understanding the Return on Investment (ROI) calculations 
        and financial projections for the Franchise Premises. These are illustrative projections and 
        actual results may vary based on market conditions and operational performance.
        """)
        
        self._add_subsection_heading("D.1 INVESTMENT SUMMARY")
        
        total_investment = self.franchise_fee + self.total_setup + self.working_capital
        
        investment_data = [
            ["Investment Component", "Amount", "Nature"],
            ["Franchise Fee", format_currency(self.franchise_fee, self.country), "Non-refundable"],
            ["Setup Costs", format_currency(self.total_setup, self.country), "Capital expenditure"],
            ["Working Capital", format_currency(self.working_capital, self.country), "Operational reserve"],
            ["<b>Total Investment</b>", f"<b>{format_currency(total_investment, self.country)}</b>", ""],
        ]
        
        inv_table = Table(investment_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        inv_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
        ]))
        self.story.append(inv_table)
        self._add_spacer(0.2)
        
        self._add_subsection_heading("D.2 REVENUE PROJECTIONS (ILLUSTRATIVE)")
        
        self._add_body("""
        The following revenue projections are based on average performance of existing Purnabramha 
        restaurants and are provided for illustrative purposes only:
        """)
        
        if self.is_australia:
            revenue_data = [
                ["Metric", "Conservative", "Moderate", "Optimistic"],
                ["Average Daily Covers", "80", "120", "150"],
                ["Average Ticket Size", "AUD $35", "AUD $40", "AUD $45"],
                ["Monthly Revenue", "AUD $84,000", "AUD $144,000", "AUD $202,500"],
                ["Annual Revenue", "AUD $1,008,000", "AUD $1,728,000", "AUD $2,430,000"],
            ]
        else:
            revenue_data = [
                ["Metric", "Conservative", "Moderate", "Optimistic"],
                ["Average Daily Covers", "100", "150", "200"],
                ["Average Ticket Size", "₹350", "₹400", "₹450"],
                ["Monthly Revenue", "₹10,50,000", "₹18,00,000", "₹27,00,000"],
                ["Annual Revenue", "₹1.26 Cr", "₹2.16 Cr", "₹3.24 Cr"],
            ]
        
        rev_table = Table(revenue_data, colWidths=[1.8*inch, 1.3*inch, 1.3*inch, 1.3*inch])
        rev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#27ae60")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ]))
        self.story.append(rev_table)
        self._add_spacer(0.2)
        
        self._add_subsection_heading("D.3 EXPENSE BREAKDOWN (% OF REVENUE)")
        
        self._add_body("""
        Typical expense breakdown as a percentage of gross revenue:
        """)
        
        expense_data = [
            ["Expense Category", "Percentage Range"],
            ["Food & Beverage Cost", "28% - 32%"],
            ["Staff Cost", "22% - 26%"],
            ["Rent", "8% - 12%"],
            ["Utilities", "3% - 5%"],
            ["Marketing", "2% - 4%"],
            ["Operations & Maintenance", "3% - 5%"],
            ["Administrative", "2% - 3%"],
            ["<b>Total Operating Expenses</b>", "<b>68% - 87%</b>"],
            ["<b>Net Margin (Before Tax)</b>", "<b>13% - 32%</b>"],
        ]
        
        exp_table = Table(expense_data, colWidths=[3*inch, 2.5*inch])
        exp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e74c3c")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
            ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor("#ecf0f1")),
        ]))
        self.story.append(exp_table)
        self._add_spacer(0.2)
        
        self._add_subsection_heading("D.4 ROI CALCULATION METHODOLOGY")
        
        self._add_body(f"""
        <b>ROI Calculation Formula:</b>
        <br/><br/>
        ROI = (Franchisee's Annual Share - Annual Investment Recovery) / Total Investment × 100
        <br/><br/>
        <b>Franchisee Share:</b> {self.revenue_share}% of Net {'Profit' if self.is_australia else 'Revenue'}
        <br/><br/>
        <b>Break-Even Analysis:</b>
        <br/>
        Under moderate projections, expected break-even period: 24-36 months
        <br/><br/>
        <b>Important Disclaimer:</b>
        <br/>
        These projections are illustrative only and do not constitute a guarantee of returns. Actual 
        results will depend on market conditions, location performance, operational efficiency, and 
        various other factors beyond the control of either Party.
        """)
        
        self._add_page_break()
        
        # Annexure E - Legal Compliance Checklist
        self.story.append(Paragraph("ANNEXURE – E", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("LEGAL & REGULATORY COMPLIANCE CHECKLIST", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure lists all legal and regulatory requirements that must be complied with for the 
        operation of the Franchise Premises.
        """)
        
        self._add_subsection_heading("E.1 MANDATORY LICENSES & PERMITS")
        
        if self.is_india:
            licenses = [
                ("FSSAI License", "Food Safety and Standards Authority of India", "Mandatory before operations"),
                ("GST Registration", "Goods and Services Tax", "Mandatory for tax compliance"),
                ("Trade License", "Local Municipal Corporation", "Required for business operation"),
                ("Shop & Establishment Act", "State Labour Department", "Employment compliance"),
                ("Fire Safety Certificate", "Fire Department", "Safety requirement"),
                ("Health License", "Health Department", "Food establishment requirement"),
                ("Liquor License", "Excise Department", "If serving alcohol"),
                ("Music License", "PPL/IPRS", "If playing music"),
                ("Signage Permission", "Municipal Corporation", "For outdoor signage"),
            ]
        else:
            licenses = [
                ("Food Business License", "Local Health Authority", "Mandatory for food service"),
                ("Business Registration", "ASIC", "Company registration requirement"),
                ("GST Registration", "ATO", "Tax compliance"),
                ("Work Health & Safety", "WorkSafe", "Workplace safety"),
                ("Fire Safety Certificate", "Fire Department", "Safety requirement"),
                ("Liquor License", "Racing, Gaming and Liquor", "If serving alcohol"),
                ("Building Compliance", "Local Council", "Occupancy certificate"),
                ("Food Safety Supervisor", "Health Authority", "Trained supervisor required"),
            ]
        
        license_data = [["License/Permit", "Issuing Authority", "Remarks"]]
        for lic, auth, rem in licenses:
            license_data.append([lic, auth, rem])
        
        lic_table = Table(license_data, colWidths=[2*inch, 2*inch, 2*inch])
        lic_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#bdc3c7")),
        ]))
        self.story.append(lic_table)
        self._add_spacer(0.2)
        
        self._add_subsection_heading("E.2 COMPLIANCE RESPONSIBILITY MATRIX")
        
        self._add_body("""
        Responsibility for obtaining and maintaining licenses:
        <br/><br/>
        <b>Franchisor Responsibility:</b>
        """)
        
        franchisor_resp = [
            "Brand trademark registration and protection",
            "Central food safety certifications",
            "National-level marketing approvals",
            "Technology and software licenses"
        ]
        
        for resp in franchisor_resp:
            self._add_bullet(resp)
        
        self._add_body("""
        <br/><b>Franchisee Responsibility:</b>
        """)
        
        franchisee_resp = [
            "Local business registration",
            "Premises-specific permits",
            "Local health and safety certificates",
            "Property lease documentation"
        ]
        
        for resp in franchisee_resp:
            self._add_bullet(resp)
        
        self._add_body("""
        <br/><b>Joint Responsibility:</b>
        """)
        
        joint_resp = [
            "FSSAI/Food business license applications",
            "Insurance procurement",
            "Environmental compliance",
            "Staff work permits (where applicable)"
        ]
        
        for resp in joint_resp:
            self._add_bullet(resp)
        
        self._add_page_break()
        
        # Annexure F - Training Program Details
        self.story.append(Paragraph("ANNEXURE – F", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("TRAINING PROGRAM DETAILS", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure outlines the comprehensive training programs provided by the Franchisor for the 
        successful operation of the Franchise Premises.
        """)
        
        self._add_subsection_heading("F.1 PRE-LAUNCH TRAINING")
        
        self._add_body("""
        Prior to the opening of the Franchise Premises, the following training will be provided:
        """)
        
        prelaunch_training = [
            "<b>Brand Orientation (2 days):</b> History, values, and culture of Purnabramha brand",
            "<b>Operations Overview (3 days):</b> Complete walkthrough of daily operations and procedures",
            "<b>Kitchen Training (5 days):</b> Food preparation, recipe execution, and quality standards",
            "<b>Service Training (3 days):</b> Customer service protocols and service standards",
            "<b>Technology Training (2 days):</b> POS systems, inventory management, and reporting tools",
            "<b>Health & Safety (1 day):</b> Food safety, hygiene, and workplace safety procedures",
            "<b>Administrative Training (2 days):</b> Accounting, reporting, and compliance procedures"
        ]
        
        for item in prelaunch_training:
            self._add_bullet(item)
        
        self._add_subsection_heading("F.2 ONGOING TRAINING PROGRAMS")
        
        self._add_body("""
        The Franchisor shall provide the following ongoing training programs:
        """)
        
        ongoing_training = [
            "<b>Monthly Refresher Sessions:</b> Updates on menu changes, new procedures, and best practices",
            "<b>Quarterly Skill Development:</b> Advanced cooking techniques, service excellence, and leadership training",
            "<b>Annual Certification:</b> Mandatory recertification for food safety and brand standards",
            "<b>New Staff Onboarding:</b> Training program for all new staff joining the team",
            "<b>Management Development:</b> Leadership and supervisory skills for senior staff"
        ]
        
        for item in ongoing_training:
            self._add_bullet(item)
        
        self._add_subsection_heading("F.3 TRAINING LOCATIONS")
        
        self._add_body("""
        Training will be conducted at:
        <br/><br/>
        <b>(a)</b> Franchisor's designated training center (for initial training)<br/>
        <b>(b)</b> The Franchise Premises (for on-site training)<br/>
        <b>(c)</b> Existing Purnabramha locations (for practical exposure)<br/>
        <b>(d)</b> Online platforms (for theoretical modules and refreshers)
        """)
        
        self._add_subsection_heading("F.4 TRAINING COSTS")
        
        self._add_body("""
        The following training costs shall apply:
        <br/><br/>
        <b>Pre-Launch Training:</b> Included in Franchise Fee<br/>
        <b>Ongoing Training:</b> Included in Service Contract Fee<br/>
        <b>Additional Training Sessions:</b> At actual cost + 10% administration fee<br/>
        <b>Travel & Accommodation:</b> To be borne by the party requiring the training
        """)
        
        self._add_page_break()
        
        # Annexure G - Brand Guidelines Summary
        self.story.append(Paragraph("ANNEXURE – G", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("BRAND GUIDELINES SUMMARY", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure provides a summary of the Purnabramha brand guidelines. The complete Brand Book 
        will be provided separately to the Franchisee upon execution of this Agreement.
        """)
        
        self._add_subsection_heading("G.1 LOGO USAGE")
        
        self._add_body("""
        The Purnabramha logo must be used in accordance with the following guidelines:
        <br/><br/>
        <b>(a)</b> Minimum clear space must be maintained around the logo<br/>
        <b>(b)</b> Logo colors must not be altered<br/>
        <b>(c)</b> Logo must not be stretched, distorted, or modified<br/>
        <b>(d)</b> Logo must not be used on unauthorized merchandise<br/>
        <b>(e)</b> Logo must appear on all official communications and materials
        """)
        
        self._add_subsection_heading("G.2 COLOR PALETTE")
        
        self._add_body("""
        The official Purnabramha color palette consists of:
        <br/><br/>
        <b>Primary Colors:</b><br/>
        • Saffron Orange (#FF6B00) - Brand primary<br/>
        • Deep Maroon (#8B0000) - Accent color<br/>
        • Warm Gold (#FFD700) - Highlight color<br/><br/>
        <b>Secondary Colors:</b><br/>
        • Off-White (#FFF8F0) - Background<br/>
        • Dark Brown (#3E2723) - Text<br/>
        • Cream (#FFFDD0) - Secondary background
        """)
        
        self._add_subsection_heading("G.3 TYPOGRAPHY")
        
        self._add_body("""
        Official fonts for all Purnabramha communications:
        <br/><br/>
        <b>Headings:</b> Playfair Display (Bold)<br/>
        <b>Body Text:</b> Open Sans (Regular, Semi-bold)<br/>
        <b>Signage:</b> Montserrat (Bold)<br/>
        <b>Hindi Text:</b> Noto Sans Devanagari
        """)
        
        self._add_subsection_heading("G.4 SIGNAGE SPECIFICATIONS")
        
        self._add_body("""
        Exterior and interior signage must comply with:
        <br/><br/>
        <b>Exterior Fascia:</b> Backlit signage with Purnabramha logo and tagline<br/>
        <b>Window Graphics:</b> As per approved templates<br/>
        <b>Menu Boards:</b> Standard design with current menu items<br/>
        <b>Directional Signs:</b> Consistent with brand colors and fonts<br/>
        <b>Promotional Materials:</b> Must be approved by Franchisor before display
        """)
        
        self._add_subsection_heading("G.5 SOCIAL MEDIA GUIDELINES")
        
        self._add_body("""
        For any approved social media activities:
        <br/><br/>
        <b>(a)</b> Use only approved hashtags and handles<br/>
        <b>(b)</b> Follow content approval process before posting<br/>
        <b>(c)</b> Maintain consistent brand voice and tone<br/>
        <b>(d)</b> Respond to comments within 24 hours<br/>
        <b>(e)</b> Never engage in controversial topics or discussions
        """)
        
        self._add_page_break()
        
        # Annexure H - Emergency Procedures
        self.story.append(Paragraph("ANNEXURE – H", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("EMERGENCY PROCEDURES & CRISIS MANAGEMENT", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure outlines the emergency procedures and crisis management protocols that must be 
        followed at the Franchise Premises.
        """)
        
        self._add_subsection_heading("H.1 FIRE EMERGENCY")
        
        self._add_body("""
        In case of fire:
        <br/><br/>
        <b>1.</b> Raise the alarm immediately<br/>
        <b>2.</b> Evacuate all customers and staff following marked exit routes<br/>
        <b>3.</b> Call emergency services (000 in Australia / 101 in India)<br/>
        <b>4.</b> Use fire extinguishers only if safe to do so<br/>
        <b>5.</b> Do not re-enter until cleared by fire services<br/>
        <b>6.</b> Report incident to Franchisor within 1 hour
        """)
        
        self._add_subsection_heading("H.2 MEDICAL EMERGENCY")
        
        self._add_body("""
        In case of medical emergency:
        <br/><br/>
        <b>1.</b> Assess the situation and ensure scene safety<br/>
        <b>2.</b> Call emergency services immediately<br/>
        <b>3.</b> Administer first aid if trained to do so<br/>
        <b>4.</b> Do not move injured person unless necessary<br/>
        <b>5.</b> Document the incident thoroughly<br/>
        <b>6.</b> Report to Franchisor within 2 hours
        """)
        
        self._add_subsection_heading("H.3 FOOD SAFETY INCIDENT")
        
        self._add_body("""
        In case of suspected food poisoning or contamination:
        <br/><br/>
        <b>1.</b> Stop serving suspected food items immediately<br/>
        <b>2.</b> Preserve samples for testing<br/>
        <b>3.</b> Document all affected customers<br/>
        <b>4.</b> Report to health authorities if required<br/>
        <b>5.</b> Notify Franchisor immediately<br/>
        <b>6.</b> Follow Franchisor's crisis communication protocol
        """)
        
        self._add_subsection_heading("H.4 SECURITY INCIDENT")
        
        self._add_body("""
        In case of robbery, theft, or violence:
        <br/><br/>
        <b>1.</b> Prioritize safety of staff and customers<br/>
        <b>2.</b> Do not resist or confront perpetrators<br/>
        <b>3.</b> Call police immediately after safe to do so<br/>
        <b>4.</b> Preserve CCTV footage and evidence<br/>
        <b>5.</b> Document incident details while fresh<br/>
        <b>6.</b> Report to Franchisor within 1 hour
        """)
        
        self._add_subsection_heading("H.5 PUBLIC RELATIONS CRISIS")
        
        self._add_body("""
        In case of negative publicity or social media crisis:
        <br/><br/>
        <b>1.</b> Do NOT respond to media or public comments without approval<br/>
        <b>2.</b> Notify Franchisor's PR team immediately<br/>
        <b>3.</b> Document all facts and evidence<br/>
        <b>4.</b> Follow Franchisor's approved communication only<br/>
        <b>5.</b> Cooperate fully with Franchisor's crisis management team
        """)
        
        self._add_subsection_heading("H.6 EMERGENCY CONTACTS")
        
        self._add_body(f"""
        <b>Emergency Services:</b> {'000' if self.is_australia else '100/101/102'}<br/>
        <b>Fire Department:</b> {'000' if self.is_australia else '101'}<br/>
        <b>Ambulance:</b> {'000' if self.is_australia else '102'}<br/>
        <b>Franchisor Emergency Line:</b> Available 24/7 (number to be provided)<br/>
        <b>Regional Operations Manager:</b> (number to be provided)<br/>
        <b>Head Office:</b> (number to be provided)
        """)
        
        self._add_page_break()
        
        # Annexure I - Menu & Recipe Standards
        self.story.append(Paragraph("ANNEXURE – I", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("MENU & RECIPE STANDARDS", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure outlines the menu and recipe standards that must be strictly followed at all 
        Purnabramha franchise locations to ensure consistent quality and authentic taste.
        """)
        
        self._add_subsection_heading("I.1 MENU CATEGORIES")
        
        self._add_body("""
        The standard Purnabramha menu consists of the following categories:
        """)
        
        menu_categories = [
            "<b>Thali (Complete Meals):</b> Traditional Maharashtrian thalis with fixed components",
            "<b>Starters:</b> Authentic appetizers and snacks",
            "<b>Main Course (Vegetarian):</b> Traditional vegetarian curries and preparations",
            "<b>Main Course (Non-Vegetarian):</b> Authentic non-veg specialties",
            "<b>Breads:</b> Variety of Indian breads including regional specialties",
            "<b>Rice & Biryanis:</b> Traditional rice preparations",
            "<b>Desserts:</b> Authentic Maharashtrian sweets and desserts",
            "<b>Beverages:</b> Traditional and modern beverage options"
        ]
        
        for cat in menu_categories:
            self._add_bullet(cat)
        
        self._add_subsection_heading("I.2 RECIPE STANDARDS")
        
        self._add_body("""
        All recipes must adhere to the following standards:
        <br/><br/>
        <b>(a) Authenticity:</b> Recipes must follow traditional Maharashtrian cooking methods<br/>
        <b>(b) Consistency:</b> Taste, presentation, and portion sizes must be consistent<br/>
        <b>(c) Quality:</b> Only approved ingredients and suppliers to be used<br/>
        <b>(d) Documentation:</b> All recipes must be documented in the Recipe Book<br/>
        <b>(e) Modifications:</b> No recipe modifications without written approval from Franchisor
        """)
        
        self._add_subsection_heading("I.3 SIGNATURE DISHES")
        
        self._add_body("""
        The following signature dishes must always be available on the menu:
        """)
        
        signature_dishes = [
            "Puran Poli (Traditional sweet flatbread)",
            "Maharashtrian Thali (Complete meal platter)",
            "Kolhapuri Chicken/Mutton (Spicy regional specialty)",
            "Sabudana Khichdi (Tapioca preparation)",
            "Misal Pav (Spiced curry with bread)",
            "Bharli Vangi (Stuffed eggplant)",
            "Solkadi (Kokum-based digestive drink)",
            "Modak (Sweet dumpling - Lord Ganesha's favorite)"
        ]
        
        for dish in signature_dishes:
            self._add_bullet(dish)
        
        self._add_subsection_heading("I.4 INGREDIENT SOURCING")
        
        self._add_body("""
        Ingredients must be sourced according to the following guidelines:
        <br/><br/>
        <b>Spices & Masalas:</b> From Franchisor-approved suppliers only<br/>
        <b>Fresh Produce:</b> From approved local vendors with quality certifications<br/>
        <b>Dairy Products:</b> From certified suppliers with proper cold chain<br/>
        <b>Meat & Seafood:</b> From approved suppliers with halal/quality certifications<br/>
        <b>Specialty Items:</b> From Franchisor's central procurement where available
        """)
        
        self._add_subsection_heading("I.5 PORTION CONTROL")
        
        self._add_body("""
        Strict portion control must be maintained for:
        <br/><br/>
        <b>(a)</b> Cost management and profitability<br/>
        <b>(b)</b> Consistency across all locations<br/>
        <b>(c)</b> Customer satisfaction and value perception<br/>
        <b>(d)</b> Inventory management and waste reduction
        """)
        
        self._add_page_break()
        
        # Annexure J - Technology Systems
        self.story.append(Paragraph("ANNEXURE – J", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("TECHNOLOGY SYSTEMS & DIGITAL INFRASTRUCTURE", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure describes the technology systems and digital infrastructure required for the 
        operation of the Franchise Premises.
        """)
        
        self._add_subsection_heading("J.1 POINT OF SALE (POS) SYSTEM")
        
        self._add_body("""
        The Franchise Premises must use the Franchisor's approved POS system with the following features:
        """)
        
        pos_features = [
            "Order management and billing",
            "Table management and reservations",
            "Kitchen display integration",
            "Inventory tracking",
            "Sales reporting and analytics",
            "Customer loyalty program integration",
            "Payment processing (cash, card, digital)",
            "GST/Tax compliance"
        ]
        
        for feature in pos_features:
            self._add_bullet(feature)
        
        self._add_subsection_heading("J.2 INVENTORY MANAGEMENT SYSTEM")
        
        self._add_body("""
        The inventory management system shall track:
        <br/><br/>
        <b>(a)</b> Raw material stock levels<br/>
        <b>(b)</b> Reorder points and automatic alerts<br/>
        <b>(c)</b> Wastage and consumption patterns<br/>
        <b>(d)</b> Vendor performance and pricing<br/>
        <b>(e)</b> Batch tracking and expiry management
        """)
        
        self._add_subsection_heading("J.3 REPORTING DASHBOARD")
        
        self._add_body("""
        Both Parties shall have access to the reporting dashboard providing:
        """)
        
        reports = [
            "Daily, weekly, and monthly sales reports",
            "Product-wise sales analysis",
            "Staff productivity metrics",
            "Customer feedback and ratings",
            "Inventory status and variance reports",
            "Financial P&L summaries",
            "Comparative performance across periods"
        ]
        
        for report in reports:
            self._add_bullet(report)
        
        self._add_subsection_heading("J.4 COMMUNICATION SYSTEMS")
        
        self._add_body("""
        The following communication systems shall be implemented:
        <br/><br/>
        <b>Internal Communication:</b> Slack/WhatsApp groups for operational coordination<br/>
        <b>Customer Feedback:</b> Integrated feedback collection system<br/>
        <b>Escalation Channels:</b> Defined escalation matrix for issues<br/>
        <b>Emergency Alerts:</b> SMS/Email alert system for critical issues
        """)
        
        self._add_subsection_heading("J.5 DATA SECURITY")
        
        self._add_body("""
        All technology systems must comply with:
        <br/><br/>
        <b>(a)</b> Data protection regulations (GDPR/Privacy Act as applicable)<br/>
        <b>(b)</b> PCI-DSS compliance for payment processing<br/>
        <b>(c)</b> Regular security audits and updates<br/>
        <b>(d)</b> Access control and user authentication<br/>
        <b>(e)</b> Regular data backups and disaster recovery
        """)
        
        self._add_page_break()
        
        # Annexure K - Quality Assurance Checklist
        self.story.append(Paragraph("ANNEXURE – K", self.styles['AgrMainTitle']))
        self._add_spacer(0.2)
        
        self.story.append(Paragraph("QUALITY ASSURANCE CHECKLIST", self.styles['AgrScheduleTitle']))
        
        self._add_body("""
        This Annexure provides the Quality Assurance Checklist that will be used for regular audits 
        of the Franchise Premises.
        """)
        
        self._add_subsection_heading("K.1 DAILY CHECKLIST")
        
        daily_items = [
            "Kitchen cleanliness and hygiene verified",
            "Staff uniforms and grooming standards met",
            "Food temperature logs recorded",
            "Cash reconciliation completed",
            "Customer feedback reviewed",
            "Inventory levels checked",
            "Equipment functionality verified"
        ]
        
        for i, item in enumerate(daily_items, 1):
            self._add_bullet(f"[  ] {item}")
        
        self._add_subsection_heading("K.2 WEEKLY CHECKLIST")
        
        weekly_items = [
            "Deep cleaning of kitchen equipment",
            "Pest control inspection",
            "Staff training session conducted",
            "Inventory full count",
            "Sales analysis review",
            "Menu item availability check",
            "Marketing materials review"
        ]
        
        for i, item in enumerate(weekly_items, 1):
            self._add_bullet(f"[  ] {item}")
        
        self._add_subsection_heading("K.3 MONTHLY CHECKLIST")
        
        monthly_items = [
            "Full kitchen deep clean",
            "Equipment maintenance check",
            "Fire safety equipment inspection",
            "Staff performance reviews",
            "Financial reconciliation",
            "License/permit validity check",
            "Insurance policy review",
            "Customer satisfaction analysis"
        ]
        
        for i, item in enumerate(monthly_items, 1):
            self._add_bullet(f"[  ] {item}")
        
        self._add_subsection_heading("K.4 AUDIT SCORING")
        
        self._add_body("""
        Quality audits will be scored as follows:
        <br/><br/>
        <b>90-100%:</b> Excellent - No action required<br/>
        <b>80-89%:</b> Good - Minor improvements needed<br/>
        <b>70-79%:</b> Satisfactory - Corrective action required within 7 days<br/>
        <b>60-69%:</b> Poor - Immediate corrective action required<br/>
        <b>Below 60%:</b> Critical - May result in operational review/suspension
        """)
        
        self._add_page_break()
    
    def _build_signature_section(self):
        """Build the signature section"""
        self.story.append(Paragraph("SIGNATURE BLOCKS", self.styles['AgrMainTitle']))
        self._add_spacer(0.3)
        
        self._add_body("""
        <b>IN WITNESS WHEREOF</b>, the Parties hereto have executed this Franchise Agreement as of the date 
        first above written, having read, understood, and agreed to all the terms and conditions contained herein.
        """)
        
        self._add_spacer(0.5)
        
        # Signature table
        directors_names = ", ".join([d.get("name", "") for d in self.directors if d.get("name")])
        first_director = directors_names.split(',')[0].strip() if directors_names else "[DIRECTOR NAME]"
        
        sig_data = [
            [Paragraph("<b>FOR THE FRANCHISOR</b>", self.styles['AgrSignatureText']), 
             Paragraph("<b>FOR THE FRANCHISEE</b>", self.styles['AgrSignatureText'])],
            ["", ""],
            [self.franchisor_name, self.legal_entity_name or "[FRANCHISEE ENTITY NAME]"],
            ["", ""],
            ["", ""],
            ["_________________________________", "_________________________________"],
            ["", ""],
            ["Authorized Signatory", first_director],
            ["Director", "Director/Partner"],
            ["", ""],
            ["", ""],
            ["_________________________________", "_________________________________"],
            ["", ""],
            ["Witness 1", "Witness 1"],
            ["Name:", "Name:"],
            ["Address:", "Address:"],
            ["", ""],
            ["", ""],
            ["_________________________________", "_________________________________"],
            ["", ""],
            ["Witness 2", "Witness 2"],
            ["Name:", "Name:"],
            ["Address:", "Address:"],
            ["", ""],
            ["", ""],
            [f"Date: {self.agreement_date}", f"Date: {self.agreement_date}"],
            [f"Place: {self.jurisdiction}", f"Place: {self.city}"],
        ]
        
        sig_table = Table(sig_data, colWidths=[3*inch, 3*inch])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        self.story.append(sig_table)
        
        self._add_spacer(0.5)
        
        # Final note
        self.story.append(Paragraph(
            "— END OF AGREEMENT —",
            ParagraphStyle('EndNote', parent=self.styles['AgrCenterBold'], 
                          textColor=colors.HexColor("#7f8c8d"), fontSize=10)
        ))

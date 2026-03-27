# =======================================
# HR LETTERS ROUTES (Extracted from server.py)
# =======================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import os
import re
import logging

router = APIRouter(prefix="/api/hr_letter", tags=["hr_letters"])
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent

# Dependency injection placeholders (set by server.py)
db = None
verify_token = None

def set_db(database):
    global db
    db = database

def set_verify_token(vt):
    global verify_token
    verify_token = vt

# ---- Models ----

class HRLetterRequest(BaseModel):
    token: str
    employeeName: str
    letterType: str
    joiningDate: Optional[str] = None
    salary: Optional[str] = None
    lastWorkingDate: Optional[str] = None
    exitReason: Optional[str] = None
    visaSubject: Optional[str] = None
    destinationCountry: Optional[str] = None
    visaNumber: Optional[str] = None
    travelPurpose: Optional[str] = None
    travelDuration: Optional[str] = None
    travelStartDate: Optional[str] = None
    travelEndDate: Optional[str] = None
    invitingCompany: Optional[str] = None
    projectDetails: Optional[str] = None

class HRLetterDownloadRequest(BaseModel):
    token: str
    content: str
    letterType: str
    employeeName: str
    format: str
    signatory: str = "sandeep"

class CustomLetterRequest(BaseModel):
    token: str
    letterDescription: str
    employeeName: Optional[str] = None
    additionalDetails: Optional[str] = None

# ---- System Prompt ----

HR_LETTER_SYSTEM_PROMPT = """You are an expert HR letter writer for Manaswini Foods Pvt. Ltd. (Purnabramha Restaurant Chain).

Company Details:
- Company Name: MANASWINI FOODS PVT. LTD.
- Brand: Purnabramha - The Largest Maharashtrian Restaurant Chain
- Registered Address: 17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102
- Director: Mr. Sandeep Gadhwal
- CIN: (Company Identification Number will be added)

Your task is to generate professional, legally appropriate HR letters. Each letter should:
1. Be formal and professional in tone
2. Include all necessary details provided
3. Follow standard Indian HR letter formats
4. Include appropriate date formatting (DD-MM-YYYY)
5. End with signature block for Mr. Sandeep Gadhwal, Director

Important: Generate ONLY the letter content. Do not include any explanations or notes outside the letter."""

# ---- Endpoints ----

@router.post("/generate")
async def generate_hr_letter(req: HRLetterRequest):
    """Generate HR letters using AI (MGT only)"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can generate HR letters")

    emp = await db.employees.find_one(
        {"name": {"$regex": f"^{req.employeeName}$", "$options": "i"}},
        {"_id": 0}
    )
    if not emp:
        raise HTTPException(404, f"Employee '{req.employeeName}' not found in database")

    today = datetime.now().strftime("%d-%m-%Y")

    if req.letterType == "offer":
        prompt = f"""Generate a professional OFFER LETTER for the following employee:

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {req.joiningDate or emp.get('dateOfJoining', 'N/A')}
Monthly Salary: Rs. {req.salary or emp.get('currentSalary', 'N/A')}
Bank Details: {emp.get('bankName', 'N/A')} - A/C: {emp.get('beneAccNo', 'N/A')}

Today's Date: {today}

The offer letter should include:
1. Welcome and congratulations
2. Position offered and reporting structure
3. Compensation details
4. Terms of employment
5. Joining formalities
6. Company policies overview
7. Acceptance clause"""

    elif req.letterType == "exit":
        prompt = f"""Generate a professional EXIT/RESIGNATION ACCEPTANCE LETTER for the following employee:

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {emp.get('dateOfJoining', 'N/A')}
Last Working Date: {req.lastWorkingDate or 'As per notice period'}
Reason for Exit: {req.exitReason or 'Personal reasons'}

Today's Date: {today}

The exit letter should include:
1. Acknowledgment of resignation
2. Acceptance of last working date
3. Handover responsibilities
4. Settlement of dues
5. Return of company property
6. Wishes for future endeavors"""

    elif req.letterType == "experience":
        prompt = f"""Generate a professional EXPERIENCE/SERVICE CERTIFICATE for the following employee:

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {emp.get('dateOfJoining', 'N/A')}
Last Working Date: {req.lastWorkingDate or today}
Gender: {emp.get('gender', 'N/A')}

Today's Date: {today}

The experience letter should include:
1. Employment confirmation with dates
2. Designation and responsibilities
3. Performance appreciation
4. Character and conduct certification
5. Best wishes for future"""

    elif req.letterType == "visa":
        subject_line = req.visaSubject or f"Employment Verification for {req.destinationCountry or 'Visa'} Application"
        prompt = f"""Generate a professional VISA SUPPORT/INVITATION LETTER for immigration purposes:

Subject/Topic: {subject_line}

Employee Name: {emp.get('name')}
Designation: {emp.get('designation', 'N/A')}
Department: {emp.get('center', 'N/A')}
Date of Joining: {emp.get('dateOfJoining', 'N/A')}
Current Salary: Rs. {emp.get('currentSalary', 'N/A')} per month
Gender: {emp.get('gender', 'N/A')}

Travel Details:
- Destination Country: {req.destinationCountry or 'N/A'}
- Visa Number (if available): {req.visaNumber or 'Applied/Pending'}
- Purpose of Travel: {req.travelPurpose or 'Business Visit'}
- Duration of Stay: {req.travelDuration or 'N/A'}
- Travel Start Date: {req.travelStartDate or 'N/A'}
- Travel End Date: {req.travelEndDate or 'N/A'}
- Inviting Company/Organization: {req.invitingCompany or 'N/A'}
- Project/Business Details: {req.projectDetails or 'Business meetings and coordination'}

Today's Date: {today}

The letter must have a Subject line: "{subject_line}"

The visa support letter should include:
1. Company introduction and legitimacy
2. Employee confirmation and role
3. Purpose of visit clearly stated
4. Travel dates and duration
5. Financial responsibility statement (company will bear expenses OR employee self-funded)
6. Guarantee of return to India after visit
7. Contact details for verification
8. Request for visa approval

This letter is for immigration/visa authorities of {req.destinationCountry or 'the destination country'}."""
    else:
        raise HTTPException(400, f"Invalid letter type: {req.letterType}")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(500, "AI service not configured")

        session_id = f"hr_letter_{req.letterType}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        chat = LlmChat(api_key=api_key, session_id=session_id, system_message=HR_LETTER_SYSTEM_PROMPT).with_model("openai", "gpt-5.2")
        user_message = UserMessage(text=prompt)
        letter_content = await chat.send_message(user_message)

        await db.hr_letters.insert_one({
            "employeeName": emp.get('name'),
            "letterType": req.letterType,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "generatedBy": session.get("managerName", ""),
            "content": letter_content[:500] + "..."
        })

        return {
            "success": True,
            "letterType": req.letterType,
            "employeeName": emp.get('name'),
            "content": letter_content,
            "generatedAt": today
        }
    except ImportError as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(500, "AI library not available")
    except Exception as e:
        logger.error(f"HR Letter generation error: {e}")
        raise HTTPException(500, f"Failed to generate letter: {str(e)}")


@router.get("/employees")
async def get_employees_for_hr(token: str):
    """Get list of employees for HR letter generation (MGT only)"""
    session = verify_token(token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can access HR features")
    employees = await db.employees.find(
        {}, {"_id": 0, "name": 1, "designation": 1, "center": 1, "dateOfJoining": 1, "currentSalary": 1, "gender": 1}
    ).to_list(1000)
    return {"employees": employees}


@router.post("/generate-custom")
async def generate_custom_letter(req: CustomLetterRequest):
    """Generate a custom letter using AI based on user description"""
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can generate HR letters")

    today = datetime.now().strftime("%d %B %Y")
    emp_details = ""
    if req.employeeName:
        emp = await db.employees.find_one({"name": req.employeeName}, {"_id": 0})
        if emp:
            emp_details = f"""
Employee Information:
- Name: {emp.get('name')}
- Designation: {emp.get('designation', 'N/A')}
- Department/Center: {emp.get('center', 'N/A')}
- Date of Joining: {emp.get('dateOfJoining', 'N/A')}
- Current Salary: Rs. {emp.get('currentSalary', 'N/A')} per month
- Gender: {emp.get('gender', 'N/A')}
"""

    prompt = f"""You are the HR manager of MANASWINI FOODS PVT. LTD. (Brand: Purnabramha - Pure Vegetarian South Indian Restaurant Chain).
    
Generate a professional {req.letterDescription}

{emp_details}

Additional Context/Requirements:
{req.additionalDetails or 'None specified'}

Today's Date: {today}

Company Details:
- Company Name: MANASWINI FOODS PVT. LTD.
- Brand: Purnabramha (Pure Vegetarian South Indian Restaurant)
- Registered Address: No. 3, First Floor, Above South Indian Bank, 60 Feet Road, MICO Layout, BTM 2nd Stage, Bangalore - 560076
- CIN: U55101KA2017PTC103726
- GSTIN: 29AAHCM4627M1ZE

Please generate a formal, professional letter that:
1. Has proper letterhead format
2. Includes date and reference number
3. Is addressed appropriately
4. Has clear and professional language
5. Ends with appropriate closing

Do NOT include signature block - that will be added separately."""

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(500, "LLM API key not configured")

        session_id = f"custom_letter_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        chat = LlmChat(api_key=api_key, session_id=session_id, system_message="You are an expert HR manager creating professional business letters.").with_model("openai", "gpt-5.2")
        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        content = str(response)

        await db.hr_letters.insert_one({
            "letter_type": "custom",
            "letter_description": req.letterDescription,
            "employee_name": req.employeeName,
            "content": content,
            "generated_at": datetime.now(timezone.utc),
            "generated_by": session.get("name", "Unknown")
        })

        return {"content": content, "letterType": "custom"}
    except Exception as e:
        logger.error(f"Custom letter generation failed: {e}")
        raise HTTPException(500, f"Letter generation failed: {str(e)}")


@router.post("/download")
async def download_hr_letter(req: HRLetterDownloadRequest):
    """Download HR letter as PDF or Word document"""
    from fastapi.responses import Response
    session = verify_token(req.token)
    if not session:
        raise HTTPException(401, "Invalid or expired token")
    if session.get("center") != "PB-MGT":
        raise HTTPException(403, "Only PB-MGT can download HR letters")

    today = datetime.now().strftime("%d-%m-%Y")
    safe_name = req.employeeName.replace(" ", "_")

    if req.format == "pdf":
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Image
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,
                               leftMargin=0.75*inch, rightMargin=0.75*inch,
                               topMargin=0.5*inch, bottomMargin=0.75*inch)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, spaceAfter=6)
        company_style = ParagraphStyle('Company', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, spaceAfter=3)
        address_style = ParagraphStyle('Address', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, spaceAfter=12)
        body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, alignment=TA_JUSTIFY, leading=14, spaceAfter=8)
        signature_style = ParagraphStyle('Signature', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceBefore=30)

        story = []

        logo_path = ROOT_DIR / "pb_logo.png"
        if logo_path.exists():
            try:
                img = Image(str(logo_path), width=1.5*inch, height=1*inch)
                img.hAlign = 'CENTER'
                story.append(img)
            except:
                story.append(Paragraph("<b>Purnabramha</b>", title_style))
        else:
            story.append(Paragraph("<b>Purnabramha</b>", title_style))

        story.append(Paragraph("<b>MANASWINI FOODS PVT. LTD.</b>", company_style))
        story.append(Paragraph("17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102", address_style))
        story.append(Spacer(1, 0.2*inch))

        letter_titles = {"offer": "OFFER LETTER", "exit": "EXIT / RESIGNATION ACCEPTANCE LETTER", "experience": "EXPERIENCE CERTIFICATE", "visa": "VISA SUPPORT LETTER"}
        story.append(Paragraph(f"<b>{letter_titles.get(req.letterType, 'HR LETTER')}</b>", title_style))
        story.append(Paragraph(f"Date: {today}", ParagraphStyle('Date', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT)))
        story.append(Spacer(1, 0.2*inch))

        content_lines = req.content.split('\n')
        for line in content_lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.1*inch))
                continue
            line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
            if line.startswith('- '):
                line = f"• {line[2:]}"
            elif line.startswith('* '):
                line = f"• {line[2:]}"
            line = line.replace('&', '&amp;')
            try:
                story.append(Paragraph(line, body_style))
            except:
                clean_line = re.sub(r'<[^>]+>', '', line)
                story.append(Paragraph(clean_line, body_style))

        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("For <b>MANASWINI FOODS PVT. LTD.</b>", signature_style))
        story.append(Spacer(1, 0.1*inch))

        if req.signatory == "jayanti":
            sign_path = ROOT_DIR / "assets" / "signatures" / "jayanti_sign.png"
            signatory_name = "Ms. Jayanti Kathale"
            signatory_title = "Founder, Director"
        else:
            sign_path = ROOT_DIR / "sign.png"
            signatory_name = "Mr. Sandeep Gadhwal"
            signatory_title = "Director"

        if sign_path.exists():
            try:
                sign_img = Image(str(sign_path), width=1.5*inch, height=0.8*inch)
                story.append(sign_img)
            except:
                pass
        story.append(Paragraph(f"<b>{signatory_name}</b>", signature_style))
        story.append(Paragraph(signatory_title, signature_style))

        doc.build(story)
        pdf_buffer.seek(0)
        filename = f"{req.letterType}_letter_{safe_name}_{today.replace('-', '')}.pdf"

        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    elif req.format == "docx":
        from docx import Document
        from docx.shared import Inches, Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        sections = doc.sections
        for section in sections:
            section.left_margin = Inches(0.75)
            section.right_margin = Inches(0.75)
            section.top_margin = Inches(0.5)
            section.bottom_margin = Inches(0.75)

        logo_path = ROOT_DIR / "pb_logo.png"
        if logo_path.exists():
            try:
                para = doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.add_run()
                run.add_picture(str(logo_path), width=Inches(1.5))
            except:
                title = doc.add_paragraph("Purnabramha")
                title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                title.runs[0].bold = True
                title.runs[0].font.size = Pt(18)
        else:
            title = doc.add_paragraph("Purnabramha")
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            title.runs[0].bold = True
            title.runs[0].font.size = Pt(18)

        company = doc.add_paragraph("MANASWINI FOODS PVT. LTD.")
        company.alignment = WD_ALIGN_PARAGRAPH.CENTER
        company.runs[0].bold = True
        company.runs[0].font.size = Pt(12)

        address = doc.add_paragraph("17/N, Ground Floor, 18th Cross, Sector 3, HSR Layout, Bangalore, Karnataka-560102")
        address.alignment = WD_ALIGN_PARAGRAPH.CENTER
        address.runs[0].font.size = Pt(8)

        doc.add_paragraph()

        letter_titles = {"offer": "OFFER LETTER", "exit": "EXIT / RESIGNATION ACCEPTANCE LETTER", "experience": "EXPERIENCE CERTIFICATE", "visa": "VISA SUPPORT LETTER"}
        letter_title = doc.add_paragraph(letter_titles.get(req.letterType, "HR LETTER"))
        letter_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        letter_title.runs[0].bold = True
        letter_title.runs[0].font.size = Pt(14)

        date_para = doc.add_paragraph(f"Date: {today}")
        date_para.runs[0].font.size = Pt(10)
        doc.add_paragraph()

        content_lines = req.content.split('\n')
        for line in content_lines:
            line = line.strip()
            if not line:
                doc.add_paragraph()
                continue
            line = line.replace('**', '')
            para = doc.add_paragraph(line)
            para.runs[0].font.size = Pt(10)
            if line.startswith('- ') or line.startswith('• '):
                para.paragraph_format.left_indent = Inches(0.25)

        doc.add_paragraph()
        doc.add_paragraph()
        sig = doc.add_paragraph("For MANASWINI FOODS PVT. LTD.")
        sig.runs[0].bold = True
        sig.runs[0].font.size = Pt(10)

        if req.signatory == "jayanti":
            sign_path = ROOT_DIR / "assets" / "signatures" / "jayanti_sign.png"
            signatory_name = "Ms. Jayanti Kathale"
            signatory_title = "Founder, Director"
        else:
            sign_path = ROOT_DIR / "sign.png"
            signatory_name = "Mr. Sandeep Gadhwal"
            signatory_title = "Director"

        if sign_path.exists():
            try:
                sig_para = doc.add_paragraph()
                run = sig_para.add_run()
                run.add_picture(str(sign_path), width=Inches(1.5))
            except:
                doc.add_paragraph()
        else:
            doc.add_paragraph()

        director = doc.add_paragraph(signatory_name)
        director.runs[0].bold = True
        director.runs[0].font.size = Pt(10)
        title_para = doc.add_paragraph(signatory_title)
        title_para.runs[0].font.size = Pt(10)

        docx_buffer = BytesIO()
        doc.save(docx_buffer)
        docx_buffer.seek(0)
        filename = f"{req.letterType}_letter_{safe_name}_{today.replace('-', '')}.docx"

        return Response(
            content=docx_buffer.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

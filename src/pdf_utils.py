from fpdf import FPDF
from typing import Optional, Dict
from datetime import datetime


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    # Replace common unicode punctuation with ASCII for built-in fonts
    replacements = (
        ('—', '-'), ('–', '-'), ('“', '"'), ('”', '"'), ('’', "'"),
        ('•', '-'), ('→', '->'), ('←', '<-'), ('…', '...')
    )
    for a, b in replacements:
        text = text.replace(a, b)
    return text

def _safe(text: str) -> str:
    # Normalize, then drop any chars not representable in latin-1
    return _normalize_text(text).encode('latin-1', 'ignore').decode('latin-1')


class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, _safe('AI Trip Planner — Itinerary'), 0, 1, 'C')
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')


def create_pdf(itinerary_markdown: str, user_input: Optional[Dict] = None) -> bytes:
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Cover
    pdf.set_font('Arial', 'B', 18)
    pdf.cell(0, 12, _safe('Your Personalized Travel Itinerary'), 0, 1, 'C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 8, datetime.now().strftime('%Y-%m-%d %H:%M'), 0, 1, 'C')
    pdf.ln(6)

    if user_input:
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, _safe('Trip Summary'), 0, 1)
        pdf.set_font('Arial', '', 11)
        lines = [
            f"From: {user_input.get('source', 'N/A')}",
            f"To: {user_input.get('destination', 'N/A')}",
            f"Dates: {user_input.get('start_date', 'N/A')} to {user_input.get('end_date', 'N/A')}",
            f"People: {user_input.get('num_people', 'N/A')} | Age group: {user_input.get('age_group', 'N/A')}",
            f"Budget/Style: {user_input.get('budget', 'N/A')} {user_input.get('currency', '')} / {user_input.get('travel_style', '')}",
        ]
        for l in lines:
            pdf.cell(0, 7, _safe(l), 0, 1)
        pdf.ln(4)

    # Body — render markdown as plain text safely
    pdf.set_font('Arial', '', 11)
    text = (itinerary_markdown or "").strip()
    # Basic cleanup: strip markdown markers
    for md in ('**', '# ', '## ', '### '):
        text = text.replace(md, '')
    # Normalize unicode to ASCII-friendly
    text = _normalize_text(text)
    for para in text.split('\n'):
        pdf.multi_cell(0, 6, _safe(para))

    # Return as bytes. FPDF returns a Latin-1 encoded string for 'S' dest
    return pdf.output(dest='S').encode('latin-1', 'ignore')



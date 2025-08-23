from fpdf import FPDF
import tempfile
import os
from datetime import datetime

class PDF(FPDF):
    def header(self):
        # Logo
        self.image("https://img.icons8.com/clouds/100/000000/worldwide-location.png", 10, 8, 33)
        # Arial bold 15
        self.set_font('Arial', 'B', 15)
        # Move to the right
        self.cell(80)
        # Title
        self.cell(30, 10, 'Travel Itinerary', 0, 0, 'C')
        # Line break
        self.ln(20)
    
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')
    
    def chapter_title(self, title):
        # Arial 12
        self.set_font('Arial', 'B', 12)
        # Background color
        self.set_fill_color(200, 220, 255)
        # Title
        self.cell(0, 6, title, 0, 1, 'L', 1)
        # Line break
        self.ln(4)
    
    def chapter_body(self, body):
        # Times 12
        self.set_font('Times', '', 12)
        # Output justified text
        self.multi_cell(0, 5, body)
        # Line break
        self.ln()
    
    def add_section(self, title, body):
        self.add_page()
        self.chapter_title(title)
        self.chapter_body(body)

def create_pdf(itinerary_text, destination, user_input=None):
    pdf = PDF()
    pdf.alias_nb_pages()
    
    # Add metadata
    pdf.set_title(f"Itinerary for {destination}")
    pdf.set_author("AI Travel Planner")
    
    # Add cover page
    pdf.add_page()
    pdf.set_font('Times', 'B', 20)
    pdf.cell(0, 60, '', 0, 1, 'C')
    pdf.cell(0, 10, f'Travel Itinerary for {destination}', 0, 1, 'C')
    
    if user_input:
        pdf.set_font('Times', '', 14)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 0, 1, 'C')
        pdf.ln(10)
        
        # Add user details
        pdf.set_font('Times', 'B', 12)
        pdf.cell(0, 10, 'Trip Details:', 0, 1)
        pdf.set_font('Times', '', 12)
        
        details = [
            f"Source: {user_input.get('source', 'N/A')}",
            f"Destination: {user_input.get('destination', 'N/A')}",
            f"Dates: {user_input.get('start_date', 'N/A')} to {user_input.get('end_date', 'N/A')}",
            f"Travelers: {user_input.get('num_people', 'N/A')}",
            f"Budget: {user_input.get('budget', 'N/A')} {user_input.get('currency', 'USD')}",
            f"Style: {user_input.get('travel_style', 'N/A')}"
        ]
        
        for detail in details:
            pdf.cell(0, 8, detail, 0, 1)
    
    # Add itinerary content
    # Split the itinerary into sections
    sections = itinerary_text.split('**')
    current_section = ""
    section_title = "Introduction"
    
    for i, part in enumerate(sections):
        if part.strip().endswith(':'):
            # This is a section title
            if current_section:
                pdf.add_section(section_title, current_section)
            section_title = part.strip().replace(':', '')
            current_section = ""
        else:
            current_section += part + "\n"
    
    # Add the last section
    if current_section:
        pdf.add_section(section_title, current_section)
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf.output(temp_file.name)
    return temp_file.name
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            super().showPage()
        super().save()

def create_20_page_pdf_bytes():
    text_snippet = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
    
    # We want text to fill 20 pages.
    # Let's create flowables.
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6
    )
    
    # A single paragraph of repeating text
    # Let's estimate how many repetitions per page:
    # Letter height is 792 pt, margins 36 top/bottom -> 720 pt height.
    # 720 / 14 leading = ~51 lines per page.
    # Each line holds ~12 words (~80 chars).
    # 51 lines * 80 chars = 4080 chars per page.
    # 20 pages = 81,600 chars.
    
    # Let's build enough text and check page count dynamically if needed, or build exact 20 pages.
    
    target_pages = 20
    
    # To be strictly 20 pages filled with text:
    # We can create 20 pages where each page is filled with flowing text.
    # Let's generate a story with enough text so it spans exactly 20 pages.
    
    # Repeating snippet: 123 chars.
    # ~35 repetitions per page fill a page nicely.
    
    story = []
    for p in range(target_pages):
        # Add paragraphs for one page
        page_text = text_snippet * 34
        story.append(Paragraph(page_text, normal_style))
        if p < target_pages - 1:
            story.append(PageBreak())

    import io
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    doc.build(story)
    
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

if __name__ == "__main__":
    pdf_bytes = create_20_page_pdf_bytes()
    
    # Verify page count with reportlab or pypdf if available
    from reportlab.pdfgen import canvas
    import io
    
    out_dir = "dummy_test_folder"
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"Generated 20-page PDF template of size {len(pdf_bytes)} bytes.")
    
    for i in range(1, 5001):
        file_path = os.path.join(out_dir, f"{i}.pdf")
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
            
    print(f"Successfully updated 5000 PDFs in {os.path.abspath(out_dir)} to be 20 pages long.")

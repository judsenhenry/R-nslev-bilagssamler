import streamlit as st
import os
import tempfile
import hashlib
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from copy import deepcopy

st.set_page_config(page_title="Rønslev Bilagssamler", layout="centered")
st.title("📘 Rønslevs Bilagssamler")

# -------------------------
# Køsystem
# -------------------------
MAX_USERS = 3
if "active_users" not in st.session_state:
    st.session_state.active_users = 0

if st.session_state.active_users >= MAX_USERS:
    st.warning("🚦 Serveren er travl. Prøv igen om lidt ⏳")
    st.stop()

st.session_state.active_users += 1

st.sidebar.header("📈 Serverstatus")
st.sidebar.write(f"Aktive brugere: {st.session_state.active_users} / {MAX_USERS}")

# -------------------------
# Hjælpefunktioner
# -------------------------
def hash_files(file_paths):
    """Lav en simpel hash baseret på filnavn og størrelse"""
    h = hashlib.sha256()
    for f in file_paths:
        h.update(f.encode())
        h.update(str(os.path.getsize(f)).encode())
    return h.hexdigest()

def add_watermark_to_file(input_path, watermark_path, output_path):
    pdf_reader = PdfReader(input_path)
    watermark_reader = PdfReader(watermark_path)
    watermark = watermark_reader.pages[0]
    pdf_writer = PdfWriter()

    for page in pdf_reader.pages:
        new_page = deepcopy(watermark)
        new_page.merge_page(page)
        pdf_writer.add_page(new_page)

    with open(output_path, "wb") as f:
        pdf_writer.write(f)

def create_simple_pdf_file(content, output_path, font='Times-Roman', font_size=18, title_x=100, title_y=800):
    width, height = A4
    can = canvas.Canvas(output_path, pagesize=A4)
    can.setFont(font, font_size)

    side_label_x = 400
    max_width = side_label_x - title_x - 10
    line_height = font_size * 1.2

    words = content.split()
    lines = []
    current = ""
    for w in words:
        test = (current + " " + w).strip() if current else w
        if pdfmetrics.stringWidth(test, font, font_size) <= max_width or current == "":
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)

    for i, line in enumerate(lines):
        y = title_y - i * line_height
        can.drawString(title_x, y, line)

    can.showPage()
    can.save()

def create_table_of_contents_file(titles, page_ranges, output_path):
    can = canvas.Canvas(output_path, pagesize=A4)
    can.setFont('Times-Bold', 18)
    can.drawString(100, 800, "Indholdsfortegnelse")
    can.setFont('Times-Roman', 12)

    top_margin = 760
    bottom_margin = 60
    line_height = 18
    y_pos = top_margin

    num_x = 100
    title_x = 125
    side_label_x = 400
    page_start_x = 450
    max_title_width = side_label_x - title_x - 10

    font_name = 'Times-Roman'
    font_size = 12

    for i, (title, (start, end)) in enumerate(zip(titles, page_ranges), 1):
        prefix = f"{i}."
        words = title.split()
        lines = []
        current_line = ""
        for w in words:
            test_line = (current_line + " " + w).strip() if current_line else w
            width = pdfmetrics.stringWidth(test_line, font_name, font_size)
            if width <= max_title_width or current_line == "":
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = w
        if current_line:
            lines.append(current_line)

        needed_height = line_height * len(lines)
        if y_pos - needed_height < bottom_margin:
            can.showPage()
            can.setFont(font_name, font_size)
            y_pos = top_margin

        first_line_y = y_pos
        can.setFont(font_name, font_size)
        can.setFillColor(colors.black)
        can.drawString(num_x, first_line_y, prefix)
        for li, line in enumerate(lines):
            can.drawString(title_x, y_pos - li * line_height, line)
        can.setFillColor(colors.black)
        can.drawString(side_label_x, first_line_y, "Side")

        can.setFont('Times-Bold', font_size)
        can.setFillColor(colors.blue)
        can.drawString(page_start_x, first_line_y, str(start))
        if end != start:
            start_width = pdfmetrics.stringWidth(str(start), 'Times-Bold', font_size)
            can.drawString(page_start_x + start_width + 2, first_line_y, f"-{end}")

        y_pos = first_line_y - needed_height - (line_height * 0.2)

    can.save()

def add_page_numbers_file(input_path, start_page):
    pdf_reader = PdfReader(input_path)
    num_pages = len(pdf_reader.pages)
    output_path = input_path.replace(".pdf", "_numbered.pdf")
    packet_path = input_path.replace(".pdf", "_numbers.pdf")

    can = canvas.Canvas(packet_path)
    font_name = 'Times-Bold'
    font_size = 12
    bottom_margin = 30

    for i in range(num_pages):
        page = pdf_reader.pages[i]
        llx, lly, urx, ury = map(float, [page.mediabox.lower_left[0], page.mediabox.lower_left[1],
                                         page.mediabox.upper_right[0], page.mediabox.upper_right[1]])
        width = urx - llx
        height = ury - lly
        can.setPageSize((width, height))
        page_num = start_page + i
        text = str(page_num)
        text_width = pdfmetrics.stringWidth(text, font_name, font_size)
        x = (width - text_width) / 2.0
        y = bottom_margin
        can.setFont(font_name, font_size)
        can.setFillColor(colors.blue)
        can.drawString(x, y, text)
        can.showPage()
    can.save()

    numbering_pdf = PdfReader(packet_path)
    pdf_writer = PdfWriter()
    for page, num_page in zip(pdf_reader.pages, numbering_pdf.pages):
        page.merge_page(num_page)
        pdf_writer.add_page(page)

    with open(output_path, "wb") as f:
        pdf_writer.write(f)
    return output_path

def merge_pdfs_disk(pdf_files, watermark_path, start_page, output_path):
    merger = PdfMerger()
    titles = [os.path.splitext(os.path.basename(f))[0] for f in pdf_files]
    page_ranges = []
    current_page = start_page

    # Dummy TOC for beregning
    dummy_toc_path = os.path.join(tempfile.gettempdir(), "dummy_toc.pdf")
    create_table_of_contents_file(titles, [(0, 0)]*len(pdf_files), dummy_toc_path)
    dummy_reader = PdfReader(dummy_toc_path)
    toc_pages = len(dummy_reader.pages)
    current_page += toc_pages

    for pdf in pdf_files:
        front_page = 1
        num_pages = len(PdfReader(pdf).pages)
        page_ranges.append((current_page, current_page + front_page + num_pages - 1))
        current_page += front_page + num_pages

    # TOC med rigtige sider
    toc_path = os.path.join(tempfile.gettempdir(), "toc.pdf")
    create_table_of_contents_file(titles, page_ranges, toc_path)
    toc_watermarked = os.path.join(tempfile.gettempdir(), "toc_watermarked.pdf")
    add_watermark_to_file(toc_path, watermark_path, toc_watermarked)
    merger.append(toc_watermarked)

    # Forsider + bilag
    for title, pdf in zip(titles, pdf_files):
        front_path = os.path.join(tempfile.gettempdir(), f"front_{title}.pdf")
        create_simple_pdf_file(title, front_path)
        front_watermarked = os.path.join(tempfile.gettempdir(), f"front_{title}_wm.pdf")
        add_watermark_to_file(front_path, watermark_path, front_watermarked)
        merger.append(front_watermarked)
        merger.append(pdf)

    with open(output_path, "wb") as f:
        merger.write(f)
    return output_path

# -------------------------
# Cached generation
# -------------------------
@st.cache_data(show_spinner=False)
def generate_pdf_cached(file_paths, watermark_path, start_page):
    output_path = os.path.join(tempfile.gettempdir(), f"cached_{hash_files(file_paths)}.pdf")
    merged_path = merge_pdfs_disk(file_paths, watermark_path, start_page, output_path)
    numbered_path = add_page_numbers_file(merged_path, start_page)
    return numbered_path

# -------------------------
# Streamlit UI
# -------------------------
uploaded_files = st.file_uploader("""
### 📄 Upload dine PDF-bilag
Upload dine **bilagsfiler** herunder.

Appen genkender og sorterer automatisk filerne ud fra deres nummer og underdel, så dine bilag står i korrekt rækkefølge i den samlede PDF.

Det er vigtigt, at filnavnene **starter med 'Bilag'** (eller 'bilag'), efterfulgt af tal, og eventuelt bogstaver og punktum.

#### ✅ Eksempler på gyldige filnavne:
- `Bilag 1 - Statisk system.pdf`  
- `Bilag 3.1 - Etagedæk.pdf`   
- `Bilag 4a - Vindlast.pdf`

#### ⚠️ Undgå disse:
- `bilag1.pdf` *(mangler mellemrum mellem 'Bilag' og tal)*
- `Appendix 1.pdf` *(mangler "Bilag")*  
- `BilagA.pdf` *(ingen tal før bogstav, kan give forkert sortering)*  

Appen sorterer filerne **numerisk** (1, 2, 2.1, 2a, 3.2, 4b …), så dine bilag står i korrekt rækkefølge i den samlede PDF.
""", accept_multiple_files=True, type="pdf")
start_page = st.number_input("Start sidetal", min_value=1, value=2)
watermark_path = os.path.join(os.path.dirname(__file__), "vandmærke.pdf")

if st.button("Generer PDF"):
    if not uploaded_files:
        st.error("Upload dine bilag først.")
    elif not os.path.exists(watermark_path):
        st.error("Filen 'vandmærke.pdf' blev ikke fundet i projektmappen!")
    else:
        with st.spinner("Genererer PDF..."):
            with tempfile.TemporaryDirectory() as tmpdirname:
                temp_files = []
                for uf in uploaded_files:
                    path = os.path.join(tmpdirname, uf.name)
                    with open(path, "wb") as f:
                        f.write(uf.read())
                    temp_files.append(path)

                numbered_path = generate_pdf_cached(temp_files, watermark_path, start_page)

                with open(numbered_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download samlet PDF",
                        f,
                        file_name="samlet_bilag_med_indholdsfortegnelse.pdf",
                        mime="application/pdf"
                    )

st.session_state.active_users -= 1

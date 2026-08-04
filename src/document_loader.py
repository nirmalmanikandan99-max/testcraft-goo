from pypdf import PdfReader
from docx import Document


def read_pdf(uploaded_file):

    reader = PdfReader(uploaded_file)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def read_docx(uploaded_file):

    document = Document(uploaded_file)

    text = ""

    for para in document.paragraphs:

        text += para.text + "\n"

    return text


def read_txt(uploaded_file):

    return uploaded_file.read().decode("utf-8")
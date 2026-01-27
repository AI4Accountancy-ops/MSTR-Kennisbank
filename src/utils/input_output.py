import PyPDF2


def read_pdf_as_text(file_path: str):
    with open(file_path, "rb") as file:
        # Initialize PDF reader
        pdf = PyPDF2.PdfReader(file)

        # Concatenate all frontend text into one string
        text = ""
        for page_num in range(len(pdf.pages)):
            text += pdf.pages[page_num].extract_text()
    return text

from docling.document_converter import DocumentConverter


def extract_document(pdf_path: str):
    """
    Converts a PDF into a Docling document.
    This is the ONLY place that talks to Docling.
    """
    converter = DocumentConverter()

    print(f"Extracting: {pdf_path}")
    result = converter.convert(pdf_path)

    return result.document

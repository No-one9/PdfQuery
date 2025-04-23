# import pdfplumber
# def extract_pdf_metadata(pdf_path):
#     with pdfplumber.open(pdf_path) as pdf:
#         return{
#             "author":pdf.metadata.get("Author",""),
#             "title": pdf.metadata.get("Title",""),
#             "pages": len(pdf.pages)
#         }
# def extract_pdf_tables(pdf_path):
#     tables=[]
#     with pdfplumber.open(pdf_path) as pdf:
#         for page in pdf.pages:
#             tables.extend(page.extract_tables())
#     return tables
# import time
# import requests
# from PyPDF2 import PdfReader, PdfWriter
# from io import BytesIO
# from docling.document_converter import DocumentConverter
# from docling_core.types.io import DocumentStream
# from docling.datamodel.document import ConversionResult
# from app.models.models import Collections
# from app.config.firebase_ref import AsyncFirebaseDataManager

# import requests
# from io import BytesIO
# import time
# import asyncio

# file_collection = Collections.FILE.value


# class PDFParserService:
#     def __init__(self, pages_per_document, firebase_client: AsyncFirebaseDataManager):
#         self.pages_per_document = pages_per_document
#         self.firebase_client = firebase_client
#         self.converter = DocumentConverter()

#     async def split_pdf_into_pages(self, pdf_bytes):
#         reader = PdfReader(pdf_bytes)
#         documents = []
#         for i in range(0, len(reader.pages), self.pages_per_document):
#             writer = PdfWriter()
#             for j in range(self.pages_per_document):
#                 if i + j < len(reader.pages):
#                     writer.add_page(reader.pages[i + j])
#             page_bytes = BytesIO()
#             writer.write(page_bytes)
#             page_bytes.seek(0)
#             documents.append(page_bytes)
#         return documents

#     async def parse_page(self, doc_num, page_bytes):
#         print(f"Processing Sub Document {doc_num}")
#         start_time = time.time()
#         doc_stream = DocumentStream(name=f"doc_{doc_num}.pdf", stream=page_bytes)
#         #  Run the conversion in a background thread (non-blocking)
#         docling_document = await asyncio.to_thread(self.converter.convert, doc_stream)
#         end_time = time.time()
#         print(
#             f"Time taken to process Sub Document {doc_num}: {end_time - start_time} seconds"
#         )
#         print("-" * 100)
#         return doc_num, docling_document

#     async def update_progress(
#         self, document_id: str, progress: int, docling_document: ConversionResult
#     ):
#         file = await self.firebase_client.get_document(file_collection, document_id)

#         # Use a single markdown update process
#         file_markdown = file.get("markdown", {})
#         last_page = len(file_markdown)

#         markdown = {
#             f"page_{i + last_page}": docling_document.document.export_to_markdown(
#                 page_no=i
#             )
#             for i in range(1, len(docling_document.document.pages) + 1)
#         }

#         file_markdown.update(markdown)

#         await self.firebase_client.update_document(
#             file_collection,
#             document_id,
#             {"progress": progress, "markdown": file_markdown},
#         )
#         print(f"Document {document_id} Progress: {progress}")

#     async def process_pdf(self, file_url: str, document_id: str) -> str:
#         try:
#             response = requests.get(file_url)
#             response.raise_for_status()
#         except requests.RequestException as e:
#             print(f"Error fetching PDF from {file_url}: {e}")
#             return None

#         pdf_documents = await self.split_pdf_into_pages(BytesIO(response.content))
#         total_docs = len(pdf_documents)
#         markdown_content = []

#         for doc_num, pdf_doc in enumerate(pdf_documents, start=1):
#             doc_num, page_markdown = await self.parse_page(doc_num, pdf_doc)
#             markdown_content.append(page_markdown)
#             progress = int((doc_num / total_docs) * 100)
#             await self.update_progress(document_id, progress, page_markdown)

#         return document_id

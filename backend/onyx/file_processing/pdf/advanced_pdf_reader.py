import os
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader, PdfWriter
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
from typing import IO
from onyx.utils.logger import setup_logger 

logger = setup_logger()

class AdvancedPDFReader:
    def __init__(self, pdf_file: IO[Any], pdf_pass: str = None):
        """Initialize the PDF reader with a file path."""
        if not pdf_file:
            raise ValueError("AdvancedPDFReader requires a valid PDF file")
        self.pdf_file = pdf_file
        self.reader = PdfReader(pdf_file)
        
        # Handle encrypted PDFs
        if self.reader.is_encrypted:
            if pdf_pass is not None:
                try:
                    decrypt_success = self.reader.decrypt(pdf_pass) != 0
                    if not decrypt_success:
                        raise ValueError("Failed to decrypt PDF with provided password")
                except Exception as e:
                    raise ValueError(f"Error decrypting PDF: {str(e)}")
            else:
                raise ValueError("PDF is encrypted but no password was provided")
        
    def get_metadata(self) -> Dict[str, str]:
        """Extract metadata from the PDF."""
        metadata = {}
        if self.reader.metadata is not None:
            for key, value in self.reader.metadata.items():
                clean_key = key.lstrip("/")
                if isinstance(value, str) and value.strip():
                    metadata[clean_key] = value
                elif isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    metadata[clean_key] = ", ".join(value)
        return metadata

    def extract_native_text(self, page_number: int) -> str:
        """Extract native text from a specific page."""
        try:
            page = self.reader.pages[page_number]
            text = page.extract_text()
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting native text from page {page_number}: {str(e)}")
            return ""

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from an image using OCR."""
        try:
            # Configure tesseract to focus on detecting text in tables
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
            return text.strip()
        except Exception as e:
            logger.error(f"Error performing OCR: {str(e)}")
            return ""

    def merge_texts(self, text1: str, text2: str) -> str:
        """Merge two texts intelligently, removing duplicates and preserving unique content."""
        if not text1:
            return text2
        if not text2:
            return text1
            
        # Split into words/segments for comparison
        segments1 = set(text1.split())
        segments2 = set(text2.split())
        
        # Combine unique segments
        all_segments = segments1.union(segments2)
        return ' '.join(sorted(all_segments))

    def process_page(self, page_number: int) -> Dict[str, Any]:
        """Process a single page using all available methods."""
        result = {
            "native_text": "",
            "ocr_text": "",
            "merged_text": "",
            "page_number": page_number
        }

        # Always extract native text
        result["native_text"] = self.extract_native_text(page_number)

        # Always perform OCR
        try:
            pdf_bytes = io.BytesIO()
            pdf_writer = PdfWriter()
            
            # Add all pages from the reader to the writer
            for page in self.reader.pages:
                pdf_writer.add_page(page)
            
            # Write to BytesIO object
            pdf_writer.write(pdf_bytes)
            pdf_bytes.seek(0)

            # Convert PDF page to image with higher DPI for better OCR
            images = convert_from_bytes(
                pdf_bytes.getvalue(),
                first_page=page_number + 1,
                last_page=page_number + 1,
                dpi=300,  # Higher DPI for better OCR accuracy
                grayscale=True
            )
            if images:
                result["ocr_text"] = "".join(self.extract_text_from_image(image) for image in images)
        except Exception as e:
            logger.error(f"Error converting page {page_number} to image: {str(e)}")
        
        # Merge the texts intelligently
        result["merged_text"] = self.merge_texts(result["native_text"], result["ocr_text"])
        
        return result

    def process_pdf(self) -> List[Dict[str, Any]]:
        """Process all pages in the PDF."""
        results = []
        for page_number in range(len(self.reader.pages)):
            result = self.process_page(page_number)
            results.append(result)
        return results

    def get_complete_text(self) -> str:
        """Get all text from the PDF combining all methods."""
        all_text = []
        
        # Add metadata section at the start
        metadata = self.get_metadata()
        if metadata:
            all_text.append("=== Document Metadata ===")
            for key, value in metadata.items():
                all_text.append(f"{key}: {value}")
            all_text.append("=" * 30 + "\n")
        
        # Process all pages
        results = self.process_pdf()

        for result in results:
            page_text = []
            
            # Add native text if available
            if result["native_text"]:
                page_text.append(result["native_text"])
            
            # Add OCR text if available and different from native text
            if result["ocr_text"] and result["ocr_text"] != result["native_text"]:
                page_text.append(result["ocr_text"])
            
            # Combine all text from this page
            if page_text:
                all_text.append(f"\n--- Page {result['page_number'] + 1} ---\n")
                all_text.extend(page_text)
        
        return "\n".join(all_text)

    def extract_images(self) -> List[Tuple[bytes, str]]:
        """Extract all images from the PDF file.
        
        Returns:
            List of tuples containing (image_bytes, image_name)
        """
        extracted_images: List[Tuple[bytes, str]] = []
        
        try:
            for page_num, page in enumerate(self.reader.pages):
                for image_file_object in page.images:
                    try:
                        image = Image.open(io.BytesIO(image_file_object.data))
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format=image.format)
                        img_bytes = img_byte_arr.getvalue()

                        image_name = (
                            f"page_{page_num + 1}_image_{image_file_object.name}."
                            f"{image.format.lower() if image.format else 'png'}"
                        )
                        extracted_images.append((img_bytes, image_name))
                    except Exception as e:
                        logger.error(f"Failed to extract image from page {page_num + 1}: {str(e)}")
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to extract images from PDF: {str(e)}")
            
        return extracted_images

if __name__ == "__main__":
    reader = AdvancedPDFReader(open("image_financial_statement.pdf", "rb"))
    print(reader.get_complete_text())
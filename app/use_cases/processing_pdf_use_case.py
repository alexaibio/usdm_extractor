import os
from logging import Logger
from pathlib import Path
from typing import Callable, Any
from injector import inject
from app.core.settings import Settings
from app.services.pdf_convertor import PDFConvertor
from app.services.pdf_convertor_v3 import PDFConvertorV3
#from app.utils.utils import find_all_files


class ProcessingPdfUseCase:
    @inject
    def __init__(self, pdf_convertor: PDFConvertorV3, logger: Logger):
        # change PDFConvertorV3 annotation here to use another convertor like PDFConvertor
        self._pdf_convertor = pdf_convertor
        self._logger = logger


    def run_extraction(self, pdf_file: Path, output_dir: str):
        """
        Run PDF parsing, Hide extractions_func from outer user
        """
        self._process_extracts(self._extracts_from_pdf, pdf_file, output_dir)


    def _process_extracts(self, extractions_func: Callable[..., Any], pdf_file_path: Path, output_dir: str):

        self._logger.info(f"   Processing file: {pdf_file_path}")

        output_filename = Path(pdf_file_path).stem + ".txt"
        output_txt_file_path = os.path.join(output_dir, output_filename)

        try:
            extracted_text = extractions_func(pdf_file_path, output_dir)

            with open(output_txt_file_path, 'w', encoding='utf-8') as file:
                file.write(extracted_text)
            self._logger.info(f"Extracted text written to {output_txt_file_path}")

        except FileNotFoundError as fnf_error:
            self._logger.error(f"File not found: {fnf_error}", exc_info=True)
        except IOError as io_error:
            self._logger.error(f"IO error: {io_error}", exc_info=True)
        except Exception as e:
            self._logger.error(f"An error occurred processing {pdf_file_path}: {e}", exc_info=True)


    def _extracts_from_pdf(self, file_path: str, output_dir:str) -> str:
        # TODO: have two steps: extract text and extract table to csv
        return self._pdf_convertor.extract_text_from_pdf(file_path, output_dir=output_dir)

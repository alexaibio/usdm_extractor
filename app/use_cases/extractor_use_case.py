import os
from logging import Logger
from pathlib import Path
from typing import Callable, Any
from injector import inject
from app.core.settings import Settings
from app.services.pdf_extractor import PDFConvertor
from app.services.pdf_convertor_v3 import PDFConvertorV3
#from app.utils.utils import find_all_files


class ExtractorUseCase:
    @inject
    def __init__(self, pdf_convertor: PDFConvertorV3, logger: Logger):
        # change PDFConvertorV3 annotation here to use another convertor like PDFConvertor
        self._pdf_convertor = pdf_convertor
        self._logger = logger


    def run_extraction(self, input_path:str, output_path:str):
        """
        Run PDF parsing, Hide extractions_func from outer user
        """
        self._process_extracts(self._extracts_from_pdf, input_path, output_path)


    def _process_extracts(self, extractions_func: Callable[..., Any], input_path:str, output_path:str):
        self._logger.info(f"Starting processing for input directory: {input_path}")

        all_files  = list(Path(input_path).glob("*.pdf"))

        for file_path in all_files:
            self._logger.info(f"Processing file: {file_path}")

            output_filename = Path(file_path).stem + ".txt"
            output_file_path = os.path.join(output_path, output_filename)

            try:
                extracted_text = extractions_func(file_path, output_path)

                with open(output_file_path, 'w', encoding='utf-8') as file:
                    file.write(extracted_text)
                self._logger.info(f"Extracted text written to {output_file_path}")

            except FileNotFoundError as fnf_error:
                self._logger.error(f"File not found: {fnf_error}", exc_info=True)
            except IOError as io_error:
                self._logger.error(f"IO error: {io_error}", exc_info=True)
            except Exception as e:
                self._logger.error(f"An error occurred processing {file_path}: {e}", exc_info=True)


    def _extracts_from_pdf(self, file_path: str, output_dir:str) -> str:
        return self._pdf_convertor.extract_text_from_pdf(file_path, output_dir=output_dir)

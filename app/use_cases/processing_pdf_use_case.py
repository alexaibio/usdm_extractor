import os
import pandas as pd
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
    # change PDFConvertorV3 annotation here to use another convertor like PDFConvertor
    def __init__(self, pdf_convertor: PDFConvertorV3, logger: Logger):
        self._pdf_convertor = pdf_convertor
        self._logger = logger


    def run_extraction_pipeline(self, pdf_file: Path, output_dir: str):
        """
        Run PDF parsing, Hide extractions_func from outer user (function injection pattern)
        can use different extractors, pdf->text, pdf->tables etc
        """
        self._process_extracts(self._pdf_convertor.extract_text_from_pdf, pdf_file, output_dir)


    def _process_extracts(self, extractions_func: Callable[..., Any], pdf_file_path: Path, output_dir: str):
        """
        Extract a piece of info (text, table etc) from pdf and save it
        """
        self._logger.info(f"   Processing file: {pdf_file_path}")

        output_filename = Path(pdf_file_path).stem + ".txt"
        output_txt_file_path = os.path.join(output_dir, output_filename)

        try:
            extracted_item = extractions_func(pdf_file_path, output_dir)

            if isinstance(extracted_item, str):
                with open(output_txt_file_path, 'w', encoding='utf-8') as file:
                    file.write(extracted_item)
            elif isinstance(extracted_item, pd.DataFrame):
                extracted_item.to_csv(output_txt_file_path.replace(".txt", ".csv"), index=False)
            else:
                raise ValueError("Unsupported extracted result type")

            self._logger.info(f"Extracted item is written to {output_txt_file_path}")

        except FileNotFoundError as fnf_error:
            self._logger.error(f"File not found: {fnf_error}", exc_info=True)
        except IOError as io_error:
            self._logger.error(f"IO error: {io_error}", exc_info=True)
        except Exception as e:
            self._logger.error(f"An error occurred processing {pdf_file_path}: {e}", exc_info=True)



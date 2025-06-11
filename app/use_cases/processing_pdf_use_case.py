import os
import pandas as pd
from logging import Logger
from pathlib import Path
from typing import Callable, Any
from injector import inject

from app.core.settings import Settings
from app.services.pdf_convertor import PDFConvertor
from app.services.pdf_convertor_v3 import PDFConvertorV3



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
        # extract text pages - [_pdf_convertor.extract_text_pages_from_pdf]
        self._process_extracts_and_save(self._pdf_convertor.extract_text_pages_from_pdf, pdf_file, output_dir)

        # extract activity and objective tables
        self._process_extracts_and_save(self._pdf_convertor.extract_activity_tables_from_pdf, pdf_file, output_dir)
        self._process_extracts_and_save(self._pdf_convertor.extract_objectives_tables_from_pdf, pdf_file, output_dir)


    def _process_extracts_and_save(self, extractions_func: Callable[..., Any], pdf_file_path: Path, output_dir: str):
        """
        Extract a piece of info (text, table etc) from pdf and save it
        """
        self._logger.info(f"   Processing file: {pdf_file_path}")

        suffix_map = {
            "extract_activity_tables_from_pdf": "_activities",
            "extract_objectives_tables_from_pdf": "_objectives",
            "extract_text_pages_from_pdf": "",
        }

        file_suffix = suffix_map.get(extractions_func.__name__)

        output_stem = pdf_file_path.stem + file_suffix
        output_txt_path = Path(output_dir) / f"{output_stem}.txt"

        try:
            result = extractions_func(pdf_file_path)

            if isinstance(result, list):
                content = "\n\n                                     --- PAGE ---\n\n".join(result)
                output_txt_path.write_text(content, encoding='utf-8')
                self._logger.info(f"   Writing TXT to {output_txt_path}")

            elif isinstance(result, pd.DataFrame):
                output_csv_path = output_txt_path.with_suffix('.csv')
                result.to_csv(output_csv_path, index=False)
                self._logger.info(f"   Writing TABLE to {output_csv_path}")

            else:
                raise TypeError(f"Unsupported extracted result type: {type(result)}")

        except FileNotFoundError as e:
            self._logger.error(f"File not found: {e}", exc_info=True)
        except IOError as e:
            self._logger.error(f"I/O error: {e}", exc_info=True)
        except Exception as e:
            self._logger.error(f"An unexpected error occurred: {e}", exc_info=True)

        # output_filename = Path(pdf_file_path).stem + file_suffix +".txt"
        # output_txt_file_path = os.path.join(output_dir, output_filename)
        #
        # try:
        #     extracted_item = extractions_func(pdf_file_path)
        #
        #     if isinstance(extracted_item, list):
        #         with open(output_txt_file_path, 'w', encoding='utf-8') as file:
        #             file.write("\n\n                                     --- PAGE ---\n\n".join(extracted_item))
        #         self._logger.info(f"   Writing TXT to {output_txt_file_path}")
        #     elif isinstance(extracted_item, pd.DataFrame):
        #         csv_file_path = output_txt_file_path.replace(".txt", ".csv")
        #         extracted_item.to_csv(csv_file_path, index=False)
        #         self._logger.info(f"   Writing TABLE to {csv_file_path}")
        #     else:
        #         raise ValueError("Unsupported extracted result type")
        #
        # except FileNotFoundError as fnf_error:
        #     self._logger.error(f"File not found: {fnf_error}", exc_info=True)
        # except IOError as io_error:
        #     self._logger.error(f"IO error: {io_error}", exc_info=True)
        # except Exception as e:
        #     self._logger.error(f"An error occurred processing {pdf_file_path}: {e}", exc_info=True)
        #
        #

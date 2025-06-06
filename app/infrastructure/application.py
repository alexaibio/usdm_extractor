import logging
import os
from pathlib import Path
from injector import inject
from app.core.settings import Settings
from app.use_cases.processing_pdf_use_case import ProcessingPdfUseCase


class Application:
    @inject
    def __init__(self,
                 processing_pdf_use_case: ProcessingPdfUseCase,
                 settings: Settings,
                 logger: logging.Logger):
        self._processing_pdf_use_case = processing_pdf_use_case
        self._input_dir = settings.INPUT_DIR
        self._output_dir = settings.OUTPUT_DIR
        self._logger = logger

    def launch(self):
        self._logger.info("Running the application.")

        Path(self._output_dir).mkdir(parents=True, exist_ok=True)

        pdf_files = list(Path(self._input_dir).glob("*.pdf"))
        if not pdf_files:
            self._logger.warning(f"No PDF files found in {self._input_dir}")
            return
        self._logger.info(f"Scanning {self._input_dir} folder... {len(pdf_files)} files found.")

        for pdf_file in pdf_files:
            self._processing_pdf_use_case.run_extraction_pipeline(
                pdf_file=pdf_file,
                output_dir=self._output_dir
            )






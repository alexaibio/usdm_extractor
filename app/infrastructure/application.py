import logging
import os
from pathlib import Path
from injector import inject
from app.core.settings import Settings
from app.use_cases.extractor_use_case import ExtractorUseCase


class Application:
    @inject
    def __init__(self,
                 extractor_use_case: ExtractorUseCase,
                 settings: Settings,
                 logger: logging.Logger):
        self._extractor_use_case = extractor_use_case
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

        for pdf_file in pdf_files:
            self._logger.info(f"Extracting: {pdf_file.name} → {self._output_dir}")
            self._extractor_use_case.run_extraction(
                input_path=self._input_dir,
                output_path=self._output_dir
            )





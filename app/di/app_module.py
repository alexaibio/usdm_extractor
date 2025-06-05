import logging
from injector import singleton, Module
from app.core.settings import get_settings, Settings
from app.services.pdf_extractor import GrobidClient
from app.services.pdf_extractor import PDFConvertor
from app.services.pdf_convertor_v3 import PDFConvertorV3


class AppModule(Module):
    def configure(self, binder):
        settings = get_settings()

        logger = logging.getLogger("USDM")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)

        binder.bind(Settings, to=settings, scope=singleton)
        binder.bind(logging.Logger, to=logger, scope=singleton)

        grobid_client = GrobidClient(settings.GROBID_URL)
        binder.bind(GrobidClient, to=grobid_client, scope=singleton)

        # can remove it because injector gets it from Annotation
        pdf_convertor = PDFConvertor(client=grobid_client, settings=settings)
        binder.bind(PDFConvertor, to=pdf_convertor, scope=singleton)

        pdf_convertor_v3 = PDFConvertorV3()
        binder.bind(PDFConvertorV3, to=pdf_convertor_v3, scope=singleton)


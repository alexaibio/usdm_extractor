import os
import sys
sys.path.append(os.path.abspath(os.sep.join(os.path.dirname(__file__).split(os.sep)[:-1])))
from injector import Injector
from app.di.app_module import AppModule
from app.infrastructure.application import Application


def main():
    injector = Injector([AppModule()])

    # Create an instance of Application and resolve all its constructor arguments using the bindings you’ve configured
    # injector must provide: extractor_use_case, setting, logger
    # it gets it from app_module binding section
    application = injector.get(Application)
    application.launch()


if __name__ == "__main__":
    main()

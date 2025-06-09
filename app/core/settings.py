from functools import lru_cache
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROBID_URL: str = 'http://localhost:8070'
    INPUT_DIR: str = './data/input_dir'
    OUTPUT_DIR: str = './data/output_dir'
    HG_API_KEY: str

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
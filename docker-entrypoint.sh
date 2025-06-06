#!/usr/bin/env bash

export PYTHONPATH=/home:$PYTHONPATH

python ./app/pdf_extractor_app.py
python ./app/pipeline.py
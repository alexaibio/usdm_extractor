#!/usr/bin/env bash

export PYTHONPATH=/home:$PYTHONPATH

python ./app/pdf_extractor.py
python ./app/pipeline.py
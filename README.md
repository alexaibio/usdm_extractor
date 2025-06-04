# A converter from PDF to USDM
The app converts a PDF with human created clinical trial protocol into 
standartized USDM json file.
Along the way all biological consepts (BC) are identified and connected 
to actions extracted from PDF file.


# Features
- find in PDF file a "Schedule of Activity" SoA section
- use Grobid to parce PDF (best pdf parser up to now - https://hub.docker.com/r/grobid/grobid/tags)
- extract every line of this section  as an activity
- use LLM to detect any BC
- form a final JSON

# Prerequisites
- Docker

# Getting Started
From inside the project folder run:
   ```
   docker-compose up 
   ```
If you want to debug and have grobid in a separate docker, run
```
docker run -it -p 8070:8070 grobid/grobid:0.8.1
or
docker run -it -p 8070:8070 grobid/grobid:0.6.2
```


## Usage

The app uses two external mounted folders:

1. `input_dir`: The input directory containing PDF of clinical trial
2. `output_dir`: The output directory where extracted USDM.json will be saved

GROBID NOTE:  
- platform: linux/amd64
- in case of MAC ARM IS, use old version 0.6.2, in case of AMD64 IS use 0.8.2
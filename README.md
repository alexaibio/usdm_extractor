# A converter from PDF to USDM
The app converts a PDF with human created clinical trial protocol into 
standartized USDM json file.
Along the way all biological consepts (BC) are identified and connected 
to actions extracted from PDF file.


# Features
- find in PDF file a "Schedule of Activity" SoA section
- parce PDF, extract a SoA table with several heuristics (for now)
  - option 1: use Grobid as a docker service to parce PDF (https://hub.docker.com/r/grobid/grobid/tags)
  - option2: use pdfplumber / camelot, no extra docker shall be run
  - option3: use LLM or CNN to detect table - NotImplementedYet
- extract every line of this section as an activity
- run LLM from one of the provider (or local) to extract from this line an Activity and possible BiomedicalConcept sections
- add Activity section to final USDM json
- call OSB API to add that Activity to Open Stady Builder application (run in docker)

# Prerequisites
- Docker

# Getting Started
From inside the project folder run:
   ```
   docker-compose up 
   ```
If you want to debug locally and run grobid in a separate docker, run
```
docker run -it -p 8070:8070 grobid/grobid:0.8.1
or
docker run -it -p 8070:8070 grobid/grobid:0.6.2
```
If you like to call OSB API, the OSB docker-copmose miust be run as well.

## Usage

The app uses two external mounted folders:

1. `input_dir`: The input directory containing PDF of clinical trial
2. `output_dir`: The output directory where the following files will be saved
   3. clinical_trial.txt - text extracted from PDF
   4. clinical_trial_name.csv - an extracted and converted table of activities 

GROBID Installation NOTE:  
The following docker-compose lines must be edited depending on what you use: ARM or Intel instruction set
- platform: linux/amd64
- in case of MAC ARM IS, use old version 0.6.2, in case of AMD64 IS use 0.8.2
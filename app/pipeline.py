import os
import sys
sys.path.append(os.path.abspath(os.sep.join(os.path.dirname(__file__).split(os.sep)[:-1])))
import yaml
import json
from pathlib import Path


# Define an Activity with a nested Procedure
activity = {
    "id": "Activity_1",
    "name": "INFORMED_CONSENT",
    "label": "Informed Consent",
    "description": "Informed Consent",
    "previousId": None,
    "nextId": "Activity_2",
    "childIds": [],
    "definedProcedures": [
        {
            "id": "Procedure_1",
            "name": "INFORMED_CONSENT",
            "label": "Informed Consent",
            "description": "Obtain informed consent from subject",
            "extensionAttributes": []
        }
    ],
    "extensionAttributes": [],
    "biomedicalConceptIds": ["BC_1"]
}

def pipeline():

    ## TEST
    base_path = Path(__file__).parent
    with open(base_path / "json_templates" / "usdm_template.yaml", "r", encoding="utf-8") as f:
        usdm_data = yaml.safe_load(f)

    study_version = usdm_data["study"]["versions"][0]
    study_design = study_version["studyDesigns"][0]

    # Add entries
    study_design["activities"].append(activity)

    # Export to JSON
    with open(base_path /"json_templates" / "usdm_filled.json", "w") as file:
        json.dump(usdm_data, file, indent=2)

    ##### Pipeline outline:
    # pdf exractor shall be already run and generate a CSV file for SoA items

    # the idea is to submit that table to LLM and ask to fill in the activity item
    # by a few short learning (an example inside the prompt)

    # Finally need an API call to post in into OSB



if __name__ == '__main__':
    pipeline()



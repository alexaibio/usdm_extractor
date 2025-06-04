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
    base_path = Path(__file__).parent
    with open(base_path / "usdm_template.yaml", "r", encoding="utf-8") as f:
        usdm_data = yaml.safe_load(f)

    study_version = usdm_data["study"]["versions"][0]
    study_design = study_version["studyDesigns"][0]

    # Add entries
    study_design["activities"].append(activity)

    # Export to JSON
    with open(base_path / "usdm_filled.json", "w") as file:
        json.dump(usdm_data, file, indent=2)




if __name__ == '__main__':
    pipeline()



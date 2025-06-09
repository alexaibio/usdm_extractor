import os
import sys
import asyncio
import json

import yaml
from pathlib import Path

from app.core.settings import get_settings
from app.models.provider_schema import LLMProvider
from app.infrastructure.llm.llm_client_factory import LLMClientFactory, llm_client_factory

sys.path.append(os.path.abspath(os.sep.join(os.path.dirname(__file__).split(os.sep)[:-1])))

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

setings = get_settings()
base_path = Path(__file__).parent       # TODO: remove late


def test_pipeline():
    #####  EXAMPLE how to work with json

    with open(base_path / "json_templates" / "usdm_template.yaml", "r", encoding="utf-8") as f:
        usdm_data = yaml.safe_load(f)

    study_version = usdm_data["study"]["versions"][0]
    study_design = study_version["studyDesigns"][0]

    # Add entries
    study_design["activities"].append(activity)

    # Export to JSON
    with open(base_path / setings.OUTPUT_DIR / "usdm_filled.json", "w") as file:
        json.dump(usdm_data, file, indent=2)



async def pipeline():
    # TODO: refactor it to be Application with dependency injection

    # load extracted Activity CSV table and temple
    output_dir = setings.OUTPUT_DIR
    csv_files = list(Path(output_dir).glob("*.csv"))

    template_path = base_path / "json_templates" / "activity_example.json"
    with open(template_path, "r", encoding="utf-8") as f:
        activity_template = f.read()

    # get LLM client
    llm_client = llm_client_factory.of(LLMProvider.hg_local)
    #model = "meta-llama/Meta-Llama-3-8B-Instruct"       # GPT-2, maximum context length of 1024 tokens
    model = "mistralai/Mistral-7B-Instruct-v0.2"
    prompt_template = f"""
    You are a clinical data structuring assistant.

    The following is a CSV table extracted from a clinical trial protocol. Your task is to analyze the table and extract each activity (such as informed consent, screening, dosing, assessments, etc.) along with its relevant details.

    Use the following JSON structure template for each activity (fill in "NA" for unknown values):

    {activity_template}

    Return only a JSON array of such activity objects.

    Here is the table:
    """

    for csv_file in csv_files:
        csv_text = csv_file.read_text(encoding="utf-8")
        prompt = prompt_template + csv_text

        result_json = await llm_client.generate(
            operation="activity_CSV_to_JSON",
            model=model,
            prompt=prompt
        )
        print(result_json)

        # safe json to output dir
        output_file = Path(output_dir) / f"{csv_file.stem}_activities.json"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result_json)

    print("All activity JSONs have been generated")




if __name__ == '__main__':
    #test_pipeline()
    asyncio.run(pipeline())



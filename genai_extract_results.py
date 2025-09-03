from io import BytesIO
from google import genai
from google.genai import types
from itables import show
import extract_results_prompt
import os
import re

print("Key loaded?", os.getenv("GEMINI_API_KEY") is not None)

import pandas as pd
import json

def json_to_dataframe(response_text: str) -> pd.DataFrame:
    """
    Converts Google Gemini JSON response text into a pandas DataFrame.
    
    Args:
        response_text (str): JSON string returned by the AI.
    
    Returns:
        pd.DataFrame: DataFrame with two columns: 'Field' and 'Value'.
    """
    # Parse the JSON string into a Python dictionary
    cleaned_text = re.sub(r"^```json\s*|\s*```$", "", response_text.strip(), flags=re.MULTILINE)
    data_dict = json.loads(cleaned_text)
    
    # Convert dictionary to DataFrame
    df = pd.DataFrame(list(data_dict.items()), columns=["Field", "Value"])
    
    return df

def get_gemini_client(api_key=None):
    key = api_key or os.getenv("GEMINI_API_KEY")
    assert key is not None, "GEMINI_API_KEY must be provided either via argument or environment"
    return genai.Client(api_key=key)
    
####################################
# Extract Results for a given file BytesIO Object
####################################
def get_extracted_results(quarter, year, type, pdf_bytesIO, api_key=None):
    client = get_gemini_client(api_key)

    pdf_bytesIO.seek(0)
    file = client.files.upload(file=pdf_bytesIO, config={"mime_type": "application/pdf"})

    # Your refined prompt (use the one we crafted earlier)
    instructions = extract_results_prompt.instruction
    prompt = extract_results_prompt.Prompt.format(quarter=quarter, year=year, type=type)

    response = client.models.generate_content(
        model="gemini-2.5-flash",   # free model
        config=types.GenerateContentConfig(
            system_instruction=instructions),
        contents=[
            {"file_data": {"file_uri": file.uri}},
            {"text": prompt}
        ],
    )
    return response

if __name__ == "__main__":
    """
    pdf_path = "PDF Files/1.pdf"
    quarter = "Q1"
    year = "FY2023"
    type = "Consolidated"   
    # Upload the PDF file
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
        file_like = BytesIO(file_bytes)

    response = get_extracted_results(quarter, year, type, pdf_path)
    df = json_to_dataframe(response.text)
    show(df)
    """
    client = get_gemini_client()
    print(client.models.generate_content(
        model="gemini-2.5-flash",   # free model
        
        contents=[
            {"text": "hi"}
        ],
    ))

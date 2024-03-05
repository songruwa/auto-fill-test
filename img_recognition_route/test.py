path_ = "/Users/luke/Downloads/rb_document_intelligence-main/birth_certificates/indian_birth_certificate_sample.jpeg"
with open(path_, "rb") as f:
    doc = f.read()
    poller = document_analysis_client.begin_analyze_document("prebuilt-document", doc)
    result = poller.result()
    
OPENAI_API_KEY = "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"
import json
def generate_from_gpt(prompt, max_tokens, oai_key=OPENAI_API_KEY, temperature=0):
    from openai import OpenAI
    client = OpenAI(api_key=oai_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are an experienced document helper."},
            {"role": "user", "content": prompt}
        ],
        seed=42,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={ "type": "json_object" }
    )
    res = response.choices[0].message.content
    return res
p = """Help extract the father's and mother's name from the extracted text of the birth certificate. Provide nationality of the parents if available. Nationality should be COUNTRY NAME. If the information is in a different language, you MUST TRANSLATE it to English.
Answer under json keys father_first_name, father_last_name, mother_first_name, mother_last_name, father_nationality, mother_nationality. If any value is in a different language, TRANSLATE TO ENGLISH.
""" + result.content
res = generate_from_gpt(p, 100)
# if any char in res is not letter
if not res.isalpha():
    print("Ran GPT again")
    res = generate_from_gpt(f"Translate the non-English part in following content into English: {res}. Keep the original json format", 100, temperature=0)
print(json.dumps(json.loads(res), indent=4))
# import the necessary packages
import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import argparse
import sys
from flask import Flask, request, jsonify
from openai import OpenAI
import json

# Build the Flask router
app = Flask(__name__)

# This is proof of conecpt, Please use environment variables for authentications
key = "784f94c9ebb94ac787f3cd8423ecb4a3"
endpoint = "https://leazyai-instance.cognitiveservices.azure.com/"
OPENAI_API_KEY = "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"


# formatting function
def format_polygon(polygon):
    if not polygon:
        return "N/A"
    return ", ".join(["[{}, {}]".format(p.x, p.y) for p in polygon])

# formatting function
def format_bounding_region(bounding_regions):
    if not bounding_regions:
        return "N/A"
    return ", ".join("Page #{}: {}".format(region.page_number, format_polygon(region.polygon)) for region in bounding_regions)

# read model, for hard coded file
def analyze_read(formUrl):
    # sample document
    #formUrl = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/read.png"

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    poller = document_analysis_client.begin_analyze_document_from_url(
        "prebuilt-read", formUrl
    )
    result = poller.result()

    print("Document contains content: ", result.content)

    for idx, style in enumerate(result.styles):
        print(
            "Document contains {} content".format(
                "handwritten" if style.is_handwritten else "no handwritten"
            )
        )

    for page in result.pages:
        print("----Analyzing Read from page #{}----".format(page.page_number))
        print(
            "Page has width: {} and height: {}, measured with unit: {}".format(
                page.width, page.height, page.unit
            )
        )

        for line_idx, line in enumerate(page.lines):
            print(
                "...Line # {} has text content '{}' within bounding box '{}'".format(
                    line_idx,
                    line.content,
                    format_polygon(line.polygon),
                )
            )

        for word in page.words:
            print(
                "...Word '{}' has a confidence of {}".format(
                    word.content, word.confidence
                )
            )

    print("----------------------------------------")

def create_dict(user_id):
    '''
    create an empty python dict for the current user

    Args:
    user_id(string): unique id for each user
    '''
    person_info_template = {
        user_id: {
            "First_Name": None,
            "Middle_Name": None,
            "Last_Name": None,
            "DOB": None,
            "Gender": None,
            "Place_of_Birth": None,
            "Father_Information": None,
            "Mother_Information": None,
            "Country_of_Nationality": None,
            "Address_within_US": None,
            "Address_not_within_US": None,
            "Passport_Number": None,
            "Alien_Registration_Number": None,
            "Date_of_Entry": None,
            "Class_of_Admission": None
        }
    }

    return person_info_template

def collect_info_State_DL(user_id, user_dict, key_val):
    '''
    write fields extracted from state DL to current user dict

    Args:
    user_id(string): unique id for each user
    dict: a python dict of dict, key is user_id while value is all user info

    Returns:
    a python dict of dict, key is user_id while value is all user info

    1st precedence of extraction in the following: 
        Address, within US
    2nd precedence of extraction in the following: 
        DOB, Gender
    4th precedence of extraction in the following:
        Surname, Given Name 
    '''
    cur_key, cur_val = key_val

    if cur_key == "FirstName":
        user_dict[user_id]["First_Name"] = str(cur_val)
    elif cur_key == "LastName":
        user_dict[user_id]["Last_Name"] = str(cur_val)
    elif cur_key == "DateOfBirth":
        user_dict[user_id]["DOB"] = str(cur_val)
    elif cur_key == "Sex":
        user_dict[user_id]["Gender"] = str(cur_val)
    elif cur_key == "Address":
        user_dict[user_id]["Address_within_US"] = str(cur_val)

    return user_dict

def collect_info_passport_front_page(user_id, user_dict, key_val):
    '''
    write fields extracted from passport to current user dict

    Args:
    user_id(string): unique id for each user
    dict: a python dict of dict, key is user_id while value is all user info

    Returns:
    a python dict of dict, key is user_id while value is all user info

    1st precedence of extraction in the following: 
        Surname, Given Name, DOB, Gender, Country of Nationality, passport number
    '''
    cur_key, cur_val = key_val
    
    if cur_key == "FirstName":
        user_dict[user_id]["First_Name"] = str(cur_val)
    elif cur_key == "LastName":
        user_dict[user_id]["Last_Name"] = str(cur_val)
    elif cur_key == "DateOfBirth":
        user_dict[user_id]["DOB"] = str(cur_val)
    elif cur_key == "Sex":
        user_dict[user_id]["Gender"] = str(cur_val)
    elif cur_key == "CountryRegion":
        user_dict[user_id]["Country_of_Nationality"] = str(cur_val)
    elif cur_key == "DocumentNumber":
        user_dict[user_id]["Passport_Number"] = str(cur_val)

    return user_dict
    
def collect_info_non_immigrant_visa(user_id, user_dict, key_val):
    '''
    write fields extracted from non_immigrant_visa to current user dict

    Args:
    user_id(string): unique id for each user
    dict: a python dict of dict, key is user_id while value is all user info

    Returns:
    a python dict of dict, key is user_id while value is all user info

    1st precedence of extraction in the following:
        Alien Registration Number

    2rd precedence of extraction in the following:
        Country of Nationality, Passport Number

    3rd precedence of extraction in the following: 
        Surname, Given Name, DOB, Gender
    
    '''
    cur_key, cur_val = key_val
    if cur_key == "Given Name":
        user_dict[user_id]["First_Name"] = str(cur_val)
    elif cur_key == "Surname":
        user_dict[user_id]["Last_Name"] = str(cur_val)
    elif cur_key == "Birth Date":
        user_dict[user_id]["DOB"] = str(cur_val)
    elif cur_key == "Sex":
        user_dict[user_id]["Gender"] = str(cur_val)
    elif cur_key == "Nationality":
        user_dict[user_id]["Country_of_Nationality"] = str(cur_val)
    elif cur_key == "Passport Number":
        user_dict[user_id]["Passport_Number"] = str(cur_val)
    elif cur_key == "Control Number":
        user_dict[user_id]["Alien_Registration_Number"] = str(cur_val)

    return user_dict

# I94
def collect_info_I94(user_id, user_dict, key_val):
    '''

    Sample： https://www.uscis.gov/sites/default/files/images/article-i9-central/I-94A.jpg

    write fields extracted from I94 to current user dict

    Args:
    user_id(string): unique id for each user
    dict: a python dict of dict, key is user_id while value is all user info

    Returns:
    a python dict of dict, key is user_id while value is all user info

    1st precedence of extraction in the following:
        Surname, Given Name, DO
    
    2rd precedence of extraction in the following:
        Country of National
    
    3rd precedence of extraction in the following:
        Passport Number
    '''
    cur_key, cur_val = key_val
    if cur_key == "First (Given) Name":
        user_dict[user_id]["First_Name"] = str(cur_val)
    elif cur_key == "Family Name":
        user_dict[user_id]["Last_Name"] = str(cur_val)
    elif "Birth Date" in cur_key:
        user_dict[user_id]["DOB"] = str(cur_key)
    elif cur_key == "Country of Citizenship":
        user_dict[user_id]["Country_of_Nationality"] = str(cur_val)
    elif cur_key == "Passport Number":
        user_dict[user_id]["Passport_Number"] = str(cur_val)
    elif cur_key == "Date of Entry":
        user_dict[user_id]["Date_of_Entry"] = str(cur_val)
    elif cur_key == "Class of Admission":
        user_dict[user_id]["Class_of_Admission"] = str(cur_val)
    
    return user_dict

def collect_info_state_ID(user_id, user_dict, key_val):
    '''
    Sample Doc: 
    https://americansecuritytoday.com/wp-content/uploads/2018/04/Sample-New-York-State-DMV-Photo-Documents-1.jpg


    write fields extracted from state ID to current user dict

    Args:
    user_id(string): unique id for each user
    dict: a python dict of dict, key is user_id while value is all user info

    Returns:
    a python dict of dict, key is user_id while value is all user info

    1st precedence of extraction in the following: 
        Address, within US
    2nd precedence of extraction in the following:
        Surname
    3rd precedence of extraction in the following: 
        Given Name, DOB,
    '''
    cur_key, cur_val = key_val
    if cur_key == "FirstName":
        user_dict[user_id]["First_Name"] = str(cur_val)
    elif cur_key == "LastName":
        user_dict[user_id]["Last_Name"] = str(cur_val)
    elif cur_key == "DOB":
        user_dict[user_id]["DOB"] = str(cur_val)
    elif cur_key == "Address":
        user_dict[user_id]["Address_within_US"] = str(cur_val)
    elif cur_key == "Sex":
        user_dict["Gender"] = str(cur_val)
    
    return user_dict

    
# general document model
def analyze_general_documents(docUrl, docType = None, clientID = None):
    # sample document
    # docUrl = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-layout.pdf"

    # create your `DocumentAnalysisClient` instance and `AzureKeyCredential` variable
    document_analysis_client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
    result_dict = create_dict(clientID)
    poller = document_analysis_client.begin_analyze_document_from_url(
            "prebuilt-document", docUrl)
    result = poller.result()

    for style in result.styles:
        if style.is_handwritten:
            print("Document contains handwritten content: ")
            print(",".join([result.content[span.offset:span.offset + span.length] for span in style.spans]))

    # print("----Key-value pairs found in document----")
    for kv_pair in result.key_value_pairs:
        # Check if either the key or value is None before attempting to access .content
        if kv_pair.key and kv_pair.value and kv_pair.key.content and kv_pair.value.content:
            cur_pair = (kv_pair.key.content, kv_pair.value.content)
            # For debugging purpose print
            # print(cur_pair)
            if docType == "I94":
                result_dict = collect_info_I94(clientID, result_dict, cur_pair)
            elif docType == "non_immigrant_visa":
                result_dict = collect_info_non_immigrant_visa(clientID, result_dict, cur_pair)
        else:
            # Handle the case where either the key or value is None
            print("Found a key-value pair with NoneType, skipping this pair.")

        # add more cases for different document types below
            
        # Below code will print out each key value pair in a stylized way
        # if kv_pair.key:
        #     print(
        #             "Key '{}' found within '{}' bounding regions".format(
        #                 kv_pair.key.content,
        #                 format_bounding_region(kv_pair.key.bounding_regions),
        #             )
        #         )
        # if kv_pair.value:
        #     print(
        #             "Value '{}' found within '{}' bounding regions\n".format(
        #                 kv_pair.value.content,
        #                 format_bounding_region(kv_pair.value.bounding_regions),
        #             )
        #         )
    # for debugging purpose print

    # # Below code will print out OCR result line by line
    # for page in result.pages:
    #     print("----Analyzing document from page #{}----".format(page.page_number))
    #     print(
    #         "Page has width: {} and height: {}, measured with unit: {}".format(
    #             page.width, page.height, page.unit
    #         )
    #     )

    #     for line_idx, line in enumerate(page.lines):
    #         print(
    #             "...Line # {} has text content '{}' within bounding box '{}'".format(
    #                 line_idx,
    #                 line.content,
    #                 format_polygon(line.polygon),
    #             )
    #         )

    #     for word in page.words:
    #         print(
    #             "...Word '{}' has a confidence of {}".format(
    #                 word.content, word.confidence
    #             )
    #         )

    #     for selection_mark in page.selection_marks:
    #         print(
    #             "...Selection mark is '{}' within bounding box '{}' and has a confidence of {}".format(
    #                 selection_mark.state,
    #                 format_polygon(selection_mark.polygon),
    #                 selection_mark.confidence,
    #             )
    #         )

    # for table_idx, table in enumerate(result.tables):
    #     print(
    #         "Table # {} has {} rows and {} columns".format(
    #             table_idx, table.row_count, table.column_count
    #         )
    #     )
    #     for region in table.bounding_regions:
    #         print(
    #             "Table # {} location on page: {} is {}".format(
    #                 table_idx,
    #                 region.page_number,
    #                 format_polygon(region.polygon),
    #             )
    #         )
    #     for cell in table.cells:
    #         print(
    #             "...Cell[{}][{}] has content '{}'".format(
    #                 cell.row_index,
    #                 cell.column_index,
    #                 cell.content,
    #             )
    #         )
    #         for region in cell.bounding_regions:
    #             print(
    #                 "...content on page {} is within bounding box '{}'\n".format(
    #                     region.page_number,
    #                     format_polygon(region.polygon),
    #                 )
    #             )
    # print("----------------------------------------")
    return result_dict


# prebuilt model: ID documents
def analyze_identity_documents(identityUrl, docType = None, clientID = None):
# sample document
    #identityUrl = "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/rest-api/identity_documents.png"

    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    poller = document_analysis_client.begin_analyze_document_from_url(
            "prebuilt-idDocument", identityUrl
        )
    id_documents = poller.result()
    result_dict = create_dict(clientID)
    key_val = None

    for idx, id_document in enumerate(id_documents.documents):
        #print("--------Analyzing ID document #{}--------".format(idx + 1))
        first_name = id_document.fields.get("FirstName")
        if first_name:
            if docType == "passport":
                key_val = ("FirstName", first_name.value) 
                result_dict = collect_info_passport_front_page(clientID, result_dict, key_val)
            elif docType == "state_DL":
                key_val = ("FirstName", first_name.value)
                result_dict = collect_info_State_DL(clientID, result_dict, key_val)
            elif docType == "state_ID":
                key_val = ("FirstName", first_name.value)
                result_dict = collect_info_state_ID(clientID, result_dict, key_val)
            # print(
            #     "First Name: {} has confidence: {}".format(
            #         first_name.value, first_name.confidence
            #     )
            # )
        last_name = id_document.fields.get("LastName")
        if last_name:
            if docType == "passport":
                key_val = ("LastName", last_name.value)
                result_dict = collect_info_passport_front_page(clientID, result_dict, key_val)
            elif docType == "state_DL":
                key_val = ("LastName", last_name.value)
                result_dict = collect_info_State_DL(clientID, result_dict, key_val)
            elif docType == "state_ID":
                key_val = ("LastName", last_name.value)
                result_dict = collect_info_state_ID(clientID, result_dict, key_val)
            # print(
            #     "Last Name: {} has confidence: {}".format(
            #         last_name.value, last_name.confidence
            #     )
            # )
        document_number = id_document.fields.get("DocumentNumber")
        if document_number:
            if docType == "passport":
                key_val = ("DocumentNumber", document_number.value)
                result_dict = collect_info_passport_front_page(clientID, result_dict, key_val)
            # print(
            #     "Document Number: {} has confidence: {}".format(
            #         document_number.value, document_number.confidence
            #     )
            # )
        dob = id_document.fields.get("DateOfBirth")
        if dob:
            if docType == "passport":
                key_val = ("DateOfBirth", dob.value)
                result_dict = collect_info_passport_front_page(clientID, result_dict, key_val)
            elif docType == "state_DL":
                key_val = ("DateOfBirth", dob.value)
                result_dict = collect_info_State_DL(clientID, result_dict, key_val)
            elif docType == "state_ID":
                key_val = ("DateOfBirth", dob.value)
                result_dict = collect_info_state_ID(clientID, result_dict, key_val)
            # print(
            #     "Date of Birth: {} has confidence: {}".format(dob.value, dob.confidence)
            # )
        doe = id_document.fields.get("DateOfExpiration")
        if doe:
            pass
            # print(
            #     "Date of Expiration: {} has confidence: {}".format(
            #         doe.value, doe.confidence
            #     )
            # )
        sex = id_document.fields.get("Sex")
        if sex:
            if docType == "passport":
                key_val = ("Sex", sex.value)
                result_dict = collect_info_passport_front_page(clientID, result_dict, key_val)
            elif docType == "state_DL":
                key_val = ("Sex", sex.value)
                result_dict = collect_info_State_DL(clientID, result_dict, key_val)
            elif docType == "state_ID":
                key_val = ("Sex", sex.value)
                result_dict = collect_info_state_ID(clientID, result_dict, key_val)
            # print("Sex: {} has confidence: {}".format(sex.value, sex.confidence))
        address = id_document.fields.get("Address")
        if address:
            if docType == "state_DL":
                key_val = ("Address", address.value)
                result_dict = collect_info_State_DL(clientID, result_dict, key_val)
            elif docType == "state_ID":
                key_val = ("Address", address.value)
                result_dict = collect_info_state_ID(clientID, result_dict, key_val)
            # pass
            # print(
            #     "Address: {} has confidence: {}".format(
            #         address.value, address.confidence
            #     )
            # )
        country_region = id_document.fields.get("CountryRegion")
        if country_region:
            if docType == "passport":
                key_val = ("CountryRegion", country_region.value)
                result_dict = collect_info_passport_front_page(clientID, result_dict, key_val)
            # print(
            #     "Country/Region: {} has confidence: {}".format(
            #         country_region.value, country_region.confidence
            #     )
            # )
        region = id_document.fields.get("Region")
        if region:
            pass
            # print(
            #     "Region: {} has confidence: {}".format(region.value, region.confidence)
            # )

        # print("--------------------------------------")
    return result_dict

def generate_from_gpt(prompt, max_tokens, oai_key=OPENAI_API_KEY, temperature=0):
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

@app.route('/analyze_document', methods=['POST'])
def analyze_document():
    data = request.json
    url = data.get('url')
    file_type = data.get('file_type', None)
    user_id = data.get('id', None)

    # Decide which function to use based on file_type
    if file_type in ["passport", "state_DL", "state_ID"]:
        result_dict = analyze_identity_documents(url, file_type, user_id)

    # birth certificate
    elif file_type in ["non_immigrant_visa", "I94", "birth_certificate"]:
        result_dict = analyze_general_documents(url, file_type, user_id)
    else:
        return jsonify({"error": "Unsupported file type"}), 400

    return jsonify(result_dict)

@app.route('/gpt_analyze', methods=['POST'])
def gpt_analyze():
    data = request.json
    document_url = data.get('url')
    prompt = data.get('prompt', '')

    # Fetch the document from the URL
    response = requests.get(document_url)
    document_bytes = response.content

    # Analyze the document with Azure Form Recognizer
    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )
    poller = document_analysis_client.begin_analyze_document(
        "prebuilt-document", document_bytes
    )
    result = poller.result()

    # Extracted content from the document
    extracted_text = result.content

    # Concatenate prompt with the extracted content for GPT processing
    full_prompt = prompt + "\n" + extracted_text

    # Process with GPT (pseudo-code, adapt according to the actual GPT interaction code)
    gpt_response = generate_from_gpt(full_prompt, max_tokens=100)  # Adjust parameters as needed

    # Process the GPT response and return
    # Note: Error handling and GPT response parsing should be implemented here

    return jsonify(gpt_response)

if __name__ == "__main__":
    app.run(debug=True)
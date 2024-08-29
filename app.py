#!/opt/homebrew/bin/python3
import streamlit as st
import streamlit.components.v1 as components
import json
global wheel_h
wheel_h = 420
from pymongo import MongoClient
from bson.objectid import ObjectId
from PIL import Image, ImageDraw
import openai
import io
import os
import base64
import json
import boto3

bedrock_runtime = boto3.client('bedrock-runtime',
                               aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'),
                               aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'),
                               region_name="us-east-1")

if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

openai.api_key = os.getenv('OPENAI_API_KEY')

## Connect to MongoDB

client = MongoClient(os.environ.get('MONGODB_ATLAS_URI'))
db = client['spin_the_wheel']
participants = db['participants']
api_keys = db['api_keys']  # New collection for API keys

def check_access_key(input_key):
    # Check if the input key exists in the api_keys collection
    return api_keys.find_one({"api_key": input_key}) is not None

def generate_image_description_with_claude(image):
    claude_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "system": "Please trunscribe this image into a json only output for MongoDB store, calture all data as a single document. Always have a 'participant' : { 'first_name' : ..., last_name : ..., company : ...} It must be only in json format no other fields allowed. ",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image}}
                 
            ]
        }]
    })

    claude_response = bedrock_runtime.invoke_model(
        body=claude_body,
        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
        accept="application/json",
        contentType="application/json",
    )
    response_body = json.loads(claude_response.get("body").read())
    st.write("Vision model has processed the image of the participant.")
    # Assuming the response contains a field 'content' with the description
    return json.loads(response_body["content"][0]['text'])

def generate_image_description_with_gpt4o(image):
    try:
        print("calling openai")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Please transcribe this image into a json only output for MongoDB store, capture all data as a single document if you don't find the details return an empty document. If data located format the JSON  with 'participant' : { 'first_name' : ..., last_name : ..., company : ...}. It must be only in json format no other fields allowed, " },
                {
            "role": "user",
            "content": 
                [{
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image}"
                }}]
                }],
                response_format={"type" : "json_object"},
                temperature=0
        );
        print(response.choices[0].message.content)
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(e)

def transform_image_to_text(image, format, selected_llm):
    try:
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format=format)
        img_byte_arr = img_byte_arr.getvalue()
        encoded_image = base64.b64encode(img_byte_arr).decode('utf-8')
        st.write("Vision model is processing the image...")
        if selected_llm == "GPT-4o":
            response = generate_image_description_with_gpt4o(encoded_image)
        elif selected_llm == "Claude3":
            response = generate_image_description_with_claude(encoded_image)
        return response
    except Exception as e:
        st.error(f"Error: {e}")

def new_ruffle_id():
    ruffle_id =  ObjectId()
    st.session_state.ruffle_id = ruffle_id
    return ruffle_id

# Access key input
st.session_state.api_key = st.text_input("Enter access key", type="password")

if st.session_state.api_key and check_access_key(st.session_state.api_key):
    # Main application logic
    selected_llm = st.selectbox("Select LLM Model", ["GPT-4o", "Claude3"],index=0)

    col1 , col2 = st.columns([1,1])

    if not 'participants' in st.session_state:
        st.session_state.participants = []

    if not 'ruffle_id' in st.session_state:
        st.session_state.ruffle_id = new_ruffle_id()

    def register_to_mongodb(participant):
        st.write("Locating participant in MongoDB...")
        located_participant = participants.find_one({"participant.first_name": participant['participant']['first_name'], "participant.last_name": participant['participant']['last_name'], "participant.company": participant['participant']['company']})

        if located_participant is None:
            st.write("Participant not found, registering...")
            participant['registration_count'] = 1
            participant['ruffle_ids'] = [st.session_state.ruffle_id]
            participant['event'] = st.session_state.api_key
            participants.insert_one(participant)
        
        else:
            st.write("Participant found, updating registration count...")
            if located_participant['registration_count'] < 2 and st.session_state.ruffle_id not in located_participant['ruffle_ids']:
                participants.update_one({"_id": located_participant['_id']}, {"$inc": {"registration_count": 1}, "$push" : {"ruffle_ids": st.session_state.ruffle_id}})
            else:
                st.write("Participant already registered twice")
                st.error("Participant already registered twice")

    @st.experimental_dialog("Processed Document",width="large")
    def add_participant(participant, img):
        st.write(participant)
        if st.button("Confirm Save to MongoDB"):
            register_to_mongodb(participant)
            st.session_state.participants.append(f"{participant['participant']['first_name']} {participant['participant']['last_name']} - {participant['participant']['company']}")
            wheel_h = 420
            st.rerun()

    with col1:
        if st.button("Enable spin the wheel"):
            wheel_h = 500
            is_disabled = True
            
        components.iframe(f"https://pash10g.github.io/spin-the-wheel?participants={json.dumps(st.session_state.participants)}", height=wheel_h, scrolling=False)

    with col2:   
        st.header('Register participants')
        st.subheader("Take a picture as a participant, please hold your name badge in a visible location") 

        camera, manual_input = st.tabs(["Camera", "Manual Input"])
        with camera:
            image = st.camera_input("Take a picture")
            if image:
                img = Image.open(io.BytesIO(image.getvalue()))
            
            reg, clear = st.columns([1,1])
            with reg:
                if st.button("Register") and image:
                    with st.status("AI Analysis...", expanded=True) as status:
                        print('before transform ' + selected_llm)
                        participant = transform_image_to_text(img, img.format, selected_llm)
                        print(participant)
                        status.update(label="AI Vision complete!", state="complete", expanded=False)
                        if 'participant' not in participant:
                            st.error("Participant not found in the response")
                    
                    
                        if participant['participant']['first_name'] == "":
                            st.error("Participant first name not detected")
                        
                        if participant['participant']['last_name'] == "":
                            st.error("Participant last name not detected")
                        
                        if participant['participant']['company'] == "":
                            st.error("Participant company not detected")
                        add_participant(participant, img)
                else:
                    st.warning("Please take a picture first")
        with manual_input:
            reg_first_name = st.text_input('Enter participant first name')
            reg_last_name = st.text_input('Enter participant last name')
            reg_company = st.text_input('Enter participant company')

            if st.button("Add Manually") and reg_first_name and reg_last_name and reg_company:
                participant = {
                    "participant": {
                        "first_name": reg_first_name,
                        "last_name": reg_last_name,
                        "company": reg_company
                    }
                }
                add_participant(participant, None)
                
        with clear:
            if st.button("New ruffle"):
                st.session_state.participants = []
                st.session_state.ruffle_id = new_ruffle_id()
                image = None
                st.rerun()
                
        for participant in st.session_state.participants:
            st.markdown(f"- {participant}")
else:
    st.error("Invalid or missing access key. Please enter a valid access key to proceed.")

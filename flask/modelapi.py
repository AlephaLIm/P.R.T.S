import requests
import os
import shutil
import random, string
import json
import sseclient

def Uploader(video):
    files = {
        'file': open(video, 'rb'),
    }
    response = requests.post('https://tmpfiles.org/api/v1/upload', files=files)
    responseJson = response.json()
    if ("status" in responseJson.keys() and responseJson["status"] == "success"):
        url = responseJson["data"]['url']
        urlSplice = url.split("/")
        finalUrl = "https://tmpfiles.org/dl/" + urlSplice[-2] + "/" + urlSplice[-1]
        print(f'Temporary Store URL: {finalUrl}')
        return finalUrl
    else:
        print("Upload Failure, Exiting")
        exit()

def ModelRequester(url, videoname, userprompt):
    session_hash = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    requesting_object = {
        "data": [{
            "video": {
                "path": url,
                "meta": {
                    "_type": "gradio.FileData"
                    },
                "orig_name": videoname,
                "url": url
            },
            "subtitles": None
        },
        userprompt
        ],
        "event_data": None,
          "fn_index": 0,
          "trigger_id": 13,
          "session_hash": session_hash
    }

    headers = {'Content-Type': 'application/json',}
    response = requests.post('https://tonic-llava-video.hf.space/gradio_api/call/gradio_interface', headers=headers, json=requesting_object)
    responseJson = response.json()
    if ("event_id" in responseJson.keys()):
        print(f'event_id:{responseJson["event_id"]}')
        print(f'session_hash:{session_hash}')
    else:
        print("Model Query Failure")
        exit()
    return session_hash

def ModelResponder(session_hash):	
    params = {'session_hash': session_hash}
    request = requests.get('https://tonic-llava-video.hf.space/gradio_api/queue/data', params=params, stream=True)
    client = sseclient.SSEClient(request)
    for event in client.events():
        eventData = json.loads(event.data)
        if("success" in eventData):
            if(eventData["success"] == True):
                print(f'Output Prompt: {eventData["output"]["data"][0]}')
                return eventData["output"]["data"][0]
            elif(eventData["success"] == False):
                print(f'Output Prompt: {eventData}')
                return eventData

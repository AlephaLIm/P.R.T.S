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

'''
input_video = gr.Video(label="Upload Video for Processing", autoplay=True)
input_textbox = gr.Text(label="Input Prompt")
output_textbox = gr.Text(label="Generated Output")

def HandleInputs(uservideo, userprompt):
    path = "/home/ubuntu/temps/" + os.path.basename(uservideo)
    shutil.copyfile(uservideo, path)
    url = Uploader(path)
    session_hash = ModelRequester(url, os.path.basename(uservideo), userprompt)
    output = ModelResponder(session_hash)
    #output = json.loads("""{"msg":"process_completed","event_id":"43575b2e5a874e9d822f5af50852924c","output":{"data":["The video begins with a desktop screen showing a serene image of a wooden pier extending into a calm body of water under a dramatic sky filled with clouds. The desktop has several icons, including folders and applications, and the taskbar at the bottom shows the time as 12:03 PM on a Monday. The scene transitions to a web browser window where the user types 'eicar' into the address bar, leading to a Google search page displaying various links related to 'EICAR'. The user clicks on one of the links, which opens a webpage titled 'EICAR Anti-Malware Testfile' from eicar.org. The webpage explains that the EICAR Anti-Malware Testfile is a test file used by anti-virus software to evaluate their detection capabilities. The user then navigates to the 'Download Area' section of the website, which offers different versions of the test file for download. The user selects the 'EICAR COM' version and clicks the 'Download' button.\\n\\nThe video continues with the user downloading the 'EICAR COM' test file. The file is saved in the 'Downloads' folder on the desktop. A notification appears indicating that the download was successful. The user then opens the downloaded file, which opens a 'Symantec Protection Results' window displaying various categories such as 'Malware', 'Trojan', 'Spyware', 'Rootkit', 'Adware', and 'Logic', all marked as 'Clean'. The user clicks the 'Close' button on the 'Symantec Protection Results' window.\\n\\nThe final part of the video shows the 'Symantec Protection Results' window again, with the same categories marked as 'Clean'. The user clicks the 'Close' button once more, and the video concludes with the desktop screen showing the 'Downloads' folder containing the 'EICAR COM' file."],"is_generating":false,"duration":41.85723829269409,"average_duration":20.785076398494816,"render_config":null,"changed_state_ids":[]},"success":true,"title":null}""")
    return output

demo.launch(share=False, server_name="10.5.18.200", server_port=52300)
#Generate a detailed description of the video
'''
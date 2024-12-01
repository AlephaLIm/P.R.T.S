import splunklib.client as client
import splunklib.results as results
import json
from modelapi import ModelResponder, ModelRequester

applications = ["chrome", "firefox", "outlook", "word", "powerpoint", "edge", "excel"]

def generate_splunk_query(url,videoname):
    
    try:
        identifyApplicationPrompt = "List all the software and programs that were open in the screen recording. format ym•r response so that it onty shows 1 software or program per line"
        applicationSessionHash = ModelRequester(url, videoname, identifyApplicationPrompt)
        applicationTranscript = ModelResponder(applicationSessionHash)
        softwareUsed = [app for app in applications if app.lower() in applicationTranscript.lower()]
    
        transcriptPrompt = "Generate a detailed transcript of the video"
        descriptionSessionHash=ModelRequester(url, videoname, transcriptPrompt)
        descriptionTranscript=ModelResponder(descriptionSessionHash)

        if len(softwareUsed) != 0:
            splunk_query = f"search index=* "
            for app in softwareUsed:
                splunk_query += f"Process_Name=*{app}.exe OR "
            splunk_query += "head 50"

            return splunk_query, descriptionTranscript
        else:
            return "", descriptionTranscript
    except json.JSONDecodeError:
        print("Invalid JSON input. Please provide a valid JSON object.")
        return None     

def splunk_connection(URL, videoname):
    try:
        # Connect to Splunk
        service2 = client.connect(
            host='10.5.18.200',  
            port=8089,                     
            username = "admin",
            password = "P@ssw0rd"       
        )
        
        query,transcript = generate_splunk_query(URL,videoname)
        job = service2.jobs.create(query)

        # Wait for the job to complete
        while not job.is_done():
            pass

        print("Connection successful! Retrieved results from '_internal':")
        all_results = list(results.ResultsReader(job.results()))
        output_data = {}
        if len(all_results) == 0:
            print("no output")
            return None
        else:
            for i, result in enumerate(all_results, start=1):
                output_data[f"Object {i}"] = result  
            #output_data["Summary"] = {"Total Objects": len(list(all_results))}               
            json_data = json.dumps(output_data,indent=4)
            return transcript,json_data
    except Exception as e:
        print(f"Failed to connect to Splunk: {e}")
        return None
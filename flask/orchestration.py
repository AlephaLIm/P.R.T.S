import splunklib.client as client
import splunklib.results as results
import json
from modelapi import ModelResponder, ModelRequester

def generate_splunk_query(URL,videoname):
    
    try:
        userprompt = "identify the application ran in this video and generate aa detailed description of the video"
        applications = ["google","whatsapp","gmail","firefox"]
        session_hash=ModelRequester(url, videoname, userprompt)
        transcript=ModelResponder(session_hash)
        software_used=[app for app in applications if app.lower() in transcript.lower()]
        # Map options to their respective Splunk queries
        splunk_queries = f"search {software_used} | head 50"

        # Generate the Splunk query based on the option
        if input_json in splunk_queries:
            query = splunk_queries[input_json]
            print(f"Generated Splunk Query: {query}")
            return query,transcript
        else:
            print("Invalid option. Please choose a valid application.")
            return None
    except json.JSONDecodeError:
        print("Invalid JSON input. Please provide a valid JSON object.")
        return None     

def splunk_connection():
    try:
        
        # Connect to Splunk
        service = client.connect(
            host='10.5.18.200',  
            port=8089,                     
            username = "admin",
            password = "P@ssw0rd"       
        )
        
        query,transcript = generate_splunk_query(URL,videoname)
        job = service.jobs.create(query)

        # Wait for the job to complete
        while not job.is_done():
            pass

        print("Connection successful! Retrieved results from '_internal':")
        all_results = list(results.ResultsReader(job.results()))
        output_data = {}
        if len(all_results) == 0:
            print("no output")
        else:
            for i, result in enumerate(all_results, start=1):
                output_data[f"Object {i}"] = result  
            #output_data["Summary"] = {"Total Objects": len(list(all_results))}               
            json_data = json.dumps(output_data,indent=4)
            return transcript,json_data
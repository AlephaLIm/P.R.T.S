# Hoshimachi-Case-Files
An automated triaging system with the aid of LLM video processing for fast and efficient triaging

# Usage instructions
System Requirements:
Python 3.12.6 or later
Python venv
MySQL Server 8.0 or later

Setup Requirements;
With the flask server directory, insert a pyvenv.cfg in the base directory. 
In the pyvenv.cfg file, include these base parameters in the file:
```.cfg
home = <path to directory of python executable>
include-system-site-packages = false
version = <python version>
executable = <path of python executable>
command = <path of python executable> -m venv <path to flask directory>
```
Add a .env file outside of the flask directory, and include these parameters:
```.env
DB_USER=<username of database user>
DB_PASSWORD=<password to authenticate user>
DB_NAME=<database schema to connect to>
UPLOAD_DIR=<specified upload directory, will be created if it does not exist>
CONFIG=<configuration directory to retrieve configurations from, default should be ./config>
SPLUNK_HOST=<IP of Splunk instance>
SPLUNK_PORT=<Splunk API Port, default should be 8089>
SPLUNK_USR=<username of splunk account to use>
SPLUNK_PASS=<password of splunk user>
```
On Linux, install redis on the system and ensure the service is running.
See https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/install-redis-on-linux/ for more information.

On Windows, set up either a Linux VM or use WSL to install the redis server required for the flask application.
See https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/install-redis-on-windows/ for more information.

To change the model api used for the video processing, modify the code blocks for the Uploader() function, ModelRequester() function, and the ModelResponder() function. 

# Running the Server
Ensure redis server is running and can be accessed via localhost, otherwise modify the redis configurations in app.py for both celery and redis. 
See https://redis-py2.readthedocs.io/en/latest/#strictredis (Redis) and 
https://docs.celeryq.dev/en/stable/getting-started/introduction.html (Celery) for more information.

Install required packages
```cmd
pip install -r requirements.txt
```

In one terminal at the flask base directory, run the following:

Windows:
```cmd
celery -A app.celery_app worker --pool=solo --loglevel INFO
```
Linux:
```cmd
celery -A app.celery_app worker --loglevel INFO
```

Then, in a separate terminal, run the app:
```cmd
python app.py
```

# P.R.T.S User Manual

This README serves as a user manual for P.R.T.S, which will explain how to set up and configre each component.


# Agent

The Agent is responsible for handling event monitoring and screen recording, and thereafter sending the relevant files to the Control Server. It has been tested to work on Windows 10 and Windows 11. There is no support for other operating systems.

## Install FFmpeg

FFmpeg is required for the Agent to function, and needs to be installed and accessible from PATH. FFmpeg can be downloaded from https://www.ffmpeg.org/download.html
## Enabling Event Subscriptions

The Windows Event Collector service must be running for Event Subscriptions to work. It can be enabled by either going into Event Viewer and clicking on Subscriptions, and then clicking yes on the dialog that appears. 

Alternatively, it can be enabled using GPO or Powershell.
>wecutil qc

##  Compiling Agent from source code

Navigate to the agent directory in the P.R.T.S repository. From there, use the following command to compile the code.
> cd agent

>cl /EHsc /std:c++17 /I"include" /Fo"bin\\" /Fe"bin\\agent.exe" main.cpp Logger.cpp HttpClient.cpp Configuration.cpp VideoRecorder.cpp EventMonitor.cpp pugixml.cpp /link wevtapi.lib user32.lib winhttp.lib

After compiling the code, you should see the compiled executable in the *bin* directory
## Running the Agent

The Agent can be ran using the following command
>agent.exe [host] [port]

Host and Port should reflect where the API Endpoints of the Control Server


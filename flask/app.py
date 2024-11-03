import os
from flask import Flask, request, render_template, json
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = './uploads'

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/agent_trigger", methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 
        
        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], name=filename))
        response = app.response_class(
            status=200,
            mimetype='application/json'
        )
        return response
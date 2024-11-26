import os
import uuid
import datetime
import redis
import time
import json
import random
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, ForeignKey, select, update, JSON, nulls_first
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, create_engine
from werkzeug.utils import secure_filename

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
load_dotenv()

app = Flask(__name__)
red = redis.StrictRedis()

app.config['UPLOAD_FOLDER'] = './uploads'
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{db_user}:{db_password}@localhost/{db_name}"

db.init_app(app)

class Client(db.Model):
    __tablename__ = "client"
    guid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(64))
    ip_addr: Mapped[Optional[str]] = mapped_column(String(15))
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    date_registered: Mapped[datetime.datetime] = mapped_column(nullable=False)
    last_modified: Mapped[datetime.datetime] = mapped_column(nullable=False)
    
class Cases(db.Model):
    __tablename__ = "cases"
    case_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    case_num: Mapped[int] = mapped_column(unique=True)
    client: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.guid"))
    json_log: Mapped[JSON] = mapped_column(JSON, nullable=False)
    transcript: Mapped[str] = mapped_column(String(255), nullable=True)
    video_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=False)
    datetime_created: Mapped[datetime.datetime] = mapped_column(nullable=False)
    datetime_resolved: Mapped[datetime.datetime] = mapped_column(nullable=True)

with app.app_context():
    db.create_all()

engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@localhost/{db_name}")
with engine.connect() as connection:
    result = connection.execute(text('select extra FROM information_schema.columns where table_name = "cases" and column_name = "case_num"')).scalar_one()
    if result == '':
        connection.execute(text('ALTER TABLE cases MODIFY case_num INTEGER UNIQUE AUTO_INCREMENT'))

def logdata_stream():
    logdata_channel = red.pubsub(ignore_subscribe_messages=True)
    logdata_channel.subscribe('logstream')
    while True:
        logtype = []
        for i in range(3):
            logtype.append(random.randint(2000, 20000))
        red.publish('logstream', json.dumps({"data":f"{random.randint(0,100)}", "logtype":logtype}))
        message = logdata_channel.get_message()
        if message:
            msg = dict(message)
            yield f'data:{msg.get('data')}\n\n'
        time.sleep(3)

def get_listresponse():
    channel = red.pubsub(ignore_subscribe_messages=True)
    channel.subscribe('case_client')
    while True:
        message = channel.get_message()
        if message:
            msg = dict(message)
            yield f'data:{msg.get('data')}\n\n'
        time.sleep(0.01)

def generate_list():
    with app.app_context():
        cases = db.session.execute(select(Cases).order_by(Cases.datetime_created.desc(), Cases.datetime_resolved.desc())).fetchmany(10)
        clients = db.session.execute(select(Client).order_by(Client.status.asc(), Client.last_modified.desc())).fetchmany(10)
    case_data = []
    client_data = []
    if cases is not None:
        for case in cases:
            if case[0].datetime_resolved is None:
                resolved = 'None'
            else:
                resolved = case[0].datetime_resolved.strftime(r"%d-%m-%Y %H:%M:%S")
            case_data.append({"casenum":case[0].case_num,"cid":str(case[0].case_id),"guid":str(case[0].client),"created":case[0].datetime_created.strftime(r"%d-%m-%Y %H:%M:%S"), "resolved":resolved})
    else:
        case_data.append('null')
    if clients is not None:
        for client in clients:
            client_data.append({"guid":str(client[0].guid),"hostname":client[0].hostname,"ip":client[0].ip_addr,"registered":client[0].date_registered.strftime(r"%d-%m-%Y %H:%M:%S"),"last_m":client[0].last_modified.strftime(r"%d-%m-%Y %H:%M:%S"),"status":client[0].status})
    else:
        client_data.append('null')
    return case_data, client_data

def publish_newlist():
    case_data, client_data = generate_list()
    time.sleep(0.5)
    red.publish('case_client', json.dumps({"cases":case_data, "clients":client_data}))

@app.route("/")
def homepage():
    return render_template('homepage.html',
                           title="Home",
                           page_css='css/homepage.css')

@app.route("/search", methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        return render_template('search.html',
                               title="Search Cases & Clients",
                               page_css='css/search.css')
    elif request.method == 'POST':
        return f"{request.form.get('field')}, {request.form.get('search')}, {request.form}"
    
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        new_guid = uuid.uuid4()
        with app.app_context():
            while db.session.execute(select(Client.guid).where(Client.guid == new_guid)).one_or_none() is not None:
                new_guid = uuid.uuid4()
                print(new_guid)
        return jsonify(guid = new_guid)
    
    elif request.method == 'POST':
        req_data = request.get_json()
        if ('guid' in req_data) and ('hostname' in req_data) and ('ip_addr' in req_data):
            guid = uuid.UUID(req_data['guid'])
            hostname = req_data['hostname']
            ip_addr = req_data['ip_addr']
            date = datetime.datetime.now()
            new_client = Client(guid=guid, hostname=hostname, ip_addr=ip_addr, status='Healthy', date_registered=date, last_modified=date)
            if db.session.execute(select(Client.guid).where(Client.guid == guid)).one_or_none() is not None:
                return "GUID already exists", 412
            with app.app_context():
                db.session.add(new_client)
                db.session.commit()
            publish_newlist()
            return "Success", 201
        else:
            return "Missing Fields", 400

@app.route("/update", methods=['POST'])
def update_details():
    if request.method == 'POST':
        req_data = request.get_json()
        if 'guid' in req_data:
            with app.app_context():
                client = db.session.execute(select(Client.guid).where(Client.guid == uuid.UUID(req_data['guid']))).one_or_none()
                if client is None:
                    return "Client does not exist", 404
                else:
                    if 'hostname' in req_data:
                        db.session.execute(update(Client),[{"guid":uuid.UUID(req_data['guid']),"hostname":req_data["hostname"]}])
                    if 'ip_addr' in req_data:
                        db.session.execute(update(Client),[{"guid":uuid.UUID(req_data['guid']),"ip_addr":req_data["ip_addr"]}])
                    db.session.execute(update(Client),[{"guid":uuid.UUID(req_data['guid']),"last_modified":datetime.datetime.now()}])
                    db.session.commit()
            publish_newlist()
            return "Success", 200
        else:
            return "No GUID provided", 400

@app.route("/agent_trigger", methods=['POST'])
def upload_file():
    if request.method == 'POST':
        if 'guid' not in request.args:
            return "Invalid request", 400
        elif 'file' not in request.files:
            return "No files provided", 400
        elif 'json' not in request.files:
            return "No json body provided", 400
        client_id = request.args.get('guid')
        post_json = json.load(request.files['json'])
        post_file = request.files['file']
        filename = secure_filename(post_file.filename)
        post_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        with app.app_context():
            client = db.session.execute(select(Client.guid).where(Client.guid == uuid.UUID(client_id))).one_or_none()
            if client is None:
                return "Client does not exist", 404
            new_cuid = uuid.uuid4()
            datetime_now=datetime.datetime.now()
            new_case = Cases(case_id=new_cuid, client=uuid.UUID(client_id), json_log=post_json, video_file=os.path.join(app.config['UPLOAD_FOLDER'], filename), datetime_created=datetime_now)
            db.session.add(new_case)
            db.session.execute(update(Client),[{"guid":uuid.UUID(client_id),"status":"Affected"}])
            db.session.commit()
        publish_newlist()
        return "Success", 200

@app.route("/datastream")
def datastream():
    return Response(logdata_stream(), mimetype="text/event-stream")

@app.route("/casestream")
def casestream():
    return Response(get_listresponse(), mimetype="text/event-stream")

@app.route("/initialize")
def initialize():
    publish_newlist()
    return "Success", 200

if __name__ == '__main__':
    app.debug = True
    app.run(threaded=True)
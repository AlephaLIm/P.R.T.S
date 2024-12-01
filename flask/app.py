import os
import uuid
import datetime
import redis
import time
import json
import random
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify, url_for, Response, send_file
from celery import shared_task
from celery.result import AsyncResult
from celery_conf import celery_init
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, ForeignKey, select, update, JSON, Text, cast
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, create_engine
from werkzeug.utils import secure_filename
from modelapi import Uploader
from orchestration import splunk_connection
import splunklib.client as client
import splunklib.results as results
class Base(DeclarativeBase):
    pass
db = SQLAlchemy(model_class=Base)
load_dotenv()

app = Flask(__name__)
red = redis.StrictRedis()

if not os.path.isdir(os.environ['UPLOAD_DIR']):
    os.makedirs(os.environ['UPLOAD_DIR'])

app.config['UPLOAD_FOLDER'] = os.environ['UPLOAD_DIR']
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
config_folder = os.environ['CONFIG']
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{db_user}:{db_password}@localhost/{db_name}"

db.init_app(app)

app.config.from_mapping(
    CELERY=dict(
        broker_url="redis://localhost",
        result_backend="redis://localhost",
        task_ignore_result=True
    ),
)

celery_app = celery_init(app)

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
    transcript: Mapped[Text] = mapped_column(Text, nullable=True)
    parsed_res: Mapped[JSON] = mapped_column(JSON, nullable=True)
    video_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=False)
    analysis_process: Mapped[str] = mapped_column(String(100), nullable=True)
    datetime_created: Mapped[datetime.datetime] = mapped_column(nullable=False)
    datetime_resolved: Mapped[datetime.datetime] = mapped_column(nullable=True)

with app.app_context():
    db.create_all()

engine = create_engine(f"mysql+pymysql://{db_user}:{db_password}@localhost/{db_name}")
with engine.connect() as connection:
    result = connection.execute(text('select extra FROM information_schema.columns where table_name = "cases" and column_name = "case_num"')).scalar_one()
    if result == '':
        connection.execute(text('ALTER TABLE cases MODIFY case_num INTEGER UNIQUE AUTO_INCREMENT'))

service = client.connect(
    host=os.environ['SPLUNK_HOST'],
    port=os.environ['SPLUNK_PORT'],
    username=os.environ['SPLUNK_USR'],
    password=os.environ['SPLUNK_PASS']
)
savedsearches = service.saved_searches
for savedsearch in savedsearches:
    if savedsearch.name == 'logstream':
        savedsearches.delete('logstream')
query = savedsearches.create('logstream', 'index=* | stats count by sourcetype | eventstats sum(count) as totalcount | eval percentage=(count/totalcount)')
kwargs = {"is_scheduled": True, "cron_schedule": "* * * * *", "dispatch.status_buckets": "0", "dispatch.earliest_time":"-1m@m","dispatch.latest_time":"now", "dispatch.ttl":"30"}
query.update(**kwargs).refresh()

def logdata_stream(query):
    logdata_channel = red.pubsub(ignore_subscribe_messages=True)
    logdata_channel.subscribe('logstream')
    initial_time = 1
    while True:
        history = query.history()
        logtype = []
        data_percentage = []
        if len(history) > 0:
            for type in list(results.JSONResultsReader(history[0].results(output_mode="json"))):
                logtype.append(type.get('sourcetype'))
                data_percentage.append(type.get('percentage'))
                total_count = type.get('totalcount')
        red.publish('logstream', json.dumps({"data":total_count, "logtype":logtype, "dataset":data_percentage}))
        message = logdata_channel.get_message()
        if message:
            msg = dict(message)
            yield f'data:{msg.get('data')}\n\n'
        time.sleep(initial_time)
        initial_time = 60

def get_listresponse():
    channel = red.pubsub(ignore_subscribe_messages=True)
    channel.subscribe('case_client')
    while True:
        message = channel.get_message()
        if message:
            msg = dict(message)
            yield f'data:{msg.get('data')}\n\n'
        time.sleep(0.01)

def get_processed_data(cid):
    d_channel = red.pubsub(ignore_subscribe_messages=True)
    d_channel.subscribe(cid)
    while True:
        message = d_channel.get_message()
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

def load_config():
    config_file = 'default/default.json'
    with os.scandir(config_folder) as entries:
        for entry in entries:
            if entry.is_file() and entry.name.endswith('.json'):
                config_file = entry.name
    with open(os.path.join(config_folder, config_file), 'r') as file:
        data = json.load(file)
    return data

def publish_newlist():
    case_data, client_data = generate_list()
    time.sleep(0.7)
    red.publish('case_client', json.dumps({"cases":case_data, "clients":client_data}))

@shared_task(ignore_result=False)
def process_data(filepath, cid) -> str:
    print(filepath)
    #model_url = Uploader(filepath)
    result_tup = splunk_connection('yes', os.path.basename(filepath))
    if result_tup is not None:
        transcript = result_tup[0]
        json_data = json.loads(result_tup[1])
        print(type(json_data))
    db.session.execute(update(Cases), [{"case_id":uuid.UUID(cid),"transcript":transcript,"parsed_res":json_data}])
    db.session.commit()
    return 'COMPLETED'

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
        fields = {"Case ID":"case_id", "Case No.":"case_num", "Client ID":"client", "System ID":"guid", "Hostname":"hostname", "IP Address":"ip_addr", "Status":"status"}
        time_fields = {"Created":"datetime_created", "Resolved":"datetime_resolved", "Register":"date_registered", "Modified":"last_modified"}
        table = request.form.get('type')
        restrict_by_time = True
        secondary_info = False
        statement = f' from {db_name}.{table}'
        if 'guid' in request.form.keys():
            table_map = {'cases':'client', 'client':'guid'}
            table_field = table_map.get(table)
            statement += f' where {table_field} = :term '
            restrict_by_time = False
            secondary_info = True
        elif request.form.get('search') != '' and (request.form.get('field') in fields.keys()):
            statement += f' where {fields[request.form.get("field")]} like :term and'
        if request.form.get("timefield") in time_fields and restrict_by_time:
            if 'where' not in statement:
                statement += ' where'
            if request.form.get('start-time') == '' or request.form.get('end-time') == '':
                statement += f' {time_fields[request.form.get("timefield")]} is null'
            else:
                statement += f' {time_fields[request.form.get("timefield")]} between :start and :end'
        if table == 'cases':
            statement = 'select *, cast(datetime_created as char) as datetime_created, cast(datetime_resolved as char) as datetime_resolved' + statement
            query = text(statement + ' order by datetime_resolved is null, datetime_created desc, datetime_resolved desc')
        else:
            statement = 'select *, cast(date_registered as char) as date_registered, cast(last_modified as char) as last_modified' + statement
            query = text(statement + ' order by status asc, last_modified desc')
        with app.app_context():
            if secondary_info:
                sanitized = request.form.get('guid')
                result = db.session.execute(query, {'term': sanitized})
                sec_data = []
                for row in result:
                    sec_data.append(row._asdict())
                response = json.dumps({'field': request.form.get('type'),'sec_data': sec_data})
            else:    
                sanitized = '%' + request.form.get('search') + '%'
                if request.form.get('field') in ["Case ID", "System ID", "Client ID"]:
                    sanitized = sanitized.replace('-', '')
                result = db.session.execute(query, {'term': sanitized, 'start': request.form.get('start-time'), 'end': request.form.get('end-time')})
                primary_data = []
                for row in result:
                    primary_data.append(row._asdict())
                response = json.dumps({'field': request.form.get('type'),'pri_data': primary_data})
        return response

@app.route("/case/<cid>", methods=['GET', 'POST'])
def case(cid):
    if request.method == 'GET':
        with app.app_context():
            caseitem = db.session.execute(select(Cases).where(Cases.case_id == uuid.UUID(cid))).one_or_none()
            if caseitem is not None:
                dl_path = '/download/' + cid
                filename = os.path.basename(caseitem[0].video_file)
                caseobj = caseitem[0]
                if caseobj.datetime_resolved is None:
                    res = "No"
                else:
                    res = "Yes"
                clientitem = db.session.execute(select(Client).where(Client.guid == caseobj.client)).one_or_none()
                if clientitem is not None:
                    client = clientitem[0]
                if caseobj.transcript != '':
                    transcript = caseobj.transcript
                    logs = caseobj.parsed_res
        return render_template('case.html',
                            title='Case Details',
                            page_css='css/case.css',
                            case=caseobj,
                            client=client,
                            resolved=res,
                            dl_path = dl_path,
                            filename=filename,
                            transcript=transcript,
                            logs=logs)
    
    elif request.method == 'POST':
        req_data = request.get_json()
        if req_data.get('action') == 'resolve':
            with app.app_context():
                db.session.execute(update(Cases),[{"case_id": uuid.UUID(cid), "datetime_resolved": datetime.datetime.now()}])
                client_id = db.session.execute(select(Cases.client).where(Cases.case_id == uuid.UUID(cid))).scalar_one()
                db.session.execute(update(Client), [{"guid":client_id, "status": "Healthy"}])
                db.session.commit()
        elif req_data.get('action') == 'open':
            with app.app_context():
                db.session.execute(update(Cases),[{"case_id": uuid.UUID(cid), "datetime_resolved": None}])
                client_id = db.session.execute(select(Cases.client).where(Cases.case_id == uuid.UUID(cid))).scalar_one()
                db.session.execute(update(Client), [{"guid":client_id, "status": "Affected"}])
                db.session.commit()
        with app.app_context():
            resolved_dt = db.session.execute(select(cast(Cases.datetime_resolved, String())).where(Cases.case_id == uuid.UUID(cid))).scalar_one()
        if resolved_dt is None:
            new_datetime = 'None'
        else:
            new_datetime = resolved_dt
        return json.dumps({"resolved":new_datetime})

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
            config = load_config()
            config['identity']['guid'] = str(guid)
            return json.dumps(config), 200
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
            config = load_config()
            config['identity']['guid'] = str(uuid.UUID(req_data['guid']))
            return json.dumps(config), 200
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
        result = process_data.delay(os.path.join(app.config['UPLOAD_FOLDER'], filename), str(new_cuid))
        with app.app_context():
            db.session.execute(update(Cases),[{"case_id":new_cuid,"analysis_process":result.id}])
            db.session.commit()
        return "Success", 200

@app.route("/download/<cid>", methods=['GET', 'POST'])
def download(cid):
    with app.app_context():
        result = db.session.execute(select(Cases.video_file).where(Cases.case_id == uuid.UUID(cid))).scalar_one()
    return send_file(result,
                     as_attachment=True,
                     download_name=os.path.basename(result),
                     mimetype='application/octect')

@app.route("/datastream")
def datastream():
    return Response(logdata_stream(query), mimetype="text/event-stream")

@app.route("/casestream")
def casestream():
    return Response(get_listresponse(), mimetype="text/event-stream")

@app.route("/initialize")
def initialize():
    publish_newlist()
    return "Success", 200

@app.route("/get_chartdata/<cid>")
def get_chartdata(cid):
    with app.app_context():
        state_id = db.session.execute(select(Cases.analysis_process).where(Cases.case_id == uuid.UUID(cid))).scalar_one()
        transcript_loaded = db.session.execute(select(Cases.transcript).where(Cases.case_id == uuid.UUID(cid))).scalar_one()
        status = AsyncResult(state_id)
    while True:
        if status.ready() or transcript_loaded is not None:
            with app.app_context():
                json_data = db.session.execute(select(Cases.parsed_res).where(Cases.case_id == uuid.UUID(cid))).scalar_one()
                result_pack = db.session.execute(select(Cases.transcript, Cases.parsed_res).where(Cases.case_id == uuid.UUID(cid))).one_or_none()
            chartdata = {}
            for data in json_data.values():
                if data.get('source') not in chartdata.keys():
                    chartdata[data.get('source')] = 1
                else:
                    chartdata[data.get('source')] += 1
            red.publish(cid, json.dumps({"transcript":result_pack[0],"json_data":result_pack[1]}))
            return json.dumps(chartdata)
        time.sleep(0.01)
        

@app.route("/check_status/<cid>")
def check_status(cid):
    return Response(get_processed_data(cid), mimetype="text/event-stream")

if __name__ == '__main__':
    app.debug = True
    app.run(threaded=True)
import os
import uuid
import datetime
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, ForeignKey, select, update
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.utils import secure_filename

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
load_dotenv()

app = Flask(__name__)

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
    date_registered: Mapped[datetime.datetime] = mapped_column(nullable=False)
    last_modified: Mapped[datetime.datetime] = mapped_column(nullable=False)
    
class Case_details(db.Model):
    __tablename__ = "case_details"
    cuid: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    case_num: Mapped[int] = mapped_column(ForeignKey("cases.case_num"))
    filename: Mapped[str] = mapped_column(String(128), nullable=False)
    risk: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    risk_type: Mapped[str] = mapped_column(String(64), nullable=False)
    logged_by: Mapped[str] = mapped_column(String(64), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    computer: Mapped[str] = mapped_column(String(64), nullable=False)
    user: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    current_loc: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_action: Mapped[str] = mapped_column(String(128), nullable=False)
    secondary_action: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    video_file: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    datetime_occured: Mapped[datetime.datetime] = mapped_column(nullable=False)

class Cases(db.Model):
    __tablename__ = "cases"
    case_num: Mapped[int] = mapped_column(primary_key=True)
    client: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.guid"))
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("case_details.cuid"))
    datetime_created: Mapped[datetime.datetime] = mapped_column(nullable=False)

with app.app_context():
    db.create_all()

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

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
            new_client = Client(guid=guid, hostname=hostname, ip_addr=ip_addr, date_registered=date, last_modified=date)
            if db.session.execute(select(Client.guid).where(Client.guid == guid)).one_or_none() is not None:
                return "GUID already exists", 412
            with app.app_context():
                db.session.add(new_client)
                db.session.commit()
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
            return "Success", 200
        else:
            return "No GUID provided", 400

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
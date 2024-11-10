import os
import uuid
import datetime
from typing import Optional
from dotenv import load_dotenv
from flask import Flask, request, render_template, json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, ForeignKey
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
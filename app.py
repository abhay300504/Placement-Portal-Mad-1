from flask import Flask
from backend.models import db
app = None   # initially app variable is None

def initial_Setup():
    app = Flask(__name__)     # in app variable we have create a flask instance means create a flask object
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///placement_portal.db.sqlite3"  # set the database URI for SQLAlchemy
    db.init_app(app)  # initialize the SQLAlchemy object with the Flask app
    app.app_context().push() # push the application context to make the app context available for database operations
    return

initial_Setup()

from backend.routes import *

if __name__=="__main__":
    app.run(debug=True)
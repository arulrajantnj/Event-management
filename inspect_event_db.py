from sqlalchemy import inspect

from app import app
from models import db


with app.app_context():
    inspector = inspect(db.engine)
    print("database uri", app.config["SQLALCHEMY_DATABASE_URI"])
    print("tables", inspector.get_table_names())

    if inspector.has_table("participants"):
        columns = inspector.get_columns("participants")
        print("participants columns", [column["name"] for column in columns])

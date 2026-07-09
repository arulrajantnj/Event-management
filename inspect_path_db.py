from app import app


print("instance_path", app.instance_path)
print("database uri", app.config["SQLALCHEMY_DATABASE_URI"])

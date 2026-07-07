from flask import Flask
import os
import sqlite3

app = Flask(__name__)
print('instance_path', app.instance_path)
print('instance_exists', os.path.exists(app.instance_path))
print('cwd', os.getcwd())
print('path abs', os.path.abspath('instance/event.db'))
try:
    conn = sqlite3.connect('instance/event.db')
    conn.close()
    print('sqlite connect OK relative')
except Exception as e:
    print('sqlite relative error', e)
try:
    conn = sqlite3.connect(os.path.join(app.instance_path, 'event.db'))
    conn.close()
    print('sqlite connect OK absolute')
except Exception as e:
    print('sqlite abs error', e)

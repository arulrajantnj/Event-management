import os
import sqlite3

root = os.getcwd()
print('cwd', root)
for p in ['event.db', os.path.join('instance', 'event.db')]:
    print('path', p, 'exists', os.path.exists(p), 'abs', os.path.abspath(p))
    if os.path.exists(p):
        conn = sqlite3.connect(p)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print('tables', cur.fetchall())
        cur.execute("PRAGMA table_info(participants)")
        print('participants columns', [row[1] for row in cur.fetchall()])
        conn.close()

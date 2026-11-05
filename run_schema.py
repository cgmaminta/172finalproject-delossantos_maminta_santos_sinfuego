from apps import dbconnect as db

con = db.getdblocation()
con.autocommit = True
cur = con.cursor()

with open('new.sql', encoding='utf-8') as f:
    cur.execute(f.read())

cur.close()
con.close()
print('Schema created.')
from apps import dbconnect as db

db.modifyDB("INSERT INTO users (user_name, user_password) VALUES (%s, %s)", ['zz_test', 'x'])

df = db.getDataFromDB(
    "SELECT user_id, user_name FROM users",
    [],
    ['userid', 'username'],
)
print(df)
from flask import Flask, render_template, request, redirect, url_for, session
from hashlib import sha256
import mysql.connector
from mysql.connector import errorcode
from flask_bootstrap import Bootstrap

app = Flask(__name__)
bootstrap = Bootstrap(app)

Flask.secret_key = '1dkm4n'

class MyDatabase:
    def __init__(self, host, user, password = None, database = None):
        self.host = (host if host != None else 'localhost')
        self.user = (user if user != None else 'root')
        self.connect_type = 1
        
        if password != None:
            self.password = password
            self.connect_type = 2
        
        if database != None:
            self.database = database
            self.connect_type = 3
        
        if (password != None) and (database != None):
            self.connect_type = 4
        
    
    def connect(self, connect_type = 0):
        self.connect_type = (connect_type if connect_type != 0 else self.connect_type)
        match self.connect_type:
            case 1:
                db = mysql.connector.connect(
                    host = self.host,
                    user = self.user
                )

            case 2:
                db = mysql.connector.connect(
                    host = self.host,
                    user = self.user,
                    password = self.password
                )

            case 3:
                db = mysql.connector.connect(
                    host = self.host,
                    user = self.user,
                    database = self.database
                )
            case 4:
                db = mysql.connector.connect(
                    host = self.host,
                    user = self.user,
                    password = self.password,
                    database = self.database
                )
            case _:
                db = mysql.connector.connect()
            
        db_cur = db.cursor(buffered=True)
        
        return db, db_cur

db = MyDatabase(
    host='localhost',
    user='root',
    database='site_users'
)

try:
    mydb, mycur = db.connect()
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_BAD_DB_ERROR:
        print("WARNING: Database not found on localhost. Creating a new one...")

        mydb, mycur = db.connect(1)

        mycur.execute("CREATE DATABASE site_users")
        mycur.execute("USE site_users")
        mycur.execute(
            "CREATE TABLE `user_data` ("
            " `id` INT(11) NOT NULL AUTO_INCREMENT,"
            " `fname` VARCHAR(255) NOT NULL,"
            " `mname` VARCHAR(255) NOT NULL,"
            " `lname` VARCHAR(255) NOT NULL,"
            " `contact_no` VARCHAR(20) NOT NULL,"
            " `email_add` VARCHAR(255) NOT NULL,"
            " `address` VARCHAR(255) NOT NULL,"
            " PRIMARY KEY(id)"
            ")"
        )
        mycur.execute(
        	"CREATE TABLE `users` ("
        	" `id` INT(11) NOT NULL AUTO_INCREMENT,"
        	" `username` VARCHAR(255) NOT NULL,"
        	" `password` BINARY(32) NOT NULL,"
        	" `info_id` INT(11) NOT NULL,"
        	" PRIMARY KEY(id),"
        	" FOREIGN KEY(info_id) REFERENCES user_data(id)"
        	")"
        )

        mydb.disconnect()

        mydb, mycur = db.connect()

@app.route('/', methods=['GET', 'POST'])
def index():
	if session == {}:
		user = None
	else:
		user = session['user']
	
	if user == None:
		return redirect(url_for('loginPage'))
	else:
		return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def loginPage():
	if request.method == 'POST':
		print("Form submitted via POST method")
		user = request.form.get('username')
		pswd = request.form.get('password')
		persist = request.form.get('remember')
		
		print(user, pswd)
		print("Checking login...")
		if checkLogin(user, pswd):
			print("User exists. Proceeding...")
			session['user'] = user
			session['login-count'] = str(0 if request.cookies.get('login-count') == None else int(request.cookies.get('login-count')) + 1)
			if persist == None:
				session.permanent = False
			else:
				session.permanent = True
			return redirect(url_for('index'))
		else:
			print("Invalid username or password.")
			return render_template('login.html', dialogPrompt='user-not-found')
		
	elif request.method == 'GET':
		if session != {}:
			if session['user']:
				return redirect(url_for('index'))
			elif session['just-registered']:
				return render_template('login.html', dialogPrompt='just-registered')
		else:
			return render_template('login.html', dialogPrompt='not-logged-in')

def checkLogin(user, password, checkType=0):
	mycur.execute("SELECT * FROM users")
	users = mycur.fetchall()
	
	if user in [x[1] for x in users]:
		if checkType == 0:
			user_id = [x[1] for x in users].index(user)
			mycur.execute(f"SELECT HEX(password) FROM users WHERE id = {user_id + 1}")
			fetchedPassHash = mycur.fetchone()[0]
			passHash = sha256(password.encode()).hexdigest()
			
			if passHash.upper() == fetchedPassHash:
				return True
			else:
				return False
		else:
			return True
	else:
		return False

@app.route('/register', methods=['GET', 'POST'])
def registerPage():
	if request.method == 'POST':
		username = request.form['username']
		fname = request.form['fname']
		mname = request.form['mname']
		lname = request.form['lname']
		cnum = request.form['cnum']
		email = request.form['email']
		address = request.form['address']
		password = request.form['password']
		
		# check if they have previously registered before
		if checkLogin(username, '', 1):
			return render_template('register.html', dialogPrompt='user-already-exists')
		
		# check if pre-existing user records match the user's details submitted (to assign its assigned id instead of adding another duplicate entry)
		query = "SELECT * FROM user_data WHERE fname=%s, lname=%s, contact_no=%s, email=%s, address=%s"
		val = (fname, lname, cnum, email, address)
		mycur.execute(query, val)
		matched = mycur.fetchall()
		
		if len(matched) >= 1:
			user_data_id = matched[0][0]
		else:
			# add user info to table
			query = "INSERT INTO `user_info` VALUES (NULL, %s, %s, %s, %s, %s, %s)"
			val = (fname, mname, lname, cnum, email, address)
			mydb.commit()
			
			mycur.execute("SELECT COUNT(*) FROM user_data")
			user_data_id = mycur.fetchall()[0]
		
		# add user into table
		query = "INSERT INTO `users` VALUES (NULL, %s, %s, %s)"
		val = (username, sha256(password.encode()).digest(), user_data_id)
		mycur.execute(query, val)
		mydb.commit()
		
		session['just-registered'] = True
		return redirect(url_for('loginPage'))
		
	else:
		return render_template('register.html')

app.run(host='0.0.0.0', port=2121, debug=True)
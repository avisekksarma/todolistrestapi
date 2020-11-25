from flask import Flask,request,session,make_response
from flask_restful import Resource,Api
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS,cross_origin
from sqlalchemy.exc import IntegrityError
import json
import requests
import logging
import os


# logging parts
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
filehandler = logging.FileHandler('main.log')
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(lineno)d:%(name)s:%(message)s')
filehandler.setFormatter(formatter)
logger.addHandler(filehandler)

app = Flask(__name__)
api = Api(app)
flask_bcrypt = Bcrypt(app)
cors = CORS(app,resources={
    r'/*': {"origins": "*",'supports_credentials': True}
})

# CORS(app)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Start of models:
class User(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(100),nullable=False)
    email = db.Column(db.String(100),nullable=False)
    password = db.Column(db.String(200),nullable=False)
    app_id = db.Column(db.Integer,db.ForeignKey('app.id'),nullable=False)
    
    todos = db.relationship('Todo',backref='user',lazy=True)
    # backref makes like a column (pseudo-column) in todo model so todo.user can be done.
    
    def __repr__(self):
        return f'User:{self.username}'

class Todo(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    todo = db.Column(db.String(500),nullable=False)
    completed = db.Column(db.Boolean,default=False)
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'Todo:{self.id}-{self.user}'

class App(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(50),unique=True,nullable=False)

    users = db.relationship('User',backref='app',lazy=True)

    def __repr__(self):
        return f'AppName: {self.name}'

# End of models.


# Start of Resources of API

# One of the main thing about flask restful is that it automatically puts the OPTIONS route.
class Register(Resource):
    def post(self):
        if session.get('userid'):
            return {'error':'Please first logout to register a new user.','status_code':400},400
        username = request.json.get('username')
        email = request.json.get('email')
        password = str(request.json.get('password'))   # making the password to be string if it were sent as integer maybe.
        app_name = request.json.get('app_name')

        if username and email and password and app_name:
            app = App.query.filter_by(name=app_name).first()
            if app:
                if User.query.filter_by(username = username,app=app).first():
                    return {'error':'Such username already exists.','status_code':400},400
                elif User.query.filter_by(email = email,app=app).first():
                    return {'error':'Such email already exists.','status_code':400},400
                else:
                    pw_hash =  flask_bcrypt.generate_password_hash(password)
                    user = User(username=username,email= email,password=pw_hash,app_id = app.id)
                    db.session.add(user)
                    db.session.commit()
                    return {'success':'You are successfully registered.','status_code':200},200
            else:
                return {'error':'Your provided app name doesnot exist.','status_code':404},404
        else:
            return {'error':"You didn't provide all the credentials",'status_code':400},400

api.add_resource(Register,'/api/register')

class Login(Resource):
    def get(self):
        
        logger.info(f"1. Userid in session is : {session.get('userid')}")
        
        if session.get('userid'):
            return {'success':'You are logged in.','status_code':200},200
        else:
            return {'error':'You are not logged in.','status_code':401},401

    # def options(self):
    #     response_obj = make_response({'hello':'there'})
    #     response_obj.headers['Access-Control-Allow-Origin'] = "*"
    #     response_obj.headers['Access-Control-Allow-Methods'] = "GET, HEAD, OPTIONS,POST"
    #     response_obj.headers['Access-Control-Allow-Headers']='content-type'
    #     return response_obj

    def post(self):
        logger.info(f"2. Userid in session is : {session.get('userid')}")
        if session.get('userid'):
            return {'error':'Please first logout to log back in again.','status_code':403},403
        username = request.json.get('username')
        password = str(request.json.get('password'))
        app_name = request.json.get('app_name')
        
        if app_name:
            # app will be None if no such app with that app name.
            app = App.query.filter_by(name=app_name).first()
        else:
            return {'error':'Please provide your app name.','status_code':400},400
        if username and password and app:
            # following returns None if no user with that username
            user = User.query.filter_by(username=username,app=app).first()
            if user and flask_bcrypt.check_password_hash(user.password,password):
                session['userid'] = user.id
                logger.info(session['userid'])
                return {'success':'Successfully logged in.','status_code':200},200
            else:
                return {'error':'Invalid username and/ or password.','status_code':400},400
        else:
            return {'error':'You did not submit username and/ or password and/ or valid app name','status_code':400},400

api.add_resource(Login,'/api/login')

class Logout(Resource):
    def get(self):
        try:
            del session['userid']
        except :
            return {'error': 'Error! You are not logged in to be logged out.','status_code':400},400
        return {'success': 'You are successfully logged out.','status_code':200},200

api.add_resource(Logout,'/api/logout')

class Todos(Resource):
    def get(self):
        user_id = session.get('userid')
        if user_id:  # that means the user is in session i.e. is logged in.
            user = User.query.filter_by(id=user_id).first()
            all_todos = []
            
            # I dont know why that this did not turn out well.
            # logger.error(User.query.join(Todo,(Todo.user_id == User.id)).filter(User.id == user_id).order_by(Todo.id.desc()))
            todos_of_this_user = list(user.todos)
            todos_of_this_user.reverse()
            try:
                for i in todos_of_this_user:
                    all_todos.append({
                    'id': i.id,
                    'todo': i.todo,
                    'completed' : i.completed
                })
            except AttributeError:   # occurs when user does not have any todo i.e. user.todos is error.
                pass
            return {
                'success':'Successfully got all todos.',
                'userid':user_id,
                'todos':all_todos,
                'status_code':200
                },200
        else:
            return {'error':'Be logged in to use this route.','status_code':400},400

    def post(self):
        # only todo is to be passed in the form data.
        todo = request.json.get('todo')
        if todo is None or todo == '':
            return {'error':'Please provide a todo.','status_code':400},400
        
        
        user_id = session.get('userid')
        if user_id:
            user = User.query.filter_by(id=user_id).first()
            todos_list = []
            try:
                for i in user.todos:
                    todos_list.append(i.todo)
            except AttributeError:   # occurs when user does not have any todo i.e. user.todos is error.
                pass
            for i in todos_list:
                if todo == i:
                    return {'error':'Such todo of yours already exists.','status_code':400},400
            
            # if code flow reaches here then the todo is to be saved.
            saved_todo = Todo(todo=todo,completed=False,user_id=user_id)
            db.session.add(saved_todo)
            db.session.commit()
            return {'success':'Successfully posted data.','status_code':200},200
        else:
            return {'error':'Be logged in to use this route.','status_code':400},400
        
api.add_resource(Todos,'/api/todos')

class TodosOneItem(Resource):
    def get(self,todo_id):
        todo_obj = Todo.query.filter_by(id=todo_id).first()
        if todo_obj:
            if todo_obj.user_id == session.get('userid'):
                return {
                    'success':'Successfully got required todo.',
                    'id': todo_id,
                    'todo': todo_obj.todo,
                    'completed' : todo_obj.completed,
                    'status_code':200
                },200
                
            else:
                return {'error':'Be logged in or You cannot see todo of others.','status_code':403},403
        else:
            return {'error':'Such id of todo does not exist.','status_code':404},404
    
    def put(self,todo_id):
        todo_obj = Todo.query.filter_by(id=todo_id).first()
        if todo_obj:
            if todo_obj.user_id == session.get('userid'): # this means that the todo is owned by the user.
                if request.json.get("todo") and request.json.get("completed"):
                    return {'error':'You cannot update and mark as complete at the same time.','status_code':400},400
                elif request.json.get("todo"):
                    
                    new_todo = request.json.get("todo")
                    todos_list = []
                    user = User.query.filter_by(id=session.get('userid')).first()
                    try:
                        for i in user.todos:
                            todos_list.append(i.todo)
                    except AttributeError:   # occurs when user does not have any todo i.e. user.todos is error.
                        pass
                    if new_todo in todos_list:
                        return {'error':'You are trying to update the todo value to be an already existing todo.','status_code':400},400
                    else:
                        todo_obj.todo = new_todo
                        db.session.commit()
                elif request.json.get("completed"):
                    if request.json.get("completed") == 'Yes':
                        todo_obj.completed = True
                    else:
                        todo_obj.completed = False
                    db.session.commit()
                return {'success':'Successfully updated the todo data.','status_code':200},200
            else:
                return {'error':'Be logged in or You cannot update todo of others.','status_code':400},400
        else:
            return {'error':'No such id of todo item exists.','status_code':404},404
        
        
    def delete(self,todo_id):
        todo_obj = Todo.query.filter_by(id=todo_id).first()
        if todo_obj:
            if todo_obj.user_id == session.get('userid'): # this means that the todo is owned by the user.
                db.session.delete(todo_obj)
                db.session.commit()
                return {'success':'Successfully deleted the todo.','status_code':200},200
            else:
                return {'error':'Be logged in or You cannot delete todo of others.','status_code':400},400
        else:
            return {'error':'Such id of todo does not exist.','status_code':404},404
            
api.add_resource(TodosOneItem,'/api/todos/<int:todo_id>')


class MakeApp(Resource):
    def post(self):
        app_name = request.json.get("app_name")
        if app_name:
            app = App.query.filter_by(name=app_name).first()
            if app:
                return {'error':'Such app name is already taken. Try another one.','status_code':400},400
            else:
                app = App(name=app_name)
                db.session.add(app)
                db.session.commit()
                return {'success':'Successfully created your app.',
                'app_name':app_name,'status_code':200},200
        else:
            return {'error':'Please provide a app name in the form data.','status_code':400},400

api.add_resource(MakeApp,'/api/makeapp')


# End of Resources of API

# @app.route('/fakeapi',methods=['GET','POST'])
# def fakeapi():
#     # logger.info(request.json)
#     # logger.warning(type(request.json))
#     response  = make_response({'message':"You made a get request in fakeapi."})
#     response.set_cookie('avisek',value='coolperson')
#     response.headers['Access-Control-Allow-Credentials'] = True
#     response.headers['Access-Control-Allow-Origin'] = 'https://www.google.com'

#     return response

@app.route('/')
def index():
    response = make_response("WELCOME TO TODOLIST REST API")
    # response.set_cookie('me',value='coolperson')
    return response

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5000)

from flask import Flask, jsonify, make_response, render_template,request, send_from_directory
import uuid
import jwt
from datetime import datetime ,timedelta
import hashlib
from pymongo import MongoClient
from apispec import APISpec
from marshmallow import Schema, fields
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_jwt_extended import JWTManager,jwt_required,get_jwt_identity,create_access_token
from bson import ObjectId

app=Flask(__name__, template_folder='swagger/template')

client = MongoClient("mongodb://localhost:27017/") 
db = client["mydatabase"]
users_collection = db["users"]
user_books =db["books"]

app.config['SECRET_KEY'] = "MY_SECRET_KEY"
jwt = JWTManager(app)

spec = APISpec (
    title='online_library',
    version='1.0.0',
    openapi_version='3.0.2',
    plugins=[FlaskPlugin(),MarshmallowPlugin()]
)

@app.route('/api/swagger.json')
def create_swagger_spec():
    return jsonify(spec.to_dict())

jwt_scheme = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
spec.components.security_scheme("BearerAuth", jwt_scheme)

class RegisterSchema(Schema):
    username=fields.Str()
    email=fields.Str()
    password=fields.Str()
    borrowed_books=fields.Int()

class UserLoginSchema(Schema):
    username=fields.Str()
    password=fields.Str()

class RegisterBookSchema(Schema):
    book_name= fields.Str()
    Author = fields.Str()
    borrowed_status=fields.Str()
    booking_date=  fields.Date()
    time_period= fields.Int()

class BorrowBookSchema(Schema):
    book_name= fields.Str()
    borrowed_status=fields.Str()
    booking_date=  fields.Date()
    time_period= fields.Int()


@app.route('/register', methods=['POST'])
def signup_user(): 
    """Register the user
        ---
        post:
            description: user can register  
            requestBody:
                description: register using email,username,password
                required: true
                content:
                    application/json:
                        schema: RegisterSchema
            responses:
                200:
                    description: successfully registered
                400:
                    description: User already exist
    """
    data = request.get_json(force=True)
    data["password"] = hashlib.sha256(data["password"].encode("utf-8")).hexdigest()
    new_user = users_collection.find_one({"username": data["username"]}) 
    
    if not new_user:
        users_collection.insert_one({ "username":data["username"] ,"email":data['email'], "password":data["password"], "borrowed_books":0})
        return jsonify({'msg': 'User created successfully'}), 200
    else:
        return jsonify({'msg': 'Username already exists'}), 400

with app.test_request_context():
    spec.path(view=signup_user)
 

@app.route("/login", methods=['POST'])
def login():
    """Get jwt token after login
        ---
        post:
            description: get jwt token if register user is logged in
            requestBody:
                required: true             
                content:
                    application/json:
                        schema: UserLoginSchema          
            responses:
                200:
                    description: Successfully returned jwt token                    
                400: 
                    description: user is not registered  
    """

    login_details =  request.get_json()
    user_from_db = users_collection.find_one({'username': login_details['username']})  
    
    if user_from_db:
        encrpted_password = hashlib.sha256(login_details['password'].encode("utf-8")).hexdigest()
        if encrpted_password == user_from_db['password']:
            token = create_access_token({'_id':str(ObjectId(user_from_db['_id'])),'username' :user_from_db['username'],"email":user_from_db['email'],'password':user_from_db['password'],"borrowed_books":user_from_db['borrowed_books'] ,'exp': datetime.utcnow() + timedelta(minutes=20)} , app.config['SECRET_KEY'] )
            return jsonify({'token':token})
       
    return make_response("User not found",401 ,{'WWW.Authentication': 'Basic realm: "login required"'})

with app.test_request_context():
    spec.path(view=login)

@app.route("/users" ,methods=['GET'])
@jwt_required()
def user():
    """Get list of users
        ---
        get:
            description : Get list of users 
            security:
                - BearerAuth: []
            responses:
                200:
                    description: Successfully returned user list
                    content:
                        application/json:
                            schema: RegisterSchema  
                400:
                    description: Not able to fetch user list
    """
    user_list=users_collection.find()
    result = []   
    for user in user_list:
        user_data = {} 
        user_data['username'] = user["username"]
        user_data['password'] = user["password"]
        user_data['email'] = user['email']
        user_data['borrowed_books']=user["borrowed_books"]
        result.append(user_data)   
    
    return jsonify({'users': result}) ,200

with app.test_request_context():
    spec.path(view=user)

@app.route('/user/delete/' ,methods=['DELETE'])
@jwt_required()
def user_delete():
    """Delete User 
        ---
        delete:
            description: deleting user from regirstered list
            security:
                -  BearerAuth: []
            responses: 
                201:
                    description: Successfully deleted user
                    content:
                        application/json:
                            schema: RegisterSchema 
                404:
                    description: Error in deleting user           
    """
    current_user = get_jwt_identity()
    print(current_user)
    user_to_del=users_collection.find_one({'_id':ObjectId(current_user['_id'])})
    
    if user_to_del: 
        users_collection.delete_one(user_to_del)
        return jsonify({'message':'user deleted successfully'}),200

    return jsonify({'message':'users can not be deleted'}),401

with app.test_request_context():
    spec.path(view=user_delete)

@app.route('/user/update/',methods=['PUT'])
@jwt_required()
def user_update():
    """update user Info
        ---
        put:
            description: user can update there Info
            security:
                -  BearerAuth: []
            requestBody:
                required: true             
                content:
                    application/json:
                        schema: RegisterSchema          
            responses:
                200:
                    description: Successfully returned jwt token                    
                400: 
                    description: user is not registered  
    """
    user_data=request.get_json()
    current_user = get_jwt_identity()
    _hased_pass = hashlib.sha256(user_data["password"].encode("utf-8")).hexdigest()
    user_to_update=users_collection.find_one({'_id':ObjectId(current_user['_id'])})

    new_data={
        "borrowed_books": current_user["borrowed_books"],
        "email": user_data["email"],
        "password":  _hased_pass,
        "username": user_data["username"]
    }
    if user_to_update:
        users_collection.update_one({'_id':ObjectId(current_user['_id'])},{"$set":new_data})
        return jsonify({'message':"User updated successfully"}),200

    return jsonify({"message":"Error in update data"}),400

with app.test_request_context():
    spec.path(view=user_update)

@app.route('/books' , methods=["POST"])
@jwt_required()
def set_books():
    """user can publish own book
        ---
        post:
            description: Publish own book
            security:
                -  BearerAuth: []
            requestBody:
                required: true             
                content:
                    application/json:
                        schema: RegisterBookSchema          
            responses:
                200:
                    description: Successfully registered                  
                400: 
                    description: Book not registered  
    """
    current_user=get_jwt_identity()
    book_data=request.get_json()
    old_book= users_collection.find_one({"book_name":book_data['book_name']})
    print (current_user)
    if not old_book:
        if current_user['username'] == book_data['Author']:
            user_books.insert_one({"book_name":book_data['book_name'], "Author":book_data['Author'] ,"borrowed_status":book_data['borrowed_status'] ,"booking_date": book_data['booking_date'],'time_period':book_data['time_period']})
            return jsonify({'msg': 'Published  your book successfully'}), 200
        else:
            return jsonify({'msg': "can not add books of other Authors"}), 401
    else: 
        return jsonify({'msg':"Book already exist"}),401

with app.test_request_context():
    spec.path(view=set_books)

@app.route('/books' ,methods=["GET"])
def books():
    """Get list of Books
        ---
        get:
            description : list all the books
            security:
                - BearerAuth: []
            responses:
                200:
                    description: Successfully returned book list
                    content:
                        application/json:
                            schema: RegisterBookSchema  
                400:
                    description: Not able to fetch book list
    """
    books_list=user_books.find()
    book_results = []

    for book in books_list :
        books_data_list = {}
        books_data_list['book_name'] = book['book_name']  
        books_data_list['Author'] =book['Author']
        books_data_list['borrowed_status'] = book['borrowed_status']
        books_data_list['booking_date'] = book['booking_date'] 
        books_data_list['time_period']=book['time_period']
        book_results.append(books_data_list)
    return jsonify({"books_data": book_results})

with app.test_request_context():
    spec.path(view=books)

@app.route('/books/<string:bookname>/',methods=['DELETE'])
def delete_book(bookname):
    """Delete book 
        ---
        delete:
            description: deleting book from  list
            security:
                -  BearerAuth: []
            parameters:
              - name: bookname
                in: path
                description: book name
                required: true
                schema:
                    type: string
            responses: 
                201:
                    description: Successfully deleted book
                    content:
                        application/json:
                            schema: RegisterBookSchema 
                404:
                    description: Error in deleting user           
    """
    book_to_del=user_books.find_one({"book_name":bookname})
    
    if book_to_del:
        user_books.delete_one(book_to_del)
        return jsonify({'message':'Book deleted successfully'}),200
    
    return jsonify({'message': 'Book does not exist'}),401 

with app.test_request_context():
    spec.path(view=delete_book)

@app.route('/books/borrow/<string:bookname>/',methods=['PUT'])
@jwt_required()
def borrow(bookname):
    """Borrow Book
        ---
        put:
            tag:
               - books
            description: rent book
            security:
                -  BearerAuth: []
            parameters:
              - name: bookname
                in: path
                description: book name
                required: true
                schema:
                    type: string 
            responses:
                200:
                    description: Successfully Borrowed book 
                    content:
                        application/json:
                            schema: BorrowBookSchema                   
                400: 
                    description: can not Borrow book  
    """
    curr_user=get_jwt_identity()
    book_to_borrow=user_books.find_one({"book_name":bookname})
    issue_date = datetime.strptime(book_to_borrow['booking_date'], "%Y-%m-%d")
    print (issue_date)
    if not book_to_borrow:
        return jsonify({'message':'Book not found'}),401

    if  1 < book_to_borrow['time_period'] > 30:
        return jsonify({'message':'Book can not be borrowed as time period exceeds min/max day limit'}),401

    elif issue_date > datetime.now() or book_to_borrow['borrowed_status'] == 'yes':
        return jsonify({'message' : 'Book is already borrowed or it\'s already booked' }),401

    elif curr_user['borrowed_books'] >= 3:
        return jsonify({'message' : 'You have already borrowed 3 books'}),401
    
    user_books.update_one({"book_name":bookname},{"$set":{"borrowed_status":"yes"}})
    users_collection.update_one({'_id':ObjectId(curr_user['_id'])}, {'$inc':{"borrowed_books":1}})
    
    return jsonify({'message':"Successfully borrowed "})

with app.test_request_context():
    spec.path(view=borrow)

@app.route('/docs/')
@app.route('/docs/<path:path>')
def swagger_docs(path=None):
    if not path or path == 'index.html':
        return render_template('index.html', base_url='/docs')
    else:
        return send_from_directory("./swagger/static", path)
       

if __name__ == '__main__':
    app.run(debug=True)
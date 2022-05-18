from apispec import APISpec
from flask import Flask, jsonify, make_response,request
import uuid
import jwt
import datetime
from functools import wraps
import hashlib
from pymongo import MongoClient


app=Flask(__name__,)
client = MongoClient("mongodb://localhost:27017/") 
db = client["mydatabase"]
users_collection = db["users"]
user_books =db["books"]


app.config['SECRET_KEY'] = "MY_SECRET_KEY"


def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token = None

        if 'x-access-tokens' in request.headers:
            token = request.headers['x-access-tokens']
           
        if not token:
            return jsonify({'message' : 'Token is missing'}),403

        try: 
            user_data = jwt.decode(token ,app.config['SECRET_KEY'], algorithms=["HS256"])
            curr_user= users_collection.find_one({"username": user_data["username"]}) 
        except:
            return jsonify({'message':'Token is invalid'}),403
        return f(curr_user ,*args,**kwargs)  
    return decorated

@app.route('/register', methods=['POST'])
def signup_user(): 
    data = request.get_json(force=True)
    data["password"] = hashlib.sha256(data["password"].encode("utf-8")).hexdigest()
    new_user = users_collection.find_one({"username": data["username"]}) 
    
    if not new_user:
        users_collection.insert_one({ "username":data["username"] , "password":data["password"], "borrowed_books":0})
        return jsonify({'msg': 'User created successfully'}), 200
    else:
        return jsonify({'msg': 'Username already exists'}), 409
 

@app.route("/login", methods=['GET'])
def login():
    login_details = request.authorization 
    user_from_db = users_collection.find_one({'username': login_details['username']})  
    
    if user_from_db:
        encrpted_password = hashlib.sha256(login_details['password'].encode("utf-8")).hexdigest()
        if encrpted_password == user_from_db['password']:
            token = jwt.encode({'username' :user_from_db['username'],'password':user_from_db['password'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=20)} , app.config['SECRET_KEY'] )
            return {'token':token}
       
    return make_response("User not found",401 ,{'WWW.Authentication': 'Basic realm: "login required"'})

@app.route("/users" ,methods=['GET'])
@token_required
def user(curr_user):
    user_list=users_collection.find()
    result = []   
    for user in user_list:
        user_data = {}
        print(user["username"])   
        user_data['username'] = user["username"]
        user_data['password'] = user["password"]
        user_data['borrowed_books']=user["borrowed_books"]
        result.append(user_data)   

    return jsonify({'users': result})

@app.route('/books' , methods=["POST"])
@token_required
def set_books(curr_user):
    book_data=request.get_json(force=True)
    print(curr_user['username'])
    new_book= user_books.find_one({"book_name":book_data['book_name']})

    if curr_user['username'] == book_data['Author']:
        user_books.insert_one({"book_id":str(uuid.uuid4()),"book_name":book_data['book_name'], "Author":book_data['Author'] ,"borrowed_status":book_data['borrowed_status'] ,"booking_date": book_data['booking_date'],"time_period":book_data['time_period'],"due_date":book_data['due_date']})
        return jsonify({'msg': 'Your book  is added to the list successfully'}), 200
    else:
        return jsonify({'msg': "can not add books of other Authors"}), 409

    # if not new_book:
    #     user_books.insert_one({"book_id":str(uuid.uuid4()),"book_name":book_data['book_name'], "Author":book_data['Author'] ,"borrowed_status":book_data['borrowed_status'] ,"booking_date": book_data['booking_date'],"time_period":book_data['time_period'],"due_date":book_data['due_date']})
    #     return jsonify({'msg': 'Book added to list successfully'}), 201
    # else:
    #     return jsonify({'msg': 'Book already exists'}), 409

@app.route('/books' ,methods=["GET"])
@token_required
def books(curr_user):
    books_list=user_books.find()
    book_results = []

    for book in  books_list:
        books_data_list = {}
        books_data_list['book_id']=book['book_id']
        books_data_list['book_name'] = book['book_name']
        books_data_list['Author'] = book['Author']
        books_data_list['borrowed_status'] = book['borrowed_status']
        books_data_list['booking_date'] = book['booking_date'] 
        books_data_list['time_period']=book['time_period']
        books_data_list['due_date']=book['due_date']
        book_results.append(books_data_list)
    return jsonify({"books_data": book_results})


@app.route('/books/<string:book_name>',methods=['DELETE'])
@token_required
def delete_book(curr_user,book_name):
    book_to_del=user_books.find_one({"book_name":book_name})
    user_books.delete_one(book_to_del)
    if not book_to_del:
        return jsonify({'message': 'Book does not exist'}),401 
    
    return jsonify({'message':'Book deleted successfully'}),200



# not implemented borrow completely
@app.route('/books/borrow/<string:book_name>',methods=['PUT'])
@token_required
def borrow(curr_user,book_name):
    book_to_borrow=user_books.find_one({"book_name":book_name})

    if not book_to_borrow:
        return jsonify({'message':'Book not found'}),401
    elif book_to_borrow['time_period'] > 30:
        return jsonify({'message' : 'You can not borrow book becoz timeperiod is more that 30 days'}),401
    elif book_to_borrow['borrowed_status'] == 'yes' :
        return jsonify({'message' : 'Book is already borrowed'}),401
    elif curr_user['borrowed_books'] >= 3:
        return jsonify({'message' : 'You have already borrowed 3 books'}),401
    
    user_books.update_one({"book_name":book_name},{"$set":{"borrowed_status":"yes"}})
    users_collection.update_one({"username":curr_user["username"]}, {'$inc':{"borrowed_books":1}})
    
    return jsonify({'message':"Successfully borrowed the book"}),200

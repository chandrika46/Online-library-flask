import pytest
from flask_jwt_extended import create_access_token
from app import app

@pytest.fixture(scope='module')
def client():  
    with app.app_context():
        with app.test_client() as client:
            app.config['TESTING'] = True
            yield client  

@pytest.fixture
def login_token(client):
    access_token = create_access_token({'username': 'rani',
                                        'password': 'rani123'})
    return access_token


def test_signup_user(client):
    response = client.post("/register", json={"username":"chandu" ,"email":"chandu@gmail.com", "password": "chandu123", "borrowed_books":0})
    assert response.status_code == 400 ,response.json

def test_signup_user_not_exist(client):
    response = client.post("/register", json={"username":"chandu" ,"email":"chandu@gmail.com", "password": "chandu123", "borrowed_books":0})
    assert response.status_code == 400 ,response.json

def test_login(client):
    response = client.post('/login', json={'username': 'chandu',
                                        'password': 'chandu123'})
    assert response.status_code == 200 , response.json

def test_registered_users_list(client,login_token):
    access_headers = {"Authorization": "Bearer {}".format(login_token)}
    response = client.get('/users',headers=access_headers)
    assert response.status_code == 200 , response.json

def test_user_update(client,login_token):
    access_headers = {"Authorization": "Bearer {}".format(login_token)}
    response = client.put('/user/update/', json={"username":"chandu" ,"email":"chandrika@gmail.com", "password": "chandu123", "borrowed_books":0}, headers=access_headers)
    assert response.status_code == 200 ,response.json

def test_user_delete(client,login_token):
    access_headers = {"Authorization": "Bearer {}".format(login_token)}
    response = client.delete('/user/delete/',headers=access_headers)
    assert response.status_code == 200 , response.json

def test_set_books(client,login_token):
    access_headers = {"Authorization": "Bearer {}".format(login_token)}
    response = client.post("/books", json={"book_name":"some book", "Author":"rani" ,"borrowed_status":"no" ,"booking_date": "2022-06-01",'time_period': 29}, headers=access_headers)
    assert response.status_code == 401 ,response.json

def test_books_list(client,login_token):
    access_headers = {"Authorization": "Bearer {}".format(login_token)}
    response = client.get('/books',headers=access_headers)
    assert response.status_code == 200 , response.json

def test_delete_book(client,login_token):
    access_headers = {"Authorization": "Bearer {}".format(login_token)}
    response = client.delete('/books/delete/story book/',headers=access_headers)
    assert response.status_code == 401 , response.json

def test_borrow(client,login_token):
    access_headers = {"Authorization": "Bearer {}".format(login_token)}
    response = client.put('/books/borrow/some book/', headers=access_headers)
    assert response.status_code == 200 ,response.json
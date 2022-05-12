from flask import Flask,render_template

app=Flask(__name__,)

@app.route("/")
def login():
    return render_template('login.html')

@app.route("/<string:page_path>")
def page(page_path):
    return render_template(page_path)



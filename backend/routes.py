from flask import current_app as app
from flask import render_template, request, redirect, url_for




@app.route("/Home",methods=["GET","POST"])
def index():
    return "welcome"
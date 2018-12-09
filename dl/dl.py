from flask import Flask, flash, render_template, redirect, url_for, session, logging, request, send_from_directory, jsonify, make_response, json
from functools import wraps
import os
import jwt
import datetime
import string
import random

app = Flask(__name__)
app.secret_key='3q994v 45vfa slv3j'

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
FILESUBURL = "http://localhost:5000/ostrowm4/app/fileSubmitter/"

def id_generator(size=32, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def searchForUrlDownload(urlKey):
    f=open('urlKeysAndFilePaths.txt','r')
    for line in f:
        partsOfFile = line.split(' ')
        if partsOfFile[0] == urlKey:
            return partsOfFile[1]
    return "notPathToFile/notFile"

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.form.get('token')

        if not token:
            flash('Token is missing','danger')
            return redirect(FILESUBURL)
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
        except:
            flash('Invalid token','danger')
            return redirect(FILESUBURL)
        return f(*args,**kwargs)
    return decorated


@app.route("/ostrowm4/app/fileSubmitter/upload/<string:u>", methods=['POST'])
@token_required
def upload(u):

    target = os.path.join(APP_ROOT, u + 'Files')
    if not os.path.isdir(target):
        os.mkdir(target)

    if 'file' not in request.files:
        flash('No file part','danger')
        return redirect(FILESUBURL)

    fileToSub = request.files['file']
    filename = fileToSub.filename

    if filename == '':
        flash('No selected file','danger')
        return redirect(FILESUBURL)

    if len(os.listdir(target)) >= 5:
        flash("You can't submit more than 5 files",'danger')
        return redirect(FILESUBURL)

    destination = '/'.join([target,filename])
    fileToSub.save(destination)
    flash('File submitted','success')

    return redirect(FILESUBURL)

@app.route("/ostrowm4/app/download/<string:f>/<string:u>", methods=['POST'])
@token_required
def download(f,u):

    target = os.path.join(APP_ROOT, u + 'Files')
    filename=f
    response = send_from_directory(target,filename)
    filename = {'filename': f}
    response.headers.set('Content-Disposition', 'attachment', **filename)
    return response

@app.route("/ostrowm4/app/createDownloadLink/<string:f>/<string:u>", methods=['POST'])
@token_required
def createDownloadLink(f,u):
    num_lines = sum(1 for line in open('urlKeysAndFilePaths.txt')) + 1
    urlId = id_generator()
    #filePath has given structure: UserFiles/filename
    filePath = u + 'Files/' + f
    record = str(urlId)+str(num_lines) + ' ' + filePath
    f = open("urlKeysAndFilePaths.txt", "a")
    f.write(record + "\n")
    f.close()
    return redirect(FILESUBURL)

@app.route("/ostrowm4/app/urlDownload/<string:k>")
def urlDownload(k):
    potentialFilePath = searchForUrlDownload(k)
    #potentialFilePath has given structure: UserFiles/filename
    partsOfFilePath = potentialFilePath.split('/')
    directoryName = partsOfFilePath[0]
    fileName = partsOfFilePath[1].rstrip()
    # I make assumption that there is no directory named notPathToFile in dl directory
    target = os.path.join(APP_ROOT, directoryName)
    response = send_from_directory(target,fileName)
    fileNameMap = {'fileName': fileName}
    response.headers.set('Content-Disposition', 'attachment', **fileNameMap)
    return response


if __name__ == '__main__':
    #app.config['SESSION_COOKIE_SECURE'] = True
    #app.config['REMEMBER_COOKIE_SECURE'] = True
    #app.config['SESSION_COOKIE_HTTPONLY'] = True
    #app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    #app.run(port = '443')
    app.run(debug=True, port=5500) #to delete on pi server

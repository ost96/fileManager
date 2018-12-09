from flask import Flask, flash, render_template, redirect, url_for, session, logging, request, send_from_directory, jsonify, make_response, json
from functools import wraps
import os
import json
from os import environ as env
import jwt
import datetime
from dotenv import load_dotenv, find_dotenv
from datetime import timedelta
from redis import Redis
from werkzeug.exceptions import HTTPException
from werkzeug.datastructures import CallbackDict
from flask.sessions import SessionInterface, SessionMixin
import pickle
import redis
from authlib.flask.client import OAuth
from six.moves.urllib.parse import urlencode

import constants

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

AUTH0_CALLBACK_URL = constants.AUTH0_CALLBACK_URL
AUTH0_CLIENT_ID = constants.AUTH0_CLIENT_ID
AUTH0_CLIENT_SECRET = constants.AUTH0_CLIENT_SECRET
AUTH0_DOMAIN = constants.AUTH0_DOMAIN

AUTH0_BASE_URL = 'https://' + AUTH0_DOMAIN
AUTH0_AUDIENCE = constants.AUTH0_AUDIENCE
if AUTH0_AUDIENCE is '':
    AUTH0_AUDIENCE = AUTH0_BASE_URL + '/userinfo'

app = Flask(__name__)

import redis
from uuid import uuid4
app.secret_key=constants.SECRET_KEY

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_FILES = APP_ROOT + "/../dl/"

#Auth0
oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid profile',
    },
)

#FUNCTIONS
def convertUrlDownloadsToList():
    target = os.path.join(APP_FILES, 'urlKeysAndFilePaths.txt')
    listOfUrlDownloads = []
    listOfUrlDownloads.append([])
    f=open(target,'r')
    i = 0
    for line in f:
        # Each record of listOfUrlDownloads is [urlKey,filename]
        partsOfFile = line.split(' ')
        listOfUrlDownloads[i].append(partsOfFile[0])
        filepath = partsOfFile[1].rstrip()
        partsOfFilepath = filepath.split('/')
        listOfUrlDownloads[i].append(partsOfFilepath[1])
        i += 1
        listOfUrlDownloads.append([])
    return listOfUrlDownloads

#REDIS CONFIGURATION
def generate_sid():
    return str(uuid4())

def openSession(username):
    #r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r = redis.StrictRedis(host='localhost', port=6379, password="", decode_responses=True)

    sid1 = str(uuid4())
    key1 = 'ostrowm4:session:'+sid1
    sid2 = str(uuid4())
    key2 = 'ostrowm4:session:'+sid2
    value1 = username
    r.set(key1, value1)
    r.set(key2, "true")
    return sid1, sid2

def closeSession(sid1, sid2):
    #r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r = redis.StrictRedis(host='localhost', port=6379, password="", decode_responses=True)
    key1='ostrowm4:session:'+sid1.rstrip()
    key2='ostrowm4:session:'+sid2.rstrip()
    r.delete(key1)
    r.delete(key2)

def getLogin(sid):
    #r = redis.StrictRedis(host='localhost', port=6379, db=0)
    r = redis.StrictRedis(host='localhost', port=6379, password="", decode_responses=True)
    key = 'ostrowm4:session:'+sid.rstrip()
    #TESTY: zapytanie redis get key w konsoli zwróci przechowywaną wartość, poniższy kod nie.
    return r.get(key) #.decode('ascii')

#saving sid's in file
def saveSid(sid):
    f = open("sid.txt", "a")
    f.write(sid + "\n")
    f.close()
#getting sid from file, first line = username, second line = "true"
def getSid(num):
    with open('sid.txt', "r") as f:
        lines=f.readlines()
    return lines[num - 1]

#application

@app.route('/ostrowm4/app/')
def index():
    return render_template('index.html')

def check_if_login(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if getLogin(getSid(2)) == "true":
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return wrap

#If redis is not required:
'''
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if constants.PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated
'''

@app.route('/ostrowm4/app/login/')
def login():
    return render_template('login.html')

@app.route('/ostrowm4/app/loginLogic/')
def loginLogic():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE)

@app.route('/ostrowm4/app/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()
    username = userinfo['name']

    session[constants.JWT_PAYLOAD] = userinfo
    session[constants.PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }

    sessionSid1, sessionSid2 = openSession(username)
    saveSid(sessionSid1)
    saveSid(sessionSid2)
    flash('You are now logged in', 'success')
    app.config['token'] = jwt.encode({'user' : username, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(minutes=3)}, app.config['SECRET_KEY'])

    return redirect(url_for('fileSubmitter'))

@app.route('/ostrowm4/app/logout/')
@check_if_login
def logout():
    closeSession(getSid(1), getSid(2))
    open('sid.txt', 'w').close()
    session.clear()
    params = {'returnTo': url_for('login', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))
    #return redirect(url_for('login'))

@app.route('/ostrowm4/app/fileSubmitter/')
@check_if_login
def fileSubmitter():
    target = os.path.join(APP_FILES, getLogin(getSid(1)) + 'Files')
    userFiles = os.listdir(target)
    dowloadUrlsList = convertUrlDownloadsToList()
    return render_template('fieSubmitter.html', files=userFiles, target=target, token=app.config['token'], username=getLogin(getSid(1)), isLog = getLogin(getSid(2)), dowloadUrls = dowloadUrlsList)

if __name__ == '__main__':
    #app.config['SESSION_COOKIE_SECURE'] = True
    #app.config['REMEMBER_COOKIE_SECURE'] = True
    #app.config['SESSION_COOKIE_HTTPONLY'] = True
    #app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    #app.run(port = '443')
    app.run(debug=True, port=5000) #to delete on pi server

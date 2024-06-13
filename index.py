#!/usr/bin/env python
from flask import Flask, render_template, request, jsonify
from datetime import datetime
import secrets
import string
import bcrypt
import bson
from pymongo import MongoClient
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

def generate(n):
  alphabet = string.ascii_letters + string.digits + '_'
  return(''.join(secrets.choice(alphabet) for i in range(n)))

@app.after_request
def add_header(r):
  r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
  r.headers["Pragma"] = "no-cache"
  r.headers["Expires"] = "0"
  r.headers['Cache-Control'] = 'public, max-age=0'
  return r

def auth():
  client = MongoClient("localhost")
  db = client.module01
  # try:
  if 'sid' in request.cookies:
    sid = request.cookies['sid']
    client = MongoClient("localhost")
    db = client.module01
    sessions = db.sessions
    result = sessions.find_one({'session' : sid})

    handle = ""
    if result is not None:
      handle = result["handle"]

    teams = db.teams
    result = teams.find_one({ 'handles' : { '$in' : [ handle ] }})

    team = ""
    if result is not None:
      team = result["team"]

    teammates = ""
    if team != "":
      teammates = ' , '.join(result['handles'])

    return { "sid" : sid, "handle" : handle, "team" : team, "teammates" : teammates }

  # except:
  #   pass

  return { "sid" : '', "handle" : "", "team" : "" }

def teammates():
  client = MongoClient("localhost")
  db = client.module01
  try:
    if 'sid' in request.cookies:
      sid = request.cookies['sid']
      client = MongoClient("localhost")
      db = client.module01
      sessions = db.sessions
      result = sessions.find_one({'session' : sid})

      handle = ""
      if result is not None:
        handle = result["handle"]

      teams = db.teams
      result = teams.find_one({ 'handles' : { '$in' : [ handle ] }})

      team = ""
      if result is not None:
        team = result["team"]

      return result['handles']

  except:
    pass

  return []
  

@app.route('/data.html', methods = ['GET'])
def data():
  session = auth()
  result = render_template('data.html', session = session)
  return result

@app.route('/upload.html', methods = ['POST'])
def upload():
  return '{}'

@app.route('/submit.html', methods = ['GET', 'POST'])
def submit():
  session = auth()
  result = render_template('submit.html', session = session)
  return result

@app.route('/teams.html', methods = ['GET', 'POST'])
def teams():
  session = auth()
  if request.method == 'POST':
    action = request.values.get('action')
    if action == "create":
      # try:
      if session['sid'] == '':
        return { 'status' : -999 }

      handles = request.values.get('handles')
      handles = handles.split(';')
      for i in range(len(handles)):
        handles[i] = handles[i].strip()

      handles = [handle for handle in handles if handle]
      
      if len(handles) < 3 or len(handles) > 4:
        return { 'status' : -1, 'message' : 'Your team size must be 3 or 4.' }
      
      client = MongoClient("localhost")
      db = client.module01
      teams = db.teams
      team = request.values.get('team').strip()

      if team == "":
        return { 'status' : -2, 'message' : 'Your team name must be nonempty.' }

      result = teams.find_one({ "team": team })

      if result is not None:
        return { 'status' : -3, 'message' : 'That team name is already taken.' }

      result = teams.find_one({ 'handles' : { '$in' : handles }})
      if result is not None:
        return { 'status' : -4, 'message' : 'One or more of those handles are already in a team.' }

      for handle in handles:
        result = db.handles.find_one({ 'handle' : handle })
        if result is None:
          return { 'status' : -5, 'message' : 'One of those handles doesn&rsquo;t exist.' }

      if len(handles) != len(set(handles)):
        return { 'status' : -6, 'message' : 'You can&rsquo;t provide a handle more than once.' }

      print(session['handle'])
      if session['handle'] not in handles:
        return { 'status' : -7, 'message' : 'Make sure you list yourself among the teammates.' }

      result = teams.update_one({"$or" : [{"handles": {'$in' : handles }}, {'team': team}]},
        { "$setOnInsert": { "team": team, "handles" : handles }}, upsert = True)

      if result.raw_result['updatedExisting'] == False:
        print("team created")
        return { 'status' : 1, 'team' : team, "teammates" : ' , '.join(handles) }


      #except:
      #  print('A')
      #  pass

      return { 'status' : 0, 'message' : 'An error occurred.' }

    elif action == "dissolve":
      team = session['team']

      if team != "":
        client = MongoClient("localhost")
        db = client.module01
        teams = db.teams
        result = teams.delete_many({ "team" : team })

        print(1)
        if result is None:
          return { 'status' : -1 }

        print(2)
        if result.deleted_count == 0:
          return { 'status' : -2 }

        print(3)
        if result.deleted_count > 1:
          return { 'status' : -3 }
        
        print(4)
        return { 'status' : 1 }

      print(5)
      return { 'status' : 0 }

  result = render_template('teams.html', session = session)
  return result

@app.route('/login.html', methods = ['GET', 'POST'])
def login():
  if request.method == 'POST':
    try:
      client = MongoClient("localhost")
      db = client.module01
      handles = db.handles
      handle = request.values.get('handle')
      password = request.values.get('password')
      print(handle)
      print(password)
      result = handles.find_one({ "handle": handle })
      if result is not None: 
        correct = result["password"]
        print(correct)
        hashed = bcrypt.hashpw(password.encode("utf-8"), correct)
        print(hashed)

        if hashed == correct:
          print("Login successfull")
          sessions = db.sessions
          sid = generate(20)
          result = sessions.insert_one({ "handle": handle, "session": sid })
          return { 'status' : 1, 'handle' : handle, 'session' : sid } 

    except:
      pass

    return { 'status' : 0 }
  
  else:
    session = auth()
    result = render_template('login.html', session = session)
    return result

@app.route('/signup.html', methods = ['GET', 'POST'])
def signup():
  if request.method == 'POST':
    try:
      client = MongoClient("localhost")
      db = client.module01
      handles = db.handles
      handle = request.values.get('handle')
      print(handle)

      if handle == '':
        return { 'status' : -2 }
        
      password = generate(7)
      print(password)
      hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
      print(hashed)
      result = handles.update_one({ "handle": handle }, { "$setOnInsert": { "password": hashed } }, upsert = True)

      if result.raw_result['updatedExisting'] == False:
        print("Handle created")
        sessions = db.sessions
        sid = generate(20)
        result = sessions.update_one({ "handle": handle }, { "$set" : { "session": sid } }, upsert = True )
        return { 'status' : 1, 'handle' : handle, 'password' : password, 'session' : sid } 

      elif result.raw_result['updatedExisting'] == True:
        print("That handle is already taken.")
        return { 'status' : -1, 'handle' : handle }
     
    except:
      pass

    return { 'status' : 0 }

  else:
    session = auth()
    result = render_template('signup.html', session = session)
    return result


@app.route('/', methods = ['GET', 'POST'])
@app.route('/index.html', methods = ['GET', 'POST'])
def main():
  session = auth()
  result = render_template('index.html', session = session)
  return result

if __name__ == '__main__':
  handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=3)
  logger = logging.getLogger('tdm')
  logger.setLevel(logging.ERROR)
  logger.addHandler(handler)
  app.run(host="0.0.0.0", debug=True, port=51238)
   

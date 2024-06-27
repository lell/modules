#!/usr/bin/env python
from common import *
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
import secrets
import string
import bcrypt
import bson
from tempfile import mkstemp
from time import time
from pymongo import MongoClient
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

@app.after_request
def add_header(r):
  r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
  r.headers["Pragma"] = "no-cache"
  r.headers["Expires"] = "0"
  r.headers['Cache-Control'] = 'public, max-age=0'
  return r



@app.route('/data.html', methods = ['GET'])
def data():
  session = auth()
  result = render_template('data.html', session = session)
  return result

@app.route('/upload.html', methods = ['POST'])
def upload():
  session = auth()
  if session['sid'] == '':
    return { 'status' : -1, 'message' : 'You must be signed in.' }

  client = MongoClient("localhost")
  db = client.module01
  files = db.files

  if 'file' not in request.files:
    return { 'status' : -2, 'message' : 'Invalid POST request.' }

  file = request.files['file']
  if not file:
    return { 'status' : -3, 'message' : 'Could not find file.' }

  if file.filename == '':
    return { 'status' : -4, 'message' : 'No file selected.' }
  
  if not allowed_file(file.filename):
    return { 'status' : -5, 'message' : 'Invalid filename.' }

  (fd, fname) = mkstemp(suffix = "", prefix = 'file_' + generate(3), dir = UPLOADS)
  os.close(fd)
  file.save(fname)
  files.insert_one({ "handle" : session['handle'], "name" : fname, "time" : time() })
  tasks = db.tasks
  tasks.insert_one({ "handle" : session['handle'], "type" : "evaluate", "name" : fname, "time" : time() })
  return { 'status' : 1 }

@app.route('/submit.html', methods = ['GET', 'POST'])
def submit():
  if request.method == 'POST':
    content = "<center><table> <tr class='board'> <td class='board'> Time </td> <td class='board'> Submitter </td> <td class='board'> Score </td> <td class='board'>  </td> </tr> "

    for result in evaluated():
      public = "?"
      if "public" in result:
        public = "%0.2f" % (100 * result["public"]) + "%"

      content = content + "<tr class='board'>"
      content = content + "<td class='board'>" + timestamp(result["time"]) + "</td>"
      content = content + "<td class='board'>" + result["handle"] + "</td>"
      content = content + "<td class='board'>" + public + "</td>"
      content = content + "<td class='board bin'> x </td>"
      content = content + "</tr>"

    content = content + "</table></center>"
    return { "content" : content }

  else:
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
        return { 'status' : -1, 'message' : 'You must be signed in.' }

      handles = request.values.get('handles')
      handles = handles.split(';')
      for i in range(len(handles)):
        handles[i] = handles[i].strip()

      handles = [handle for handle in handles if handle]
      
      if len(handles) < 3 or len(handles) > 4:
        return { 'status' : -2, 'message' : 'Your team size must be 3 or 4.' }
      
      client = MongoClient("localhost")
      db = client.module01
      teams = db.teams
      team = request.values.get('team').strip()

      if team == "":
        return { 'status' : -3, 'message' : 'Your team name must be nonempty.' }

      result = teams.find_one({ "team": team })

      if result is not None:
        return { 'status' : -4, 'message' : 'That team name is already taken.' }

      result = teams.find_one({ 'handles' : { '$in' : handles }})
      if result is not None:
        return { 'status' : -5, 'message' : 'One or more of those handles are already in a team.' }

      for handle in handles:
        result = db.handles.find_one({ 'handle' : handle })
        if result is None:
          return { 'status' : -6, 'message' : 'One of those handles doesn&rsquo;t exist.' }

      if len(handles) != len(set(handles)):
        return { 'status' : -7, 'message' : 'You can&rsquo;t provide a handle more than once.' }

      print(session['handle'])
      if session['handle'] not in handles:
        return { 'status' : -8, 'message' : 'Make sure you list yourself among the teammates.' }

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
        return { 'status' : -1 }
        
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
        return { 'status' : -2, 'handle' : handle }
     
    except:
      return { 'status' : -3, 'message' : 'An unknown error occurred.' }

    return { 'status' : 0 }

  else:
    session = auth()
    result = render_template('signup.html', session = session)
    return result


@app.route('/', methods = ['GET'])
@app.route('/index.html', methods = ['GET', 'POST'])
def main():
  if request.method == 'POST':
    content = "<center><table> <tr class='board'> <td class='board'> Rank </td> <td class='board'> Team </td> <td class='board'> Score </td> </tr> "

    rank = 1
    for result in leaderboard():
      public = "?"
      if "public" in result:
        public = "%0.2f" % (100 * result["public"]) + "%"
      
      handle = result["handle"]
      team = getteam(handle)
      content = content + "<tr class='board'>"
      content = content + "<td class='board'>" + str(rank) + "</td>"
      content = content + "<td class='board'>" + team + "</td>"
      content = content + "<td class='board'>" + public + "</td>"
      content = content + "</tr>"
      rank = rank + 1

    content = content + "</table></center>"
    print(content)
    return { "content" : content }

  else:
    session = auth()
    result = render_template('index.html', session = session)
    return result

if __name__ == '__main__':
  handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=3)
  logger = logging.getLogger('tdm')
  logger.setLevel(logging.ERROR)
  logger.addHandler(handler)
  app.run(host="0.0.0.0", debug=True, port=51238)
   

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from time import time
import secrets
import string
import bcrypt
from pymongo import MongoClient, DESCENDING

mydir = os.path.dirname(os.path.realpath(__file__))
UPLOADS = mydir + '/uploads'
EXTENSIONS = {'txt', 'csv', 'tsv' }

def timestamp(zz):
  return datetime.fromtimestamp(zz).strftime("%Y-%m-%d %H:%M:%S")

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
      teammates = ', '.join(result['handles'])

    return { "sid" : sid, "handle" : handle, "team" : team, "teammates" : teammates }

  # except:
  #   pass

  return { "sid" : '', "handle" : "", "team" : "" }

def gethandle():
  handle = ""
  if 'sid' in request.cookies:
    sid = request.cookies['sid']
    client = MongoClient("localhost")
    db = client.module01
    sessions = db.sessions
    result = sessions.find_one({'session' : sid})

    if result is not None:
      handle = result["handle"]

  return handle

def getteam(handle = ""):
  if handle == "":
    handle = gethandle()

  client = MongoClient("localhost")
  db = client.module01
  teams = db.teams
  result = teams.find_one({ 'handles' : { '$in' : [ handle ] }})
  if result is not None:
    return result["team"]

  return ""


def getteams():
  client = MongoClient("localhost")
  db = client.module01
  teams = db.teams
  results = teams.find({})
  teams = []
  for result in results:
    teams.append(result["team"])

  return teams

def teammates(handle = ""):
  client = MongoClient("localhost")
  db = client.module01
  if handle == "":
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

  return []
  
def leaderboard():
  teams = getteams()
  results = []
  for team in teams:
    client = MongoClient("localhost")
    db = client.module01
    teams = db.teams
    result = teams.find_one({ 'team' : team })
    if result is None:
      return []

    handles = result["handles"]

    tasks = db.tasks
    print(team)
    print(handles)
    files = tasks.find({ 'handle' : { '$in' : handles }, 'type' : 'evaluated' })
    files.sort("public", DESCENDING)
    files = [file for file in files]
    if len(files) > 0:
      results.append(files[0])

  return results

def evaluated():
  handles = teammates()
  client = MongoClient("localhost")
  db = client.module01
  tasks = db.tasks
  results = tasks.find({ 'handle' : { '$in' : handles }, 'type' : 'evaluated' }).sort("time", DESCENDING)
  returns = []
  for result in results:
    returns.append(result)

  return returns

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTENSIONS

def generate(n):
  alphabet = string.ascii_letters + string.digits + '_'
  return(''.join(secrets.choice(alphabet) for i in range(n)))

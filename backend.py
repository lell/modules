#!/usr/bin/env python
from common import *
import pandas as pd
import numpy as np
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
import secrets
import string
import bcrypt
import bson
from tempfile import mkstemp
from time import time, sleep
from pymongo import MongoClient
import logging
from logging.handlers import RotatingFileHandler

def main():
  private = pd.read_csv("private.txt", sep = ' ', header = 0)
  public = pd.read_csv("public.txt", sep = ' ', header = 0)
  stamp = "[" + datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S") + "]"
  print(stamp + ' starting backend')
  done = False
  client = MongoClient("localhost")
  db = client.module01
  tasks = db.tasks
  while not done:
    stamp = "[" + datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S") + "]"
    # print("[" + stamp + "]")
    result = tasks.find_one_and_update({ "type" : "evaluate" }, { '$set' : { "type" : "evaluating", "time" : time()} }, upsert = False)
    if result != None:
      fname = result['name']
      print(stamp + ' evaluating ' + fname)
      df = pd.read_csv(fname, sep = ' ', header = 0)
      pr_mask = private.notna().values.reshape(-1)
      pr_acc = np.mean(df.values.reshape(-1)[pr_mask] == private.values.reshape(-1)[pr_mask])
      pu_mask = public.notna().values.reshape(-1)
      pu_acc = np.mean(df.values.reshape(-1)[pu_mask] == public.values.reshape(-1)[pu_mask])
      result = tasks.find_one_and_update({ "name" : result["name"] },
        { '$set' : { "type" : "evaluated", "time" : time() , "public" : pu_acc, "private" : pr_acc } }, upsert = False)

      print(stamp + ' evaluated ' + fname)

    sleep(1)

if __name__ == '__main__':
  main()

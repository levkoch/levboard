from flask import Flask
import os

app = Flask(__name__)
app.secret_key = os.environ['FLASK_TOKEN']
app.static_folder = '../static'
app.template_folder = '../templates'

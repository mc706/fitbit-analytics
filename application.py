from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from config import DEBUG
application = Flask(__name__)

application.config.from_object('config')

if not DEBUG:
    toolbar = DebugToolbarExtension(application)

db = SQLAlchemy(application)

# mail = Mail(app)
#
# import logging
# from logging.handlers import RotatingFileHandler
# file_handler = RotatingFileHandler(
#     'logs/fitbitAnalytics.log', 'a', 1 * 1024 * 1024, 10)
# file_handler.setFormatter(
#     logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
# app.logger.setLevel(logging.INFO)
# file_handler.setLevel(logging.INFO)
# app.logger.addHandler(file_handler)

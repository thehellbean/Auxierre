#!/usr/bin/env python
# -*- coding: utf-8 -*-

import flask
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.mail import Mail
from flask.ext.babel import Babel, gettext
from geoip import geolite2
import config
import random

app = Flask(__name__)
app.config.from_object(config.DevelopmentConfig)
db = SQLAlchemy(app)
mail = Mail(app)
babel = Babel(app)

from flaskapp import views, models
from flaskapp.userlogin import authorise
import ffttask.tasks

@babel.localeselector
def get_locale():
	country_language = {'KR': 'ko', 'SE': 'sv', 'GB': 'en', 'US': 'en'}
	if "l" in flask.request.cookies:
		val = flask.request.cookies.get("l", "")
		if val in country_language.values():
			return val
	match = geolite2.lookup(flask.request.remote_addr)
	if match and match.country in country_language.keys():
		return country_language[match.country]
	else:
		lang = flask.request.accept_languages.best_match(app.config['LANGUAGES'].keys())
		if lang:
			return lang
		else:
			return "en"

def get_flag():
	langs = {'en': gettext('English'), 'sv': gettext('Swedish'), 'ko': gettext('Korean')}
	loc = get_locale()
	return (loc, langs[loc])

def get_flag_list():
	langs = {'en': gettext('English'), 'sv': gettext('Swedish'), 'ko': gettext('Korean')}
	loc = get_locale()
	del langs[loc]
	return zip(langs.keys(), langs.values())

@app.before_request
def csrf_protect():
	if flask.request.method == "POST":
		token = flask.session.get('_csrf_token', None)
		if not token or token != flask.request.form.get('_csrf_token'):
			flask.abort(403)

def generate_csrf_token():
	if '_csrf_token' not in flask.session:
		flask.session['_csrf_token'] = ''.join(random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(32))
	return flask.session['_csrf_token']

def wrap_authorise():
	return authorise(flask.request)

app.jinja_env.globals.update(get_flag=get_flag, get_flag_list=get_flag_list, get_user=wrap_authorise)
app.jinja_env.globals.update(csrf_token = generate_csrf_token)
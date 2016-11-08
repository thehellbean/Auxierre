import hashlib
import datetime
from flask import request, render_template, redirect, url_for
from flaskapp.models import User, Session
from flaskapp import db
from functools import wraps
import random
import base64

def requires_auth(permission, requires_email_verification=True):
	def check_auth(f):
		@wraps(f)
		def auth_wrapper(*args, **kwargs):
			user = authorise(request)
			if not user or user.permissions < permission or (requires_email_verification and not user.emailverified):
				return render_template("access denied.html"), 403
			return f(*args, **kwargs)
		return auth_wrapper
	return check_auth

def not_auth():
	def check_no_auth(f):
		@wraps(f)
		def no_auth_wrapper(*args, **kwargs):
			user = authorise(request)
			if user:
				return redirect(url_for('index'))
			return f(*args, **kwargs)
		return no_auth_wrapper
	return check_no_auth


def login(username, password):
	user = User.query.filter_by(username=username).first()
	if user:
		salted = password.encode("utf-8") + user.salt.encode("utf-8")
		if hashlib.sha256(salted).hexdigest() == user.password:
			return user
		else:
			return None
	else:
		return None

def token(user, save):
	alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
	token = ''.join(random.choice(alphabet) for i in range(10))
	cookie = base64.b64encode(token + " " + str(user.id))
	if save:
		expires = datetime.datetime.utcnow() + datetime.timedelta(days=365)
		ses = Session(token, expires, user.id)
		db.session.add(ses)
		db.session.commit()
	else:
		expires = datetime.datetime.utcnow() + datetime.timedelta(days=1)
		ses = Session(token, expires, user.id)
		db.session.add(ses)
		db.session.commit()
	return cookie

def authorise(request):
	cookie = request.cookies.get('auth', None)
	if not cookie:
		return None
	decoded = base64.b64decode(cookie).split(" ")
	token = decoded[0]
	userid = decoded[1]
	if token and userid:
		ses = Session.query.filter_by(token=token).first()
		if ses:
			if str(ses.user_id) == userid:
				return ses.user
	return None
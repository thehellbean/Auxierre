# -*- coding: utf-8 -*-
import datetime
import os
import flask
import re
from mutagen.easyid3 import EasyID3
from flask import request, url_for
from flaskapp import app, models, db
from werkzeug import secure_filename
from sqlalchemy import desc, func, or_
from flask.ext.babel import gettext
import userlogin
import emails
import ffttask.tasks
from werkzeug.contrib.cache import SimpleCache
import hashlib


stat_cache = SimpleCache()
ALLOWED_EXTENSIONS = ["mp3"]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.errorhandler(404)
def page_not_found(e):
	return flask.render_template("404.html"), 404

@app.route("/")
@app.route("/index")
def index():
	featured = models.FeaturedTransform.query.order_by(models.FeaturedTransform.created.desc()).first()
	return flask.render_template("index.html", featured=featured)

@app.route("/songinfo/<int:songid>/")
def songinfo(songid):
	song = models.Song.query.get(songid)
	if song:
		if song.private and userlogin.authorise(request) != song.user:
			return flask.render_template("access denied.html"), 403
		lastIndex = request.args.get("lastIndex", type=int)
		if request.method == "GET" and lastIndex is not None:
			return flask.jsonify({"lastIndex": song.last_index, "transformData": song.data[lastIndex:], "finished": song.full, "length": song.data_length, "timePerSegment": song.time_per_segment})
		else:
			try:
				song.views += 1
				db.session.commit()
			except:
				db.session.rollback()
			if song.artist:
				song_title = gettext("%(title)s by %(artist)s", title=song.title, artist=song.artist)
				page_title = gettext("Auxierre") + gettext("visualisation of %(title)s by %(artist)s", title=song.title, artist=song.artist)
			else:
				song_title = gettext('%(title)s', title=song.title)
				page_title = gettext("Auxierre") + gettext('visualisation of %(title)s', title=song.title)
			return flask.jsonify({"overview": flask.render_template("overview.html", song=song), "title": song_title, "link": song.path[25:], "page title": page_title})
	else:
		return flask.jsonify({"success": False})

@app.route("/visualise/")
def visualise():
	return flask.render_template("transform info.html")

@app.route("/visualise/<int:songid>/rate/", methods=["POST"])
@userlogin.requires_auth(0)
def rate_song(songid):
	if request.method == "POST":
		score = request.form.get("score", type=float)
		if not score:
			return flask.jsonify({"success": False, "error": "Not valid score"})
		if score < 0:
			score = 0.0
		elif score > 5:
			score = 5.0
		song = models.Song.query.get(songid)
		user = userlogin.authorise(request)
		if models.SongRating.query.filter_by(song=song, user=user).all():
			models.SongRating.query.filter_by(song=song, user=user).first().rating = score
		else:
			rating = models.SongRating(user.id, song.id, score)
			db.session.add(rating)
		try:
			db.session.commit()
		except:
			db.session.rollback()
			raise
		rating = 0
		count = 0
		for r in song.ratings:
			rating += r.rating
			count += 1
		if count == 0:
			count = 1
		song.average_rating = rating / count
		try:
			db.session.commit()
		except:
			db.session.rollback()
			raise
		return flask.jsonify({"success": True})
	else:
		return flask.jsonify({"success": False})

@app.route("/visualise/<int:songid>/edit/", methods=["GET", "POST"])
@userlogin.requires_auth(0)
def edit_song(songid):
	song = models.Song.query.get(songid)
	if not song:
		return flask.render_template("404.html"), 404
	if userlogin.authorise(request) != song.user or not song:
		return flask.render_template("access denied.html"), 403
	elif request.method == "GET":
		return flask.render_template("edit song.html", song=song)
	elif request.method == "POST":
		if request.form.get("delete") == "true":
			p = song.path
			try:
				db.session.delete(song)
				db.session.commit()
				os.remove(p)
				return flask.jsonify({"success": True})
			except:
				db.session.rollback()
				return flask.jsonify({"success": False})
		song.title = request.form.get("title")
		song.artist = request.form.get("artist")
		song.genre = request.form.get("genre")
		song.album = request.form.get("album")
		song.private = request.form.get("private") == "on"
		try:
			db.session.commit()
			return flask.jsonify({"success": True})
		except:
			db.session.rollback()
			return flask.jsonify({"success": False})

@app.route("/upload/", methods=["GET"])
def transform_upload():
	recent = db.session.query(models.Song).filter_by(private=False).order_by(desc(models.Song.created)).limit(5).all()
	return flask.render_template("transform upload.html", recent_song=recent)

@app.route("/playlist/<int:playlistid>")
def playlist_view(playlistid):
	playlist = models.Playlist.query.get(playlistid)
	if playlist:
		return flask.render_template("playlists.html", playlist=playlist)
	else:
		return flask.render_template("404.html", 404)

@app.route("/getsong/<int:songid>/")
def getsong(songid):
	song = models.Song.query.get(songid)
	if song:
		return flask.send_file(song.path)
	else:
		return flask.jsonify({'success': False})

@app.route("/updates/")
def updates():
	return flask.render_template("updates.html")

@app.route("/contact/")
def contact():
	return flask.render_template("contact.html")

@app.route("/stats/")
def stats():
	stat = {}
	stat["total_views"] = models.Song.query.with_entities(func.sum(models.Song.views)).first()[0]
	stat["avg_views"] = models.Song.query.with_entities(func.avg(models.Song.views)).first()[0]
	stat["total_song"] = models.Song.query.count()
	stat["total_data"] = models.Song.query.with_entities(func.sum(models.Song.data_length)).first()[0]
	stat["total_seconds"] = models.Song.query.with_entities(func.sum(models.Song.duration)).first()[0]
	stat["average_rating"] = db.session.query(func.avg(models.Song.average_rating).label('average')).filter(models.Song.average_rating != 0).first()[0]
	return flask.render_template("stats.html", stats=stat)

@app.route("/about/")
def about():
	return flask.redirect(url_for("index"))

@app.route("/catalogue/<int:page>/", methods=["GET"])
@app.route("/catalogue/", methods=["GET"])
def catalogue(page=1):
	if page < 1:
		page = 1
	try:
		sort = int(request.args.get("sort", 0))
	except:
		sort = 0
	sort_methods = [models.Song.title, models.Song.artist, models.Song.album, models.Song.genre, models.Song.duration, models.Song.views, models.Song.average_rating, models.Song.created, models.User.username]
	if sort > len(sort_methods) - 1:
		sort = len(sort_methods) - 1
	elif sort < 0:
		sort = 0
	title = models.Song.title.ilike("%"+request.args.get("title", "").strip()+"%")
	artist = models.Song.artist.ilike("%"+request.args.get("artist", "").strip()+"%")
	album = models.Song.album.ilike("%"+request.args.get("album", "").strip()+"%")
	genre = models.Song.genre.ilike("%"+request.args.get("genre", "").strip()+"%")
	uploader = models.User.username.ilike("%"+request.args.get("uploader", "").strip()+"%")
	songs = models.Song.query.order_by(desc(sort_methods[sort])).filter(title, artist, album, genre, uploader).filter(or_(models.Song.private == False, models.Song.user == userlogin.authorise(request))).distinct()
	songs = songs.paginate(page, 15)
	return flask.render_template("catalogue.html", songs=songs)

@app.route("/l")
def set_language():
	lang = request.args.get('l', "", type=str)
	if lang:
		response = app.make_response("Language set")
		response.set_cookie('l', value=lang)
		return response
	return flask.redirect(url_for("index"))

@app.route("/upload/", methods=["POST"])
@userlogin.requires_auth(4)
def upload():
	if request.method == "POST":
		data_files = request.files.getlist("files")[:3]
		private_values = request.form.getlist("private")
		result_ids = []
		song_names = []
		results = []
		for private_index, file in enumerate(data_files):
			if file and allowed_file(file.filename):
				filename = secure_filename(file.filename)
				songname = filename.replace("_", " ")
				now = datetime.datetime.now()
				filename = os.path.join("%s.%s" % (now.strftime("%Y-%m-%d-%H-%M-%S-%f"), filename.rsplit('.', 1)[1]))
				path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
				file.save(path)
				artist = ""
				album = ""
				genre = ""
				private = private_values[private_index] == "true"
				try:
					tags = EasyID3(path)
					artist = tags.get('artist', [""])[0]
					songname = tags.get('title', [songname])[0]
					album = tags.get('album', [""])[0]
					genre = tags.get('genre', [""])[0]
				except:
					# No ID3 tags, nothing to do about that
					pass
				song = models.Song(path, songname, artist, album, genre, private)
				user = userlogin.authorise(request)
				if user:
					song.user_id = user.id
				db.session.add(song)
				try:
					db.session.commit()
				except:
					db.session.rollback()
				results.append(True)
				result_ids.append(song.id)
				song_names.append(songname)
				ffttask.tasks.fftMP3.delay(song.id)
		return flask.jsonify({"success": results, "id": result_ids, "name": song_names})
	return flask.jsonify({"success": False})

@app.route("/login/", methods=["POST", "GET"])
@userlogin.not_auth()
def login():
	if request.method == "POST":
		user = userlogin.login(request.form.get("username"), request.form.get("password"))
		if not user:
			error = "User not found or password is incorrect"
			return flask.render_template("login.html", error=error)
		else:
			flask.flash("You were successfully logged in")
			response = flask.redirect(url_for("index"))
			token = userlogin.token(user, False)
			response.set_cookie('auth', value=token)
			return response
	else:
		return flask.render_template("login.html")

@app.route("/verify/<verification>/")
def verify(verification):
	ver = models.EmailVerification.query.filter_by(token=verification).first()
	if ver:
		if datetime.datetime.utcnow() < ver.expires_on:
			ver.user.emailverified = True
			try:
				db.session.delete(ver)
				db.session.commit()
				flask.flash(gettext("Your email has been verified!"))
				return flask.redirect(url_for("index"))
			except:
				db.session.rollback()
				error = gettext("Something went wrong. Please try again later")
		else:
			try:
				db.session.delete(ver)
				db.sesion.commit()
			except:
				db.rollback()
			error = gettext("That email verification token has expired. Please request a new one")
	else:
		error = gettext("That verification token doesn't exist")
	return flask.render_template("login.html", error=error)


@app.route("/register/", methods=["POST", "GET"])
@userlogin.not_auth()
def register():
	if request.method == "POST":
		username = request.form.get("username")
		password = request.form.get("password")
		email = request.form.get("email")
		verifyemail = request.form.get("verifyemail")
		verifypassword = request.form.get("verifypassword")
		reg = re.compile("^[0-9a-zA-Z_-]*$")
   		match = reg.match(username)
   		if not (username and password and email and verifyemail and verifypassword):
   			error = gettext("You must enter all required information")
   		elif not match or match.group() != username:
   			error = gettext("Username can only contain alphanumeric characters, underscores and dashes")
   		elif models.User.query.filter_by(username=username).all():
   			error = gettext("That username is already taken")
   		elif models.User.query.filter_by(email=email).all():
   			error = gettext("That email has already been used to register an account")
   		elif verifyemail != email:
   			error = gettext("Emails don't match")
   		elif verifypassword != password:
   			error = gettext("Passwords don't match")
   		elif len(username) < 3:
   			error = gettext("Username must be at least three characters long")
   		else:
   			user = models.User(username, password, email)
   			try:
   				db.session.add(user)
   				db.session.commit()
   				verif = models.EmailVerification(user.id)
   				db.session.add(verif)
   				db.session.commit()
   			except:
   				db.session.rollback()
   				return flask.render_template("register.html", error=gettext("Something went wrong, please try again later"))
   			emails.send_verification_mail(user, verif.token)
   			flask.flash(gettext("You have been successfully registered! Please check your inbox to verify your e-mail address."))
   			return flask.redirect(url_for("index"))
   		return flask.render_template("register.html", error=error)
   	return flask.render_template("register.html")

@app.route("/logout/")
def logout():
	token = flask.request.cookies.get("auth")
	ses = models.Session.query.filter_by(token=token).first()
	if ses:
		db.session.delete(ses)
		db.session.commit()
	response = flask.redirect(url_for("index"))
	flask.flash(gettext("You have been logged out"))
	response.set_cookie("auth", "", expires=0)
	return response

@app.route("/user/<int:userid>")
def user(userid):
	user = models.User.query.get(userid)
	if user and userlogin.authorise(request) == user:
		return flask.render_template("userpanel.html")
	elif user:
		return flask.render_template("user.html", user=user)
	else:
		return flask.render_template("404.html"), 404

@app.route("/admin/")
@userlogin.requires_auth(4)
def admin():
	return flask.render_template("admin panel.html")

@app.route("/resendemail/")
def resend_email():
	user = userlogin.authorise(flask.request)
	if not user:
		return flask.redirect(url_for("index"))
	for email in models.EmailVerification.query.filter_by(user=user):
		db.session.delete(email)
	verif = models.EmailVerification(user.id)
	try:
		db.session.add(verif)
		db.session.commit()
	except:
		db.session.rollback()
	emails.send_verification_mail(user, verif.token)
	flask.flash("Email resent!")
	return flask.redirect(url_for("index"))

@app.route("/reset/", methods=["GET", "POST"])
@userlogin.not_auth()
def password_reset():
	if request.method == "POST":
		userin = request.form.get("useremail")
		reg = re.compile(".+@.+\..+")
		if reg.match(userin):
			user = models.User.query.filter_by(email=userin).first()
		else:
			user = models.User.query.filter_by(username=userin).first()
		if user:
			try:
				res = models.PasswordReset(user.id)
				db.session.add(res)
				db.session.commit()
				emails.send_password_reset(user, res.token)
				flask.flash("Reset password e-mail sent!")
			except:
				db.session.rollback()
				flask.flash("Something went wrong. Please try again later")
		else:
			flask.flash("No user with that username/e-mail exists")
	return flask.render_template("send password email.html")

@app.route("/reset/<token>", methods=["GET", "POST"])
@userlogin.not_auth()
def passreset(token):
	reset = models.PasswordReset.query.filter_by(token=token).first()
	if not reset:
		flask.flash("That is not a valid password reset token")
		return flask.redirect(url_for("index"))
	if request.method == "POST":
		newp = request.form.get("newpass")
		confp = request.form.get("confpass")
		if newp != confp:
			flask.flash("Passwords do not match")
			return flask.redirect(flask.url_for('passreset', token=token), code=303)
		else:
			user = reset.user
			user.password = hashlib.sha256(newp.encode("utf-8") + user.salt.encode("utf-8")).hexdigest()
			try:
				db.session.delete(reset)
				db.session.commit()
			except:
				db.session.rollback()
				flask.flash("Something went wrong. Please try again later")
				return flask.redirect(flask.url_for('passreset', token=token), code=303)
		flask.flash(gettext("Your password has been successfully changed. You can now log in"))
		return flask.redirect(url_for('login'))
	else:
		return flask.render_template("reset password.html")

@app.route("/fourier/")
def fourier_vis():
	return flask.render_template("fourier vis.html")

if __name__ == "__main__":
	app.run("0.0.0.0", debug=True)
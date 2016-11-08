import datetime
from flaskapp import db
from sqlalchemy import DateTime, Text
from sqlalchemy.schema import ForeignKey
import random
import hashlib

class User(db.Model):
	__tablename__ = 'user'

	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(20))
	password = db.Column(db.String(64))
	salt = db.Column(db.String(64))

	email = db.Column(db.String(254))
	emailverified = db.Column(db.Boolean())
	emailverification = db.relationship('EmailVerification', backref='user')
	passwordreset = db.relationship('PasswordReset', backref='user')
	comments = db.relationship('Comment', backref='user')
	tokens = db.relationship('Session', backref='user')
	ratings = db.relationship('SongRating', backref='user')

	songs = db.relationship('Song', backref='user')
	playlists = db.relationship('Playlist', backref='user')

	permissions = db.Column(db.Integer())

	def __init__(self, username, password, email):
		self.username = username
		alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
		self.salt = ''.join(random.choice(alphabet) for i in range(64))
		self.password = hashlib.sha256(password.encode("utf-8") + self.salt.encode("utf-8")).hexdigest()
		self.email = email
		self.emailverified = False
		self.permissions = 0

class EmailVerification(db.Model):
	__tablename__ = 'emailverification'

	id = db.Column(db.Integer, primary_key=True)
	token = db.Column(db.String(10))
	expires_on = db.Column(db.DateTime, default=datetime.datetime.utcnow() + datetime.timedelta(days=7))
	created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow())
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

	def __init__(self, userid):
		self.user_id = userid
		self.token = ''.join(random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(10))

class PasswordReset(db.Model):
	__tablename__ = 'passwordreset'

	id = db.Column(db.Integer, primary_key=True)
	token = db.Column(db.String(10))
	expires_on = db.Column(db.DateTime, default=datetime.datetime.utcnow() + datetime.timedelta(days=7))
	created_on = db.Column(db.DateTime, default=datetime.datetime.utcnow())
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

	def __init__(self, userid):
		self.user_id = userid
		self.token = ''.join(random.choice("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") for i in range(10))

class Session(db.Model):
	__tablename__ = 'session'

	id = db.Column(db.Integer, primary_key=True)
	token = db.Column(db.String(24))
	expires = db.Column(db.DateTime)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

	def __init__(self, token, expires, user_id):
		self.expires = expires
		self.token = token
		self.user_id = user_id

class SongRating(db.Model):
	__tablename__ = 'songrating'

	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
	rating = db.Column(db.Float())

	def __init__(self, user_id, song_id, rating):
		self.user_id = user_id
		self.song_id = song_id
		self.rating = rating

class Song(db.Model):
	__tablename__ = 'song'

	id = db.Column(db.Integer, primary_key=True)
	colors = db.Column(db.Integer())

	title = db.Column(db.String(50))
	artist = db.Column(db.String(50))
	album = db.Column(db.String(50))
	genre = db.Column(db.String(30))
	duration = db.Column(db.Integer())

	path = db.Column(db.String(255))

	data_length = db.Column(db.Integer())
	full = db.Column(db.Boolean())
	data = db.Column(db.PickleType())
	time_per_segment = db.Column(db.Float())
	last_index = db.Column(db.Integer())
	
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	ratings = db.relationship('SongRating', backref='song')
	average_rating = db.Column(db.Float())
	comments = db.relationship('Comment', backref='song')
	views = db.Column(db.Integer)
	private = db.Column(db.Boolean())
	playlists = db.relationship('Playlist', secondary='playlistsong')
	
	featured = db.relationship('FeaturedTransform', backref='song', lazy='select', uselist=False)

	created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	expires = db.Column(db.DateTime, default=datetime.datetime.utcnow() + datetime.timedelta(days=7))

	def __init__(self, path, title, artist, album, genre, private):
		self.title = title
		self.path = path
		self.artist = artist
		self.album = album
		self.genre = genre

		self.last_index = 0
		self.colors = random.randint(0, 2)
		self.views = 0
		self.data = []
		self.average_rating = 0
		self.private = private

	def __repr__(self):
		return "<Song {} #{}>".format(self.title, self.id)

class Comment(db.Model):
	__tablename__ = 'comment'

	id = db.Column(db.Integer, primary_key=True)
	parent = db.Column(db.Integer, db.ForeignKey('comment.id'))
	children = db.relationship('Comment')
	song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	text = db.Column(db.String(300))

class FeaturedTransform(db.Model):
	__tablename__ ='featuredtransform'

	id = db.Column(db.Integer, primary_key=True)
	song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
	created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
	description = db.Column(db.Text())

	def __init__(self, song, description):
		self.song = song
		self.description = description

class Update(db.Model):
	__tablename__ = 'update'

	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(50))
	content = db.Column(db.Text())
	created = db.Column(DateTime, default=datetime.datetime.utcnow)

class Playlist(db.Model):
	__tablename__ = 'playlist'

	id = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	name = db.Column(db.String(30))
	songs = db.relationship('Song', secondary='playlistsong', order_by='playlistsong.c.order')

	def __init__(self, uid, pname):
		self.user_id = uid
		self.name = pname

class PlaylistSong(db.Model):
	__tablename__ = 'playlistsong'

	id = db.Column(db.Integer, primary_key=True)
	song_id = db.Column(db.Integer, db.ForeignKey('song.id'))
	playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.id'))
	order = db.Column(db.Integer)

	def __init__(self, sid, pid, order):
		self.song_id = sid
		self.playlist_id = pid
		self.order = order
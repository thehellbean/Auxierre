from flask.ext.mail import Message
from flaskapp import mail, app, decorators
from flask import render_template

@decorators.async
def send_async_email(app, msg):
	with app.app_context():
		mail.send(msg)

def send_email(subject, recipients, text_body, html_body):
	msg = Message(subject, recipients=recipients, sender="noreply@hellbean.com")
	msg.body = text_body
	msg.html = html_body
	send_async_email(app, msg)

def send_verification_mail(user, verification):
	send_email("Verify your email at Auxierre",
		[user.email],
		render_template("verification email.txt", user=user, verification=verification),
		render_template("verification email.html", user=user, verification=verification))

def send_password_reset(user, res):
	send_email("Reset your Auxierre password", [user.email],
		render_template("password reset email.txt", user=user, token=res),
		render_template("password reset email.html", user=user, token=res))
from __future__ import absolute_import

from celery import Celery

celeryApp = Celery('ffttask',
			broker="redis://localhost:6379/0",
			backend="redis://localhost:6379/0",
			include=['ffttask.tasks'])

if __name__ == "__main__":
	app.start()
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from flaskapp import app, db, config

app.config.from_object(config.DevelopmentConfig)

migrate = Migrate(app, db, directory="migrations")
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == "__main__":
	manager.run()
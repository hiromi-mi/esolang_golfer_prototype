import os
from flask import Flask, g
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from celery import Celery, Task

celery = Celery(__name__, broker = 'redis://localhost:6379/0')

# https://flask.palletsprojects.com/en/1.1.x/patterns/celery/
def init_celery(app=None):
    celery.conf.update(app.config)

    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(test_config=None):
    csp = {
            'default-src': '\'self\'',
            'script-src': '\'self\'',
    }

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
            SECRET_KEY='dev',
            DATABASE=os.path.join(app.instance_path, 'esolang.sqlite'),
            )
    Talisman(
            app,
            content_security_policy=csp,
            content_security_policy_nonce_in=['style-src']
            )

    if test_config is None:
        # load instance app.config
        app.config.from_pyfile('config.py', silent=False)
    else:
        app.config.from_mapping(test_config)
    import db
    db.init_app(app)

    import auth
    import submit
    import dashboard
    app.register_blueprint(auth.bp)
    app.register_blueprint(submit.bp)
    app.register_blueprint(dashboard.bp)
    app.add_url_rule('/', endpoint='index')

    csrf = CSRFProtect(app)
    init_celery(app)

    return app

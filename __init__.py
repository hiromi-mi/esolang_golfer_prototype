import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
            SECRET_KEY='dev',
            DATABASE=os.path.join(app.instance_path, 'esolang.sqlite'),
            )

    if test_config is None:
        # load instance app.config
        app.config.from_pyfile('config.py', silent=False)
    else:
        app.config.from_mapping(test_config)

    from . import db
    db.init_app(app)

    from . import auth
    from . import submit
    from . import dashboard
    app.register_blueprint(auth.bp)
    app.register_blueprint(submit.bp)
    app.register_blueprint(dashboard.bp)
    app.add_url_rule('/', endpoint='index')

    csrf = CSRFProtect(app)

    return app

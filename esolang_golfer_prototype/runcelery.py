# https://stackoverflow.com/questions/25360136/flask-with-create-app-sqlalchemy-and-celery

from app import celery, create_app

app = create_app(None)
# bind urrent application context
app.app_context().push()

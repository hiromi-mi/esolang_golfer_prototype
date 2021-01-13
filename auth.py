import functools

from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for
        )
from werkzeug.security import check_password_hash, generate_password_hash

from esolang_golfer_prototype.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')


# wrapper which require authentification
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            # TODO why auth.login not auth/login
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

# runs before the view function
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
                'SELECT * FROM user WHERE id = ?', (user_id,)
                ).fetchone()
    # save g.user as dictionary structure and can be used in base.html

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        user = db.execute('SELECT * FROM user WHERE username = ?', (username,)
                ).fetchone()

        if user is None or not check_password_hash(user['password'], password):
            error = 'Incorrect username or password.'

        if error is None:
            session.clear()
            # preserve until session across requests, signed
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        # Get error message, and shown in get_flashed_messages()
        flash(error)

    return render_template('auth/login.html')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
            # statistically
        elif db.execute(
                'SELECT id FROM user WHERE username = ?', (username, )
                ).fetchone() is not None:
            error = 'Already Registered User {}'.format(username)

        if error is None:
            db.execute('INSERT INTO user (username, password) VALUES (?, ?)',
                    (username, generate_password_hash(password))
                    )
            db.commit()
            return redirect(url_for('auth.login'))

        app.logger.error("Error: %s", error)
        flash(error)

    return render_template('auth/register.html')

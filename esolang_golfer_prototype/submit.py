from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for, config, current_app
        )
from werkzeug.exceptions import abort

from auth import login_required
from db import get_db
from judge import judge


# without prefix, you can submit noew
bp = Blueprint('submit', __name__, url_prefix='/submission')

@bp.route('/submit/<int:fieldid>', methods=('GET','POST'))
@login_required
def submitwithid(fieldid):
    if request.method == 'POST':
        return submit()
    # TODO depend on dict's adding id will be saved
    if fieldid >= 0 and fieldid < len(current_app.config['FIELDS'].keys()):
        return render_template('submission/submit.html', \
                fields=current_app.config['FIELDS'].keys(), \
                currentfield=list(current_app.config['FIELDS'].keys())[fieldid])
    else:
        return render_template('submission/submit.html', \
                fields=current_app.config['FIELDS'].keys())


@bp.route('/submit', methods=('GET', 'POST'))
@login_required
def submit():
    if request.method == 'POST':
        error = None
        fieldname = request.form['fieldname']
        sourcetext = request.form['source']
        source = sourcetext.encode()
        length = len(source)

        if not sourcetext:
            error = "Source code should not be empty."

        if length > 10000:
            error = "Source code is too longer."
        if hasattr(current_app.config['FIELDS'], fieldname) == None:
            error = f"Your language: {fieldname} is not expected: {current_app.config['FIELDS'][fieldname]}"

        if error is not None:
            flash(error)
        else:
            submission_id = judge(fieldname, sourcetext, source, length)
            return redirect(f'/submission/{submission_id}')

    return render_template('submission/submit.html',
            fields=current_app.config['FIELDS'].keys())

@bp.route('/')
@login_required
def get_submissions():
    db = get_db()
    # datetime(created, "localtime") created -> get time as localtime
    submissions = db.execute(
            'SELECT s.id, fieldname, user_id, length, username, status, datetime(created, "localtime") created'
            ' FROM submission s JOIN user u ON s.user_id = u.id'
            ' ORDER BY created DESC'
            ).fetchall()
    return render_template('submission/index.html', submissions=submissions)

@bp.route('/<int:submitid>')
@login_required
def get_submission(submitid):
    db = get_db()
    submission = db.execute(
            'SELECT fieldname, length, username, status, datetime(created, "localtime") created, source, s.user_id'
            ' FROM submission s JOIN user u ON s.user_id = u.id'
            ' WHERE s.id = ?'
            ,(submitid,)
            ).fetchone()
    results = db.execute(
            'SELECT lang, stdin, stdout, stderr'
            ' FROM result WHERE submission_id = ?'
            ,(submitid,)
            ).fetchall()

    if submission is None:
        abort(404, f"Submission {submitid} Does not exist.")

    return render_template(
            'submission/submission.html',
            currentid=submitid,
            submission=submission,
            results=enumerate(results))

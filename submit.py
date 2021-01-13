from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for
        )
from werkzeug.exceptions import abort

import os.path
import docker
import tempfile

from esolang_golfer_prototype.auth import login_required
from esolang_golfer_prototype.db import get_db

client = docker.from_env()

# without prefix, you can submit noew
bp = Blueprint('submit', __name__, url_prefix='/submission')

@bp.route('/submit', methods=('GET', 'POST'))
@login_required
def submit():
    if request.method == 'POST':
        error = None
        fieldname = request.form['field']
        source = request.form['source']
        bsource = source.encode()
        length = len(bsource)

        if not source:
            error = "Source code should not be empty."

        if length > 10000:
            error = "Source code is too longer."

        # TODO
        # if field_id
        if error is not None:
            flash(error)
        else:
            db = get_db()
            langs = db.execute(
                    'SELECT id, fieldlang'
                    ' FROM field'
                    ' WHERE fieldname = ?',
                    (fieldname,)).fetchall()

            if len(langs) == 0:
                error = "Your language is not expected"
                flash(error)
                return render_template('submission/submit.html')

            lang = langs[0]

            stdout = ""
            stderr = ""

            # TODO
            with tempfile.TemporaryDirectory(dir=os.environ["HOME"]) as tmpdir:
                # usually mkstemp's file should be removed manuall,
                # but in this case 
                # it will be removed authomatically by TemporaryDirectory()
                (fd, fpath) = tempfile.mkstemp(dir=tmpdir)
                with open(fd, "wb") as fp:
                    fp.write(bsource)
                fname = os.path.split(fpath)[-1]

                #% TODO
                volumes = {tmpdir : { 'bind': '/code', 'mode':'ro'}}

                container = client.containers.run(
                        f"esolang/{lang['fieldlang']}",
                        (lang['fieldlang'], f"/code/{fname}"),
                        detach=True,
                        volumes=volumes
                        )

                container.wait(timeout=7)
                stdout = container.logs(stdout=True, stderr=False).decode()
                stderr = container.logs(stdout=True, stderr=False).decode()
            
            status = "AC" if stdout == "Hello, World!" else "WA"

            # TODO that Should be validated:  languages
            db.execute('INSERT INTO submission'
                    '(field_id, source, stdout, stderr, status, length, user_id)'
                    'VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (lang['id'], source, stdout, stderr, status, length, g.user['id'])
                    )
            db.commit()
            return redirect(url_for('index'))

    return render_template('submission/submit.html')

@bp.route('/')
@login_required
def get_submissions():
    db = get_db()
    submissions = db.execute(
            'SELECT s.id, fieldname, length, username, status, created'
            ' FROM submission s JOIN user u ON s.user_id = u.id JOIN field f ON f.id = s.field_id'
            ' ORDER BY created DESC'
            ).fetchall()
    return render_template('submission/index.html', submissions=submissions)

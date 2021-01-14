from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for, config
        )
from werkzeug.exceptions import abort

import os.path
import docker
from docker.types import LogConfig, Ulimit
import tempfile
import time

from esolang_golfer_prototype.auth import login_required
from esolang_golfer_prototype.db import get_db

client = docker.from_env()

# without prefix, you can submit noew
bp = Blueprint('submit', __name__, url_prefix='/submission')

@bp.route('/submit/<int:fieldid>', methods=('GET',))
@login_required
def submitwithid(fieldid):
    # TODO depend on dict's adding id will be saved
    if fieldid >= 0 and fieldid < len(config.LANGS.keys()):
        return render_template('submission/submit.html', \
                fields=config.LANGS.keys(), \
                currentfield=list(config.LANGS.keys())[fieldid])
    else:
        return render_template('submission/submit.html', \
                fields=config.LANGS.keys())


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
        if hasattr(config.LANGS, fieldname) == None:
            error = f"Your language: {fieldname} is not expected: {config.LANGS[fieldname]}"

        # TODO
        if error is not None:
            flash(error)
        else:
            db = get_db()

            field = config.LANGS[fieldname]

            stdout = ""
            stderr = ""

            # TODO
            with tempfile.TemporaryDirectory(dir=os.environ["HOME"]) as tmpdir:
                # usually mkstemp's file should be removed manuall,
                # but in this case 
                # it will be removed authomatically by TemporaryDirectory()
                (fd, fpath) = tempfile.mkstemp(suffix=".bash", dir=tmpdir)
                with open(fd, "wb") as fp:
                    fp.write(source)
                fname = os.path.split(fpath)[-1]

                # input
                (fd, fpath) = tempfile.mkstemp(dir=tmpdir)
                with open(fd, "wb") as fp:
                    fp.write(b"Hello")
                inputname = os.path.split(fpath)[-1]

                #% TODO
                volumes = {tmpdir : { 'bind': '/code', 'mode':'ro'}}

                container = client.containers.run(
                        f"esolang/{field['fieldlangs'][0]}",
                        ("sh","-c", f"{field['fieldlangs'][0]} /code/{fname} < /code/{inputname}"),
                        detach=True,
                        volumes=volumes,
                        mem_limit="128m",
                        network_mode="none",
                        # ulimit, see /etc/security/limits.conf
                        # 2MB (log file will be included)
                        #ulimits=[Ulimit(name='fsize', hard=20000*1000)],
                        # cpus does not support
                        cpu_period=100000,
                        cpu_quota=50000,
                        pids_limit=20,
                        # 実際はjsonなので64KBほど
                        log_config=LogConfig(type=LogConfig.types.JSON, config={'max-size':'1m'})
                        )

                #container.wait(timeout=7)
                while range(7):
                    time.sleep(1)
                    container.reload()
                    if container.status == "exited":
                        break
                if container.status != "exited":
                    container.kill()
                stdout = container.logs(stdout=True, stderr=False)
                stderr = container.logs(stdout=False, stderr=True)
            
            status = "AC" if stdout == b"Hello, World!" else "WA"


            # TODO that Should be validated:  languages
            submission_id = db.execute('INSERT INTO submission'
                    '(fieldname, source, status, length, user_id)'
                    'VALUES (?, ?, ?, ?, ?)',
                    (fieldname, source, status, length, g.user['id'])
                    ).lastrowid
            db.execute('INSERT INTO result'
                    '(lang, stdin, stdout, stderr, exitcode, user_id, submission_id)'
                    'VALUES (?,?,?,?,?,?,?)',
                    (field["fieldlangs"][0],"", stdout, stderr, 0, g.user["id"], submission_id)
                    )
            db.commit()
            return redirect(url_for('index'))

    return render_template('submission/submit.html',
            fields=config.LANGS.keys())

@bp.route('/')
@login_required
def get_submissions():
    db = get_db()
    # datetime(created, "localtime") created -> get time as localtime
    submissions = db.execute(
            'SELECT s.id, fieldname, length, username, status, datetime(created, "localtime") created'
            ' FROM submission s JOIN user u ON s.user_id = u.id'
            ' ORDER BY created DESC'
            ).fetchall()
    return render_template('submission/index.html', submissions=submissions)

@bp.route('/<int:submitid>')
@login_required
def get_submission(submitid):
    db = get_db()
    submission = db.execute(
            'SELECT fieldname, length, username, status, datetime(created, "localtime") created, source'
            ' FROM submission s JOIN user u ON s.user_id = u.id'
            ' WHERE s.id = ?'
            ,(submitid,)
            ).fetchone()
    result = db.execute(
            'SELECT stdin, stdout, stderr'
            ' FROM result WHERE submission_id = ?'
            ,(submitid,)
            ).fetchone()

    if submission is None:
        abort(404, f"Submission {submitid} Does not exist.")

    return render_template('submission/submission.html', currentid=submitid, submission=submission, result=result)

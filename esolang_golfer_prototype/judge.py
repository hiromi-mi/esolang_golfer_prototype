from flask import config
from flask import g
from flask import current_app, app

import os.path
import docker
from docker.types import LogConfig, Ulimit
import tempfile
import time
import base64

import threading
import asyncio

from db import get_db
from app import celery

client = docker.from_env()

def judge_init(tmpdir, source, field, db, submission_id, user_id):
    (fd, fpath) = tempfile.mkstemp(suffix=".bash", dir=tmpdir)
    with open(fd, "wb") as fp:
        fp.write(source)
    fname = os.path.split(fpath)[-1]
    # input
    inputnames = []
    for testcase in current_app.config["TESTCASES"]:
        (fd, fpath) = tempfile.mkstemp(dir=tmpdir)
        with open(fd, "wb") as fp:
            fp.write(testcase[0])
        inputnames.append(os.path.split(fpath)[-1])

    volumes = {tmpdir : { 'bind': '/code', 'mode':'ro'}}

    containers = []

        #input_id, testcase in enumerate(current_app.config["TESTCASES"]):
    for input_id, inputname in enumerate(inputnames):
        for lang in field['fieldlangs']:
            containers.append((client.containers.run(
                    f"esolang/{lang}",
                    ("sh","-c", f"{lang} /code/{fname} < /code/{inputname}"),
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
                    ), input_id, lang))

    #container.wait(timeout=7)
    time.sleep(7)
        #if container.status == "exited":
    #            break

    status_bool = True
    for (container, input_id, lang) in containers:
        container.reload()
        if container.status != "exited":
            container.kill()
        stdout = container.logs(stdout=True, stderr=False)
        stderr = container.logs(stdout=False, stderr=True)

        testcase = current_app.config["TESTCASES"][input_id]

        db.execute('INSERT INTO result'
                '(lang, stdin, stdout, stderr, exitcode, user_id, submission_id)'
                'VALUES (?,?,?,?,?,?,?)',
                (lang, testcase[0], stdout, stderr, 0, user_id, submission_id)
                )
        if stdout != testcase[1]:
            status_bool = False
    return status_bool

def judge(fieldname, sourcetext, source, length):
    db = get_db()

    status = "Waiting"

    stdout = ""
    stderr = ""

    field = current_app.config["FIELDS"][fieldname]

    status = "Waiting"

    submission_id = db.execute('INSERT INTO submission'
            '(fieldname, source, status, length, user_id)'
            'VALUES (?, ?, ?, ?, ?)',
            (fieldname, source, status, length, g.user['id'])
            ).lastrowid
    db.commit()
    b64_source = base64.b64encode(source).decode("ascii")
    judge_async.delay(b64_source, field, submission_id, g.user["id"])
    return submission_id

# user_id は async においては分からないので持ち込む必要あり
@celery.task()
def judge_async(b64_source, field, submission_id, user_id):
    # due to passing bytes sequence into celery.task is not avaliable
    source = base64.b64decode(b64_source, validate=True)
    status = "Waiting"
    db = get_db()

    with tempfile.TemporaryDirectory(dir=os.environ["HOME"]) as tmpdir:
        status = "AC" if judge_init(tmpdir, source, field, db, submission_id, user_id) else "WA"

    # status = "AC" if stdout == b"Hello, World!" else "WA"
    db.execute('UPDATE submission'
            ' SET status = ? WHERE id = ?', (status, submission_id))
    db.commit()

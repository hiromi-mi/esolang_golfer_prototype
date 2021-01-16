from flask import config
from flask import g
from flask import current_app

import os.path
import docker
from docker.types import LogConfig, Ulimit
import tempfile
import time
from contextlib import ExitStack

import threading
import asyncio

client = docker.from_env()

from esolang_golfer_prototype.db import get_db

async def judge_run(testcase, source):
    with tempfile.TemporaryDirectory(dir=os.environ["HOME"]) as tmpdir:
        (fd, fpath) = tempfile.mkstemp(suffix=".bash", dir=tmpdir)
        with open(fd, "wb") as fp:
            fp.write(source)
        fname = os.path.split(fpath)[-1]
        # input
        (fd, fpath) = tempfile.mkstemp(dir=tmpdir)
        with open(fd, "wb") as fp:
            fp.write(testcase[0])
        inputname = os.path.split(fpath)[-1]

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

def judge(fieldname, sourcetext, source, length):
    db = get_db()

    status = "Waiting"

    stdout = ""
    stderr = ""

    field = current_app.config["FIELDS"][fieldname]

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

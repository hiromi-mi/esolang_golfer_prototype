from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for
        )
from esolang_golfer_prototype.db import get_db
bp = Blueprint('dashboard', __name__)

@bp.route('/')
def dashboard():
    db = get_db()
    
    fields = db.execute(
            'SELECT id, fieldname, fieldlang'
            ' FROM field').fetchall()

    field_bests = []
    # TODO N+1
    # at least one item are required
    for field in fields:
        smallest_submission = db.execute(
                'SELECT id, length'
                ' FROM submission'
                ' WHERE field_id = ?'
                " and status = 'AC'"
                ' ORDER BY length ASC',
                (field['id'],),
                ).fetchone()
        if smallest_submission is not None:
            field_bests.append(f"{field['fieldname']} : {smallest_submission['length']} Bytes")
        else:
            field_bests.append(field['fieldname'] + ": " + "No Submissions")
    return render_template('index.html', field_bests=field_bests)

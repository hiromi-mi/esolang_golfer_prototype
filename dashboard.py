from flask import (
        Blueprint, flash, g, redirect, render_template, request, session, url_for, config, current_app
        )
from db import get_db
bp = Blueprint('dashboard', __name__)

@bp.route('/')
def dashboard():
    db = get_db()
    
    field_bests = []
    # TODO N+1
    # at least one item are required
    for cnt, field in enumerate(current_app.config['FIELDS'].values()):
        smallest_submission = db.execute(
                'SELECT submission.id, length, username, user_id'
                ' FROM submission JOIN user ON user.id = submission.user_id'
                ' WHERE fieldname = ?'
                " and status = 'AC'"
                ' ORDER BY length ASC',
                (field["fieldname"],),
                ).fetchone()
        if smallest_submission is not None:
            field_bests.append((field['fieldname'], f"{smallest_submission['length']} Bytes", f"user-{smallest_submission['username']}", cnt, smallest_submission['user_id']))
        else:
            field_bests.append((field['fieldname'], "", "", cnt))
    return render_template('index.html', field_bests=field_bests)

import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    # g is for each request
    if 'db' not in g:
        g.db = sqlite3.connect(
                current_app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES
                )
        g.db.row_factory = sqlite3.Row

    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

    db.execute('INSERT INTO field'
            '(fieldname, fieldlang) VALUES (?, ?)',
            ("Transceternal", "transceternal"))
    db.execute('INSERT INTO field'
            '(fieldname, fieldlang) VALUES (?, ?)',
            ("Functional()", "functional"))
    db.commit()

@click.command('add-lang')
@click.argument('name', type=str, required=True)
@click.argument('lang', type=str, required=True)
@with_appcontext
def add_lang_command(name, lang):
    db = get_db()
    db.execute('INSERT INTO field'
            '(fieldname, fieldlang) VALUES (?, ?)',
            (name, lang))
    db.commit()
    click.echo(f'Added {name} {lang}.')

# click: CLI instance
@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(add_lang_command)

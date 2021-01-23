import pytest
from esolang_golfer_prototype.db import get_db
from flask import g, session

def test_register(client, app):
    assert client.get('/auth/register').status_code == 200
    response = client.post(
            '/auth/register', data = {'username':'a', 'password':'a','check':'a'}
            )
    assert 'http://localhost/auth/register' == response.headers['Location']

    with app.app_context():
        assert get_db().execute(
                "select * from user where username ='a'",
                ).fetchone() is None

@pytest.mark.parametrize(('username', 'password', 'message'), (
    ('', '', b'Username is required.'),
    ('a', '', b'Password is required.'),
    ('test',  'test', b'Already Registered User test'),
    ))

def test_register_validate_input(client, username, password, message):
    response = client.post(
            '/auth/register',
            data={'username':username, 'password':password}
            )
    assert message in response.data

def test_logout(client, auth):
    auth.login()

    with client:
        auth.logout()
        assert 'user_id' not in session

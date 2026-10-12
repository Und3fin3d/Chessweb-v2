from datetime import timedelta
from secrets import token_urlsafe
from time import time

from flask import current_app, g, request, session
from flask_login import LoginManager, current_user, login_user
from flask_socketio import SocketIO

from config import db
from models import GuestIdentity, LoginToken, Player


def valid_login(token):
    with db.engine.connect() as connection:
        return connection.execute(
            db.select(LoginToken.player_id).where(LoginToken.id == token, LoginToken.expires > time())
        ).scalar_one_or_none()


def load_player(token):
    player_id = valid_login(token)
    player = db.session.get(Player, player_id) if player_id is not None else None
    if player is not None:
        player.login_token = token
    return player


def start_login(player, remember=False):
    duration = current_app.config.get('REMEMBER_COOKIE_DURATION', timedelta(days=365)) if remember else current_app.permanent_session_lifetime
    seconds = duration.total_seconds() if isinstance(duration, timedelta) else duration
    token = LoginToken(id=token_urlsafe(32), player_id=player.id, expires=int(time() + seconds))
    db.session.execute(db.delete(LoginToken).where(LoginToken.expires <= time()))
    db.session.add(token)
    db.session.commit()
    player.login_token = token.id
    login_user(player, remember=remember)
    current_app.session_interface.regenerate(session)


def revoke_login():
    token = session.get('_user_id')
    if token is not None:
        db.session.execute(db.delete(LoginToken).where(LoginToken.id == token))
        db.session.commit()


def allocate_guest():
    guest = GuestIdentity()
    db.session.add(guest)
    db.session.commit()
    return -guest.id


class SessionLoginManager(LoginManager):
    def _load_user_from_remember_cookie(self, cookie):
        if hasattr(request, 'sid'):
            return None
        player = super()._load_user_from_remember_cookie(cookie)
        if player is not None:
            g.remembered_login = True
        return player


class SessionStore:
    def __init__(self, backend):
        self.backend = backend

    def __getattr__(self, name):
        return getattr(self.backend, name)

    @property
    def cache(self):
        return self.backend.cache

    @cache.setter
    def cache(self, cache):
        self.backend.cache = cache

    def save_session(self, app, state, response):
        token = state.get('_user_id')
        if token is not None and valid_login(token) is None:
            return
        self.backend.save_session(app, state, response)


class SessionSocketIO(SocketIO):
    def expire_room(self, room):
        clients = list(self.server.manager.get_participants('/', room))
        for sid, _ in clients:
            self.server.disconnect(sid, namespace='/')

    def expire_session(self, session_id):
        self.expire_room('session:' + session_id)

    def expire_login(self, token):
        if token is not None:
            self.expire_room('login:' + token)

    def _handle_event(self, handler, message, namespace, sid, *args):
        def authorised(*values):
            cookie = request.cookies.get(current_app.config['SESSION_COOKIE_NAME'])
            backend = current_app.session_interface
            expected = backend._sign(current_app, session.sid) if backend.use_signer else session.sid
            identity = current_user.is_authenticated or session.get('id') is not None
            if cookie != expected or not identity or (session.get('_user_id') and not current_user.is_authenticated):
                if message != 'connect':
                    self.emit('error', {'message': 'Session expired - please reload the page.'}, room=sid)
                return
            self.identity_handler()
            if message == 'connect':
                self.server.enter_room(sid, 'session:' + session.sid, namespace=namespace)
                if current_user.is_authenticated:
                    self.server.enter_room(sid, 'login:' + session['_user_id'], namespace=namespace)
            return handler(*values)

        return super()._handle_event(authorised, message, namespace, sid, *args)

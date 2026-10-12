from datetime import timedelta
from secrets import token_urlsafe
from threading import Lock
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
        backend = current_app.session_interface
        with backend.lock:
            backend.revoked.add(token)


def allocate_guest():
    guest = GuestIdentity()
    db.session.add(guest)
    db.session.commit()
    return -guest.id


class SessionLoginManager(LoginManager):
    def _load_user_from_remember_cookie(self, cookie):
        if hasattr(request, 'sid'):
            return None
        token = session.get('_user_id')
        player = super()._load_user_from_remember_cookie(cookie)
        if player is None:
            session['_remember'] = 'clear'
            if token is None:
                session.pop('_user_id', None)
            else:
                session['_user_id'] = token
        else:
            g.remembered_login = True
        return player


class SessionStore:
    def __init__(self, backend):
        self.backend = backend
        self.lock = Lock()
        self.retired = set()
        self.revoked = set()

    def __getattr__(self, name):
        return getattr(self.backend, name)

    @property
    def cache(self):
        return self.backend.cache

    @cache.setter
    def cache(self, cache):
        self.backend.cache = cache

    def stale(self, state):
        token = state.get('_user_id')
        return token is not None and valid_login(token) is None

    def blocked(self, state):
        return state.sid in self.retired or state.get('_user_id') in self.revoked

    def regenerate(self, state):
        with self.lock:
            sid = state.sid
            self.backend.regenerate(state)
            if state.sid != sid:
                self.retired.add(sid)

    def save_session(self, app, state, response):
        if self.stale(state):
            return
        with self.lock:
            if not self.blocked(state):
                self.backend.save_session(app, state, response)


class SessionSocketIO(SocketIO):
    def expire_room(self, room):
        with current_app.session_interface.lock:
            clients = list(self.server.manager.get_participants('/', room))
            for sid, _ in clients:
                self.server.disconnect(sid, namespace='/')

    def expire_session(self, session_id):
        self.expire_room('session:' + session_id)

    def expire_login(self, token):
        if token is not None:
            self.expire_room('login:' + token)

    def connect_session(self, handler, namespace, sid, values):
        backend = current_app.session_interface
        if backend.stale(session):
            return False
        with backend.lock:
            if backend.blocked(session):
                return False
            try:
                self.server.enter_room(sid, 'session:' + session.sid, namespace=namespace)
                if current_user.is_authenticated:
                    self.server.enter_room(sid, 'login:' + session['_user_id'], namespace=namespace)
                return handler(*values)
            except (KeyError, ValueError):
                if self.server.manager.is_connected(sid, namespace):
                    raise
                return False

    def _handle_event(self, handler, message, namespace, sid, *args):
        def authorised(*values):
            cookie = request.cookies.get(current_app.config['SESSION_COOKIE_NAME'])
            backend = current_app.session_interface
            expected = backend._sign(current_app, session.sid) if backend.use_signer else session.sid
            identity = current_user.is_authenticated or session.get('id') is not None
            if cookie != expected or not identity or backend.blocked(session) or (session.get('_user_id') and not current_user.is_authenticated):
                if message == 'connect':
                    return False
                self.server.disconnect(sid, namespace=namespace)
                return
            self.identity_handler()
            if message == 'connect':
                return self.connect_session(handler, namespace, sid, values)
            return handler(*values)

        return super()._handle_event(authorised, message, namespace, sid, *args)

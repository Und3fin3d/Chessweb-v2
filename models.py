from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from config import db
from json import dumps,loads

friendship_table = db.Table(
    'friendship',
    db.Column('user_id', db.Integer, db.ForeignKey('player.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('player.id'), primary_key=True)
)

class Player(db.Model, UserMixin):
    __tablename__ = 'player'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    rating = db.Column(db.Integer)
    wins = db.Column(db.Integer, default=0)
    losses = db.Column(db.Integer, default=0)
    draws = db.Column(db.Integer, default=0)

    friendship = db.relationship('Player',
                                 secondary=friendship_table,
                                 primaryjoin=(friendship_table.c.user_id == id),
                                 secondaryjoin=(friendship_table.c.friend_id == id),
                                 backref=db.backref('friends', lazy='dynamic'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def add_friend(self, friend):
        if not self.is_friends_with(friend):
            self.friendship.append(friend)
            friend.friendship.append(self)

    def remove_friend(self, friend):
        if self.is_friends_with(friend):
            self.friendship.remove(friend)
            friend.friendship.remove(self)

    def is_friends_with(self, user):
        return user in self.friendship

    def get_friends(self):
        return self.friends.all()
    
        

class Game(db.Model):
    __tablename__ = 'game'

    id = db.Column(db.Integer, primary_key=True)
    white_player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    black_player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    result = db.Column(db.String(50))
    fen = db.Column(db.String(255))
    moves = db.Column(db.Text)

    white_player = db.relationship('Player', foreign_keys=[white_player_id], backref='white_games')
    black_player = db.relationship('Player', foreign_keys=[black_player_id], backref='black_games')

    def add_moves(self, moves):
        self.moves = dumps(moves)
        
    def get_moves(self):
        return loads(self.moves) if self.moves else []

from flask import render_template,redirect,url_for,session,request
from flask_socketio import SocketIO, join_room, rooms
from flask_login import LoginManager,login_user,logout_user,current_user,login_required
from models import Player,Game
from static.forms import LoginForm, RegistrationForm
from chess import Board
from bug import BugBoards
from config import app,db
from time import perf_counter

boards = {}
vboards = {}
deletelist = {}
anon = [1]
socketio = SocketIO(app, manage_session=False)

with app.app_context():
    #db.drop_all() used to clear database
    db.create_all()

login = LoginManager(app)
login.login_view = 'login'
login.init_app(app)

@login.user_loader
def load_user(user_id):
    return Player.query.get(int(user_id))

@app.route('/')
def index():
    user = current_user
    if not user.is_authenticated:
        if 'id' not in session:
            session['id'] = anon[0]
            session['username'] = "Anonymous-"+str(anon[0])
            x = anon.pop()
            if len(anon) == 0:    
                anon.append(x+1)
    else:
        session['username'] = user.username
        session['_fresh'] = True
    if 'game' in session:
        if session['game'][1] in boards and session['game'][0] in boards[session['game'][1]] and boards[session['game'][1]][session['game'][0]][1] == None:
            boards[session['game'][1]].pop(session['game'][0], None)
            session.pop('game', None)
            session.pop('pieces', None)
        else:
            return redirect(url_for('game')) 
    return render_template('index.html', user=user)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Player.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            return redirect(url_for('signin'))
        anon.insert(0, session.pop('id'))
        login_user(user, remember=form.remember_me.data)
        session['username'] = form.username.data
        return redirect(url_for('index'))
    return render_template('login.html',  title='Sign In', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = Player(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        anon.insert(0, session.pop('id'))
        login_user(user, remember=False)
        session['username'] = form.username.data
        return redirect(url_for('index'))
    return render_template('register.html', title='Register', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/game')
def game():
    if 'game' in session and session['game'][1] in boards and session['game'][0] in boards[session['game'][1]]:
        return render_template('game.html')
    return redirect(url_for('index'))

@socketio.on('connect')
def handle_connect():
    user = current_user
    if user.is_authenticated:
        join_room(user.id)

@socketio.on('home')
def home():
    if 'game' in session:
        boards[session['game'][1]].pop(session['game'][0], None)
        session.pop('game', None)
        session.pop('pieces', None) 
    socketio.emit('redirect', url_for('index'), room = request.sid)

@socketio.on('over')
def over():
    user = current_user
    if 'game' in session:
        boards[session['game'][1]].pop(session['game'][0], None)
    if user.is_authenticated:
        join_room(user.id)

@socketio.on('pair')
def pair(request):
    time = request['data'][0]
    increment = request['data'][1]
    session['increment'] = increment
    def create_board(authenticated):
        games = Game.query.count() + 1 + sum(len(boards[x]) for x in boards)
        user_id = current_user.id if authenticated else session['id']
        boards.setdefault(time, {})[games] = [authenticated, None, user_id, None, session['username'], time*60, time*60, increment, Board()]
        session['game'] = [games, time]
        session['pieces'] = False
        join_room('waiting' + str(games))

    if 'game' in session:
        if session['game'][1] in boards and session['game'][0] in boards[session['game'][1]]:
            boards[session['game'][1]].pop(session['game'][0], None)
        session.pop('game', None)
    if time in boards:
        match = [x for x in boards[time] if boards[time][x][:2] == [current_user.is_authenticated, None] and boards[time][x][7]==increment]
        if match:
            y = boards[time][match[0]]
            y[1] = current_user.id if current_user.is_authenticated else session['id']
            y[3] = session['username']
            session['game'] = [match[0], time]
            session['pieces'] = True
            join_room('waiting' + str(match[0]))
            socketio.emit('redirect', url_for('game'), room='waiting' + str(match[0]))
        else:
            create_board(current_user.is_authenticated)
    else:
        create_board(current_user.is_authenticated)

@socketio.on('bugmatch')
def bugmatch(request):
    time = request['data'][0]
    increment = request['data'][1]
    session['increment'] = increment
    
    def create_board(authenticated):
        games = Game.query.count() + 1 + sum(len(boards[x]) for x in boards)
        user_id = current_user.id if authenticated else session['id']
        boards.setdefault(time, {})[games] = [authenticated, [user_id], [session['username']],[], [time*60,time*60], [time*60,time*60], increment, BugBoards()]
        session['game'] = [games, time]
        session['pieces'] = False
        join_room('waiting' + str(games))
        
    if 'game' in session:
        if session['game'][1] in boards and session['game'][0] in boards[session['game'][1]]:
            boards[session['game'][1]].pop(session['game'][0], None)
        session.pop('game', None)
    if time in vboards.setdefault('bug', {}):
        match = [x for x in boards[time] if boards[time][x][0] == current_user.is_authenticated and len(boards[time][x][0]) < 4 and boards[time][x][6]==increment]
        if match:
            y = boards[time][match[0]]
            y[0] += [current_user.id] if current_user.is_authenticated else [session['id']]
            pw = len(y[0])
            #2 -> 1  3->0 4->1
            y[pw//3 + 2].append(session['username'])
            session['game'] = [match[0], time]
            session['pieces'] = pw%2==0
            join_room('waiting' + str(match[0]))
            if pw==4:
                socketio.emit('redirect', url_for('game'), room='waiting' + str(match[0]))
        else:
            create_board(current_user.is_authenticated)
    else:
        create_board(current_user.is_authenticated)


@socketio.on('move')
def update(request):
    move = request['data']
    b = boards[session['game'][1]][session['game'][0]]
    game = b[8]
    
    if move == "initiation":
        join_room('game'+str(session['game']))
        socketio.emit('names', {'black': boards[session['game'][1]][session['game'][0]][3], 'white': boards[session['game'][1]][session['game'][0]][4]}, room='game'+str(session['game']))
        b.append(perf_counter())
    else:
        time = b[5] if game.wmove else b[6]
        t = perf_counter()-b[-1]
        time -= t - b[7]
        if game.wmove:
            b[5] = time
        else:
            b[6] = time
    game.play(move)
    
    legal = game.legalmoves()
    if game.active:
        socketio.emit('update',{'moves':legal,'board':game.grid(),'square':move[2:],'checks':game.incheck(),'white': int(b[5]),'black': int(b[6]),'move':game.wmove},room= 'game'+str(session['game']))
        b[-1] = perf_counter()
    else:
        if game.result:
            l = "White wins by checkmate"
        elif game.result is None:
            l = "Draw"
        else:
            l = "Black wins by checkmate"
        socketio.emit('update',{'moves':[],'board':game.grid(),'square':'','white': '','black': l,'checks':game.incheck(),'move':game.wmove},room= 'game'+str(session['game']))
        socketio.emit('over',room= 'game'+str(session['game']))
        if current_user.is_authenticated:
            white_player = db.session.query(Player).get(b[2])
            black_player = db.session.query(Player).get(b[1])
            if game.result is True:
                white_player.wins += 1
                black_player.losses += 1
            elif game.result is False:
                black_player.wins += 1
                white_player.losses += 1
            else:
                white_player.draws += 1
                black_player.draws += 1
            new_game = Game(white_player=white_player, black_player=black_player, result=game.result, fen=game.FEN)
            new_game.add_moves(game.moves)
            db.session.add(new_game)
            db.session.commit()

@socketio.on('timeout')
def timeout():
    b = boards[session['game'][1]][session['game'][0]]
    t = perf_counter()-b[-1]
    game = b[8] 
    time = b[5] if game.wmove else b[6]
    time-=t
    if time <= 0:
        l = "Black won on time" if game.wmove else "White won on time"
        socketio.emit('update',{'moves':[],'board':game.grid(),'square':'','white': '','black': l,'move':game.wmove},room= 'game'+str(session['game']))
        socketio.emit('over',room= 'game'+str(session['game']))   
        if current_user.is_authenticated:
            white_player = db.session.query(Player).get(b[2])
            black_player = db.session.query(Player).get(b[1])
            new_game = Game(white_player=white_player, black_player=black_player, result=l, fen=game.FEN)
            new_game.add_moves(game.moves)
            db.session.add(new_game)
            db.session.commit()
        boards[session['game'][1]].pop(session['game'][0], None)

    else:
        socketio.emit('update',{'moves':game.legalmoves(),'board':game.grid(),'square':'','checks':game.incheck(),'white': int(b[5]),'black': int(b[6]),'move':game.wmove},room= 'game'+str(session['game']))    
        
@socketio.on('addFriend')
def add_friend(friend_username):
    user = current_user
    if user.is_authenticated:
        friend = Player.query.filter_by(username=friend_username).first()
        if friend and friend != user:
            user.add_friend(friend)
            db.session.commit()
            socketio.emit('friendAdded', {'friend': friend.username})
        else:
            socketio.emit('error', {'message': 'Invalid username or cannot add yourself as a friend.'})
    else:
        socketio.emit('error', {'message': 'You must be logged in to add friends.'})        

@socketio.on('getFriendList')
def get_friend_list():
    user = current_user
    if user.is_authenticated:
        friends = user.get_friends()
        socketio.emit('friendList', {'friends': [{'username': friend.username} for friend in friends]}, room=request.sid)
    else:
        socketio.emit('friendList', {'friends': []}, room=request.sid)
@socketio.on('challengePair')
def challenge_pair():
    games = [x for x in boards['challenge'] if boards['challenge'][x][1] == current_user.id][0]
    session['game'] = [games, 'challenge']
    session['pieces'] = True
    session['friend'] = boards['challenge'][games][4]
    socketio.emit('redirect', url_for('game'), room=request.sid)

@socketio.on('challengeFriend')
def challenge_friend(friend_username):
    user = current_user
    if user.is_authenticated:
        friend = Player.query.filter_by(username=friend_username).first()
        games = Game.query.count() + 1 + sum(len(boards[x]) for x in boards)
        boards.setdefault('challenge', {})[games] = [True,friend.id, user.id,friend_username, session['username'],600,600,0, Board()]
        session['game'] = [games, 'challenge']
        session['pieces'] = False
        session['friend'] = friend_username
        socketio.emit('redirect', url_for('game'), room=request.sid)
        socketio.emit('challenge', room=friend.id)
    
@socketio.on('challengeAgain')
def challenge_again():
    user = current_user
    friend_username = session['friend']
    games = Game.query.count() + 1 + sum(len(boards[x]) for x in boards)
    friend = Player.query.filter_by(username=friend_username).first()
    boards.setdefault('challenge', {})[games] = [True,friend.id, user.id,friend_username, session['username'],600,600,0, Board()]
    socketio.emit('redirect', url_for('game'), room=request.sid)
    socketio.emit('challenge', room=friend.id)
    session['game'] = [games, 'challenge']
    session['pieces'] = False
    

if __name__ == "__main__":
    socketio.run(app ,port=6500, debug=True)
    #socketio.run(app,host='0.0.0.0',port=6500, debug=True) 
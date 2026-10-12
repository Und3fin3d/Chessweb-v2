from flask import render_template, redirect, url_for, session, request
from flask_socketio import SocketIO, join_room, close_room
from flask_login import LoginManager, login_user, logout_user, current_user
from models import Player, Game
from static.forms import LoginForm, RegistrationForm
from chess import Board
from bug import BugBoards
from config import app, db
from time import perf_counter
import os,glob

boards = {}
boards['custom'] = {}  # Store custom position games
bug_games = {}
anon = [1]
activeg = [0]
socketio = SocketIO(app, manage_session=False)

BUG_SEATS = [
    {'team': 0, 'board': 0, 'colour': 'white'},
    {'team': 0, 'board': 1, 'colour': 'black'},
    {'team': 1, 'board': 0, 'colour': 'black'},
    {'team': 1, 'board': 1, 'colour': 'white'}
]

with app.app_context():
    db.create_all()

login = LoginManager(app)
login.login_view = 'login'
login.init_app(app)


def player_identifier():
    if current_user.is_authenticated:
        return f'user-{current_user.id}'
    return f'anon-{session.get("id")}'


def total_active_games():
    bug_total = sum(len(bucket) for bucket in bug_games.values())
    return sum(len(boards[x]) for x in boards) + bug_total


def next_game_id():
    return Game.query.count() + 1 + total_active_games()


def cleanup_standard_session():
    game = session.get('game')
    if not game:
        return
    time_key = game[1]
    game_id = game[0]
    if time_key == 'custom':
        # Custom games cleanup is handled separately
        if 'custom' in boards and game_id in boards['custom']:
            boards['custom'].pop(game_id, None)
        return
    if time_key in boards and game_id in boards[time_key]:
        boards[time_key].pop(game_id, None)
        if not boards[time_key]:
            boards.pop(time_key, None)


def cleanup_bug_session():
    if session.get('variant') != 'bughouse' or 'game' not in session:
        return
    key = (session['game'][1], session.get('increment', 0))
    game_id = session['game'][0]
    bucket = bug_games.get(key)
    if bucket and game_id in bucket:
        bucket.pop(game_id, None)
        if not bucket:
            bug_games.pop(key, None)


def reset_session_flags():
    for key in ['game', 'pieces', 'increment', 'variant', 'bug_board', 'bug_colour', 'bug_team', 'friend']:
        session.pop(key, None)


def bug_bucket_key():
    if 'game' not in session:
        return None
    return (session['game'][1], session.get('increment', 0))


def get_bug_game():
    if session.get('variant') != 'bughouse':
        return None, None, None
    key = bug_bucket_key()
    if not key:
        return None, None, None
    bucket = bug_games.get(key)
    if not bucket:
        return None, None, None
    game_id = session['game'][0]
    return bucket.get(game_id), bucket, key


def bug_room_name(game_id, key):
    return f'buggame-{key[0]}-{key[1]}-{game_id}'


def bug_state_payload(game_data):
    payload = {
        'boards': game_data['game'].grid(),
        'legal': game_data['game'].legalmoves(),
        'pools': game_data['game'].pools(),
        'checks': game_data['game'].checks(),
        'turns': [board.wmove for board in game_data['game'].boards],
        'timers': [
            {'white': int(game_data['timers'][0]['white']), 'black': int(game_data['timers'][0]['black'])},
            {'white': int(game_data['timers'][1]['white']), 'black': int(game_data['timers'][1]['black'])}
        ],
        'names': game_data.get('names', []),
        'lastMove': game_data['game'].last_moves(),
        'active': game_data['game'].active,
        'teams': game_data.get('teams', {})
    }
    return payload


@login.user_loader
def load_user(user_id):
    return Player.query.get(int(user_id))


@app.route('/')
def index():
    user = current_user
    if not user.is_authenticated:
        if 'id' not in session:
            session['id'] = anon[0]
            session['username'] = f"Anonymous-{anon[0]}"
            x = anon.pop()
            if len(anon) == 0:
                anon.append(x + 1)
    else:
        session['username'] = user.username
        session['_fresh'] = True

    if 'game' in session:
        variant = session.get('variant', 'classic')
        if variant == 'bughouse':
            key = bug_bucket_key()
            bucket = bug_games.get(key, {}) if key else {}
            stored = bucket.get(session['game'][0]) if bucket else None
            if stored and stored.get('ready'):
                return redirect(url_for('game'))
            cleanup_bug_session()
            reset_session_flags()
        else:
            time_key = session['game'][1]
            game_id = session['game'][0]
            if time_key in boards and game_id in boards[time_key]:
                if boards[time_key][game_id][1] is None:
                    cleanup_standard_session()
                    reset_session_flags()
                else:
                    return redirect(url_for('game'))
            else:
                reset_session_flags()

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
    return render_template('login.html', title='Sign In', form=form)


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
    reset_session_flags()
    return redirect(url_for('index'))


@app.route('/game')
def game():
    if 'game' not in session:
        return redirect(url_for('index'))
    variant = session.get('variant', 'classic')
    if variant == 'bughouse':
        key = bug_bucket_key()
        bucket = bug_games.get(key) if key else None
        if bucket and session['game'][0] in bucket and bucket[session['game'][0]].get('ready'):
            return render_template('game.html', variant='bughouse')
        return redirect(url_for('index'))
    time_key = session['game'][1]
    # Support custom games
    if time_key == 'custom':
        if session['game'][0] in boards['custom']:
            return render_template('game.html', variant='classic')
        return redirect(url_for('index'))
    if time_key in boards and session['game'][0] in boards[time_key]:
        return render_template('game.html', variant='classic')
    return redirect(url_for('index'))
@app.route('/bgame')
def bgame():
    if 'game' in session and session['game'][1] in bboards and session['game'][0] in bboards[session['game'][1]]:
        return render_template('bgame.html')
    return redirect(url_for('index'))


@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(current_user.id)


@socketio.on('home')
def home():
    if session.get('variant') == 'bughouse':
        cleanup_bug_session()
    elif 'game' in session:
        room = 'game' + str(session['game'])
        current = get_game_data()
        if current and current[8].active:
            socketio.emit('over', {'message': 'A player left the game.'}, room=room, skip_sid=request.sid)
        close_room(room)
        cleanup_standard_session()
    reset_session_flags()
    socketio.emit('redirect', url_for('index'), room=request.sid)


@socketio.on('over')
def over():
    if session.get('variant') == 'bughouse':
        cleanup_bug_session()
    else:
        cleanup_standard_session()
    reset_session_flags()
    if current_user.is_authenticated:
        join_room(current_user.id)


@socketio.on('pair')
def pair(request_payload):
    time_selection = request_payload['data'][0]
    increment = request_payload['data'][1]
    session['increment'] = increment

    def create_board(authenticated):
        games = next_game_id()
        user_id = current_user.id if authenticated else session['id']
        boards.setdefault(time_selection, {})[games] = [
            authenticated,
            None,
            user_id,
            None,
            session['username'],
            time_selection * 60,
            time_selection * 60,
            increment,
            Board()
        ]
        session['game'] = [games, time_selection]
        session['pieces'] = False
        session['variant'] = 'classic'
        join_room('waiting' + str(games))

    if 'game' in session:
        cleanup_standard_session()
        reset_session_flags()
    if time_selection in boards:
        match = [
            x for x in boards[time_selection]
            if boards[time_selection][x][:2] == [current_user.is_authenticated, None]
            and boards[time_selection][x][7] == increment
        ]
        if match:
            y = boards[time_selection][match[0]]
            y[1] = current_user.id if current_user.is_authenticated else session['id']
            y[3] = session['username']
            session['game'] = [match[0], time_selection]
            session['pieces'] = True
            session['variant'] = 'classic'
            join_room('waiting' + str(match[0]))
            socketio.emit('redirect', url_for('game'), room='waiting' + str(match[0]))
        else:
            create_board(current_user.is_authenticated)
    else:
        create_board(current_user.is_authenticated)


@socketio.on('bugmatch')
def bugmatch(request_payload):
    time_selection = request_payload['data'][0]
    increment = request_payload['data'][1]
    session['increment'] = increment
    session['variant'] = 'bughouse'

    if 'game' in session and session.get('variant') == 'bughouse':
        cleanup_bug_session()
        reset_session_flags()
        session['variant'] = 'bughouse'
    elif 'game' in session:
        cleanup_standard_session()
        reset_session_flags()
        session['variant'] = 'bughouse'

    bucket_key = (time_selection, increment)
    bucket = bug_games.setdefault(bucket_key, {})
    available_game_id = next((gid for gid, data in bucket.items() if len(data['seats']) < 4), None)

    if available_game_id is None:
        game_id = next_game_id()
        bucket[game_id] = {
            'seats': [],
            'seat_lookup': {},
            'game': BugBoards(),
            'timers': [
                {'white': time_selection * 60, 'black': time_selection * 60},
                {'white': time_selection * 60, 'black': time_selection * 60}
            ],
            'last_move': [perf_counter(), perf_counter()],
            'increment': increment,
            'ready': False,
            'names': [
                {'white': None, 'black': None},
                {'white': None, 'black': None}
            ],
            'teams': {0: [], 1: []}
        }
    else:
        game_id = available_game_id

    game_data = bucket[game_id]
    seat_index = len(game_data['seats'])
    if seat_index >= 4:
        socketio.emit('error', {'message': 'Game already full.'}, room=request.sid)
        return

    seat_blueprint = BUG_SEATS[seat_index]
    player_key = player_identifier()
    seat_payload = {
        'player_key': player_key,
        'username': session['username'],
        'authenticated': current_user.is_authenticated,
        'db_id': current_user.id if current_user.is_authenticated else None,
        'seat': seat_blueprint
    }
    game_data['seats'].append(seat_payload)
    game_data['seat_lookup'][player_key] = seat_index
    game_data['teams'][seat_blueprint['team']].append(session['username'])

    session['game'] = [game_id, time_selection]
    session['pieces'] = seat_blueprint['colour'] == 'black'
    session['bug_board'] = seat_blueprint['board']
    session['bug_colour'] = seat_blueprint['colour']
    session['bug_team'] = seat_blueprint['team']

    waiting_room = f'bugwait-{time_selection}-{increment}-{game_id}'
    join_room(waiting_room)

    if len(game_data['seats']) == 4:
        game_data['ready'] = True
        game_data['last_move'] = [perf_counter(), perf_counter()]
        board_names = [{'white': None, 'black': None}, {'white': None, 'black': None}]
        for seat in game_data['seats']:
            board_idx = seat['seat']['board']
            colour = seat['seat']['colour']
            board_names[board_idx][colour] = seat['username']
        game_data['names'] = board_names
        socketio.emit('redirect', url_for('game'), room=waiting_room)


def get_game_data():
    """Get current game data from session, supporting both standard and custom games."""
    time_key = session['game'][1]
    game_id = session['game'][0]
    if time_key == 'custom':
        return boards['custom'].get(game_id)
    return boards[time_key].get(game_id) if time_key in boards else None


@socketio.on('move')
def update(request_payload):
    if session.get('variant') == 'bughouse':
        return
    move = request_payload['data']
    current = get_game_data()
    if not current:
        return
    game = current[8]

    if move == "initiation":
        join_room('game' + str(session['game']))
        socketio.emit('names', {
            'black': current[3],
            'white': current[4]
        }, room='game' + str(session['game']))
        current.append(perf_counter())
        return

    time_bank = current[5] if game.wmove else current[6]
    elapsed = perf_counter() - current[-1]
    time_bank -= elapsed - current[7]
    if game.wmove:
        current[5] = time_bank
    else:
        current[6] = time_bank

    game.play(move)
    legal = game.legalmoves()
    room_name = 'game' + str(session['game'])

    if game.active:
        socketio.emit('update', {
            'moves': legal,
            'board': game.grid(),
            'square': move[2:],
            'checks': game.incheck(),
            'white': int(current[5]),
            'black': int(current[6]),
            'move': game.wmove
        }, room=room_name)
        current[-1] = perf_counter()
    else:
        if game.result:
            label = "White wins by checkmate"
        elif game.result is None:
            label = "Draw"
        else:
            label = "Black wins by checkmate"
        socketio.emit('update', {
            'moves': [],
            'board': game.grid(),
            'square': '',
            'white': '',
            'black': label,
            'checks': game.incheck(),
            'move': game.wmove
        }, room=room_name)
        socketio.emit('over', room=room_name)
        close_room(room_name)
        if current_user.is_authenticated:
            white_player = db.session.query(Player).get(current[2])
            black_player = db.session.query(Player).get(current[1])
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
    if session.get('variant') == 'bughouse':
        return
    current = get_game_data()
    if not current:
        return
    elapsed = perf_counter() - current[-1]
    game = current[8]
    clock = current[5] if game.wmove else current[6]
    clock -= elapsed
    room_name = 'game' + str(session['game'])
    if clock <= 0:
        label = "Black won on time" if game.wmove else "White won on time"
        socketio.emit('update', {
            'moves': [],
            'board': game.grid(),
            'square': '',
            'white': '',
            'black': label,
            'move': game.wmove
        }, room=room_name)
        socketio.emit('over', room=room_name)
        close_room(room_name)
        if current_user.is_authenticated:
            white_player = db.session.query(Player).get(current[2])
            black_player = db.session.query(Player).get(current[1])
            new_game = Game(white_player=white_player, black_player=black_player, result=label, fen=game.FEN)
            new_game.add_moves(game.moves)
            db.session.add(new_game)
            db.session.commit()
        # Clean up session based on game type
        if session['game'][1] == 'custom':
            game_id = session['game'][0]
            if game_id in boards['custom']:
                boards['custom'].pop(game_id, None)
        else:
            cleanup_standard_session()
    else:
        if game.wmove:
            current[5] = clock
        else:
            current[6] = clock
        socketio.emit('update', {
            'moves': game.legalmoves(),
            'board': game.grid(),
            'square': '',
            'checks': game.incheck(),
            'white': int(current[5]),
            'black': int(current[6]),
            'move': game.wmove
        }, room=room_name)


@socketio.on('bug_initiate')
def bug_initiate():
    game_data, bucket, key = get_bug_game()
    if not game_data or not game_data.get('ready'):
        return
    join_room(bug_room_name(session['game'][0], key))
    socketio.emit('bug_state', bug_state_payload(game_data), room=request.sid)


@socketio.on('bugmove')
def bugmove(request_payload):
    game_data, bucket, key = get_bug_game()
    game_id = session['game'][0] if 'game' in session else None
    if not game_data or not game_data.get('ready'):
        return
    move = request_payload['data'].get('move')
    board_index = request_payload['data'].get('board')
    if game_id is None:
        return
    if move is None or board_index not in [0, 1]:
        return
    board = game_data['game'].boards[board_index]
    mover = 'white' if board.wmove else 'black'
    prev_len = len(board.moves)
    game_data['game'].play(move, board_index)
    if len(board.moves) == prev_len:
        return
    elapsed = perf_counter() - game_data['last_move'][board_index]
    timer_value = game_data['timers'][board_index][mover] - elapsed + game_data['increment']
    game_data['timers'][board_index][mover] = max(0, timer_value)
    game_data['last_move'][board_index] = perf_counter()
    room_name = bug_room_name(game_id, key)
    socketio.emit('bug_state', bug_state_payload(game_data), room=room_name)

    if not game_data['game'].active:
        conclude_bug_game(session['game'][0], game_data, bucket, key, board_index, reason='checkmate')


def conclude_bug_game(game_id, game_data, bucket, key, board_index, reason):
    losing_board = game_data['game'].boards[board_index]
    if reason == 'checkmate':
        result = losing_board.result
        if result is True:
            winning_colour = 'white'
        elif result is False:
            winning_colour = 'black'
        else:
            winning_colour = None
    else:
        winning_colour = 'black' if reason == 'time_white' else 'white'

    winning_team = None
    if winning_colour:
        for seat in game_data['seats']:
            if seat['seat']['board'] == board_index and seat['seat']['colour'] == winning_colour:
                winning_team = seat['seat']['team']
                break
    team_names = game_data.get('teams', {})
    winners = ', '.join(team_names.get(winning_team, [])) if winning_team is not None else 'Team'
    message = f"{winners} win by {'checkmate' if reason == 'checkmate' else 'time'}"
    room_name = bug_room_name(game_id, key)
    socketio.emit('bug_over', {'message': message}, room=room_name)
    bucket.pop(game_id, None)
    if not bucket:
        bug_games.pop(key, None)


@socketio.on('bug_timeout')
def bug_timeout(request_payload):
    game_data, bucket, key = get_bug_game()
    game_id = session['game'][0] if 'game' in session else None
    if not game_data or game_id is None:
        return
    board_index = request_payload.get('board')
    colour = request_payload.get('colour')
    if board_index not in [0, 1] or colour not in ['white', 'black']:
        return
    elapsed = perf_counter() - game_data['last_move'][board_index]
    game_data['timers'][board_index][colour] -= elapsed
    if game_data['timers'][board_index][colour] <= 0:
        reason = 'time_white' if colour == 'white' else 'time_black'
        conclude_bug_game(session['game'][0], game_data, bucket, key, board_index, reason=reason)
    else:
        game_data['last_move'][board_index] = perf_counter()
        room_name = bug_room_name(game_id, key)
        socketio.emit('bug_state', bug_state_payload(game_data), room=room_name)


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
    session['variant'] = 'classic'
    session['friend'] = boards['challenge'][games][4]
    socketio.emit('redirect', url_for('game'), room=request.sid)


@socketio.on('challengeFriend')
def challenge_friend(friend_username):
    user = current_user
    if user.is_authenticated:
        friend = Player.query.filter_by(username=friend_username).first()
        games = next_game_id()
        boards.setdefault('challenge', {})[games] = [True, friend.id, user.id, friend_username, session['username'], 600, 600, 0, Board()]
        session['game'] = [games, 'challenge']
        session['pieces'] = False
        session['variant'] = 'classic'
        session['friend'] = friend_username
        socketio.emit('redirect', url_for('game'), room=request.sid)
        socketio.emit('challenge', room=friend.id)


@socketio.on('challengeAgain')
def challenge_again():
    user = current_user
    friend_username = session['friend']
    games = next_game_id()
    friend = Player.query.filter_by(username=friend_username).first()
    boards.setdefault('challenge', {})[games] = [True, friend.id, user.id, friend_username, session['username'], 600, 600, 0, Board()]
    socketio.emit('redirect', url_for('game'), room=request.sid)
    socketio.emit('challenge', room=friend.id)
    session['game'] = [games, 'challenge']
    session['pieces'] = False
    session['variant'] = 'classic'


# Custom board game socket events
@socketio.on('createCustomGame')
def create_custom_game(request_payload):
    """Create a new custom game with a specific FEN position and time control."""
    fen = request_payload.get('fen')
    time_control = request_payload.get('time', 10)  # Default 10 minutes
    increment = request_payload.get('increment', 0)
    
    if not fen:
        socketio.emit('error', {'message': 'No FEN position provided.'}, room=request.sid)
        return
    
    try:
        # Validate FEN by trying to create a board with it
        test_board = Board(fen)
    except Exception as e:
        socketio.emit('error', {'message': f'Invalid FEN position: {str(e)}'}, room=request.sid)
        return
    
    game_id = next_game_id()
    user_id = current_user.id if current_user.is_authenticated else session['id']
    
    # Store custom game: [authenticated, player2_id, player1_id, player2_name, player1_name, white_time, black_time, increment, board, fen, status]
    boards['custom'][game_id] = [
        current_user.is_authenticated,
        None,  # player 2 (opponent) - not joined yet
        user_id,  # player 1 (creator)
        None,  # player 2 name
        session['username'],  # creator name
        time_control * 60,  # white time in seconds
        time_control * 60,  # black time in seconds
        increment,
        Board(fen),  # board with custom position
        fen,  # store the FEN
        'waiting'  # status: waiting, active, completed
    ]
    
    socketio.emit('customGameCreated', {'gameId': game_id}, room=request.sid)


@socketio.on('listCustomGames')
def list_custom_games():
    """Return all available custom games waiting for players."""
    available_games = []
    
    for game_id, game_data in boards['custom'].items():
        # Only show games that are waiting for opponent (player2 is None)
        if game_data[1] is None and game_data[10] == 'waiting':
            # Determine if it's a standard position
            fen = game_data[9]
            is_standard = fen == 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
            
            available_games.append({
                'id': game_id,
                'creator': game_data[4],
                'time': game_data[5] // 60,  # Convert seconds back to minutes
                'increment': game_data[7],
                'fen': fen[:50] + '...' if len(fen) > 50 else fen,  # Truncated FEN preview
                'isStandard': is_standard,
                'authenticated': game_data[0]
            })
    
    socketio.emit('customGamesList', {'games': available_games}, room=request.sid)


@socketio.on('joinCustomGame')
def join_custom_game(request_payload):
    """Join an existing custom game."""
    game_id = request_payload.get('gameId')
    
    if game_id not in boards['custom']:
        socketio.emit('error', {'message': 'Game not found.'}, room=request.sid)
        return
    
    game_data = boards['custom'][game_id]
    
    # Check if game is still waiting
    if game_data[10] != 'waiting':
        socketio.emit('error', {'message': 'Game is no longer available.'}, room=request.sid)
        return
    
    # Check if player is trying to join their own game
    creator_id = game_data[2]
    current_id = current_user.id if current_user.is_authenticated else session['id']
    
    if creator_id == current_id:
        socketio.emit('error', {'message': 'Cannot join your own game.'}, room=request.sid)
        return
    
    # Add player 2 to the game
    game_data[1] = current_id
    game_data[3] = session['username']
    game_data[10] = 'active'
    
    # Set up session for the joining player
    session['game'] = [game_id, 'custom']
    session['pieces'] = True  # Player 2 gets black pieces
    session['variant'] = 'classic'
    
    # Notify both players
    room_name = f'customgame-{game_id}'
    join_room(room_name)
    socketio.emit('redirect', url_for('game'), room=request.sid)
    
    # Also redirect the creator if they're still waiting
    creator_room = f'waiting-custom-{game_id}'
    socketio.emit('redirect', url_for('game'), room=creator_room)


if __name__ == "__main__":
    socketio.run(app, port=6500, debug=True)

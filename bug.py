#we need to know when captures have been made
#we need to be able to place
from chess import *


class Board(Board):
    def __init__(self,FEN='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 -'):
        self.K = (None,None)
        self.k = (None,None)
        self.FEN = FEN
        self.board,self.wmove, self.wcast, self.bcast,self.ep,self.fifty, self.movenum,self.pool = self.loadFEN(FEN)
        print(self.pool,self.movenum)
        self.moves = []
        self.otpool = []
        self.result = None
        self.prom = []
        self.legal = []
        self.active = True
        self.isActive()
    def loadFEN(self, FEN):
        grid = [[Square(f'{chr(97+x)}{y+1}') for x in range(8)] for y in range(8)]
        FEN = split('[/ ]', FEN)
        gamestate = FEN[8:]
        castle1 = [True if x in ['k', 'q'] else False for x in gamestate[1][:2].lower()]
        castle2 = [True if x in ['k', 'q'] else False for x in gamestate[1][2:].lower()]
        b = FEN[:8]
        b.reverse()
        buffer = 0
        for y,row in enumerate(b):
            for x,sq in enumerate(row):
                if sq.isdigit():
                    buffer += int(sq)-1
                else:
                    grid[y][x+buffer].movein(self.pclass(sq,x+buffer,y))
            buffer = 0
        return grid,gamestate[0]=='w', castle1, castle2,gamestate[2],gamestate[3],gamestate[-2],[x for x in gamestate[-1] if x != '-']
    def isCapture(self,move):
        return self.board[move[2]][move[3]].occupied
    def place(self,p,x,y):
        x2, y2 = (self.K if self.wmove else self.k)
        print(self.pool)
        if not(p.lower()=='p' and y in [0,7]) and not self.board[y][x].occupied:
            if not self.board[y2][x2].piece.check():
                self.board[y][x].movein(self.pclass(p,x,y))
                self.pool.remove(p)
                self.wmove = not self.wmove
                self.ep = '-'
                self.prom = [] 
            else:
                old = deepcopy(self.board)
                self.board[y][x].movein(self.pclass(p,x,y))
                if not self.board[y2][x2].piece.check():
                    self.pool.remove(p)
                    self.wmove = not self.wmove
                    self.ep = '-'
                    self.prom = [] 
                else:
                    self.board = deepcopy(old)
                    
    def play(self,move):
        if self.active:
            if move in self.legal:
                if move[0]!='O':
                    move = [int(move[1])-1,ord(move[0])-97,int(move[3])-1,ord(move[2])-97]
                    if self.isCapture(move):
                        print('capture')
                        self.otpool.append(self.board[move[2]][move[3]].piece.name())
                self.playraw(move)
                self.wmove = not self.wmove
                self.ep = '-'
                self.prom = []  
                if type(move)==list and self.board[move[2]][move[3]].piece.name().lower()=='p' and abs(move[2]-move[0])==2:
                    dir = 1 if self.wmove else -1
                    self.ep = (move[2]+dir,move[3])   
                self.moves.append(move)    
            elif move[:-1]+"Prom" in self.legal:
                self.promotion(move)
                self.moves.append(move)
            elif move[1]=='@' and len(move)==4:
                piece = move[0] if self.wmove else move[0].lower()
                if piece in self.pool:
                    self.place(piece,ord(move[2])-97,int(move[3])-1)
        self.isActive()
#verify checks
class BugBoards:
    def __init__(self,FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 -'):
        self.boards = [Board(FEN),Board(FEN)]
        self.result = []
        self.active = self.boards[0].active and self.boards[1].active
    def play(self,move,board):
        if self.active:
            self.boards[board].play(move)
            self.boards[board^1].pool.extend(self.boards[board].otpool)
            self.boards[board].otpool = []
            self.active = self.boards[0].active and self.boards[1].active
        else:
            self.result = [board.result for board in self.boards]
    def display(self):
        for Board in self.boards:
            for row in reversed(Board.board):
                print('|'.join(square.piece.name() if square.occupied else '•' for square in row))
            print()
    def grid(self):
        return [[[square.piece.name() if square.occupied else '•' for square in row] for row in board] for board in self.boards]
if __name__ == "__main__":
    # Initialize the bughouse game
    bughouse_game = BugBoards()

    # Display initial state
    print("Initial state:")
    bughouse_game.display()

    # Simulate a sequence of moves
    """
    moves = [
        ("e2e4", 0),("e2e4", 1),("d7d5", 0),("d7d5", 1),("e4d5", 0),("a7a5",0),("p@d7",1)
    ]
    """
    moves = [
        ("e2e4", 0), ("b8c6", 0), ("d2d4", 1),  ("b1c3", 0),
        ("g8f6", 1),("g8f6", 0), ("d4d5", 1), ("d2d4", 0),
        ("e7e6", 1),("d7d5", 0), ("d5e6", 1), ("e4e5", 0), 
        ("d7e6", 1), ("d1d8", 1), ("f6e4", 0), 
        ("e8d8", 1), ("c1g5", 1), ("c3e4", 0), 
        ("d5e4", 0), ("f8e7", 1), ("g1h3", 0), 
        ("b1c3", 1), ("c8h3", 0), ("N@d4", 1),  
        ("g2h3", 0), ("c6d4", 0), ("O-O-O", 1),
        ("P@e6", 0), ("b8c6", 1), ("g5f6", 1), 
        ("N@f3", 0), ("d1f3", 0), ("e7f6", 1),  
        ("d4f3", 0), ("e1e2", 0), ("e2e3", 1),  
        ("Q@d2", 0), ("c1d2", 0), ("d8d2", 0)
    ]
    
    for move, board_index in moves:
        bughouse_game.play(move, board_index)
        print(f"\nAfter move {move} on board {board_index}:")
        bughouse_game.display()
        print(bughouse_game.active)
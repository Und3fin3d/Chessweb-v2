from re import split
from copy import deepcopy
from pieces import *

class Square:
    def __init__(self,name,piece = None):
        self.name = name
        self.piece = piece
        self.occupied = (piece != None)
    def movein(self,piece):
        self.piece = piece
        self.occupied = True
    def moveout(self):
        p = self.piece
        self.piece = None
        self.occupied = False
        return p
class Board:
    def __init__(self,FEN='rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'):
        self.K = (None,None)
        self.k = (None,None)
        self.FEN = FEN
        self.board,self.wmove, self.wcast, self.bcast,self.ep,self.fifty, self.movenum = self.loadFEN(FEN)
        self.moves = []
        self.result = None
        self.prom = []
        self.legal = []
        self.active = True
        self.isActive()
        
    def pclass(self,pname,x,y):
        m = False
        if pname == 'k':
            self.k = (x,y)
        elif pname == 'K':
            self.K = (x,y)
        elif pname == 'p' and y!=6:
            m = True
        elif pname == 'P' and y!=1:
            m = True        
        pdict = {'p':Pawn(pname.isupper(),x,y,self,m),'n':Knight(pname.isupper(),x,y,self),'b':Bishop(pname.isupper(),x,y,self),'r':Rook(pname.isupper(),x,y,self),'q':Queen(pname.isupper(),x,y,self),'k':King(pname.isupper(),x,y,self),}
        return pdict[pname.lower()]
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
        return grid,gamestate[0]=='w', castle1, castle2,gamestate[2],gamestate[3], gamestate[-1]
    def displayboard(self,board=None):
        board = self.board if board is None else board
        for row in reversed(board):
            print('|'.join(square.piece.name() if square.occupied else '•' for square in row))
        print()
    def grid(self):
        return [[square.piece.name() if square.occupied else '•' for square in row] for row in self.board]
    def incheck(self):
        x, y = (self.K if self.wmove else self.k)
        if self.board[y][x].piece.check():
            return self.board[y][x].name
        else:
            return ''
    def isActive(self):
        self.legal = self.get_legalmoves()
        if not self.legal:
            self.active = False 
            x, y = (self.K if self.wmove else self.k)
            if self.board[y][x].piece.check():
                self.result = False if self.wmove else True
        else:
            alive = [x for y in self.grid() for x in y if x != '•']
            if len(alive) == 2:
                self.active = False
            elif len(alive) == 3:
                self.active =  not {'b','B','N','n'} & set(alive)
            elif len(alive) == 4 and 'b' in alive and 'B' in alive:
                bishops = [(x-1,y-1) for y in range(len(self.grid())) for x in range(len(self.grid()[0])) if self.grid()[y][x].lower() == 'b']
                if sum(bishops[0])%2 == sum(bishops[1])%2:
                    self.active = False

                
            
    def promotion(self,move):
        prom = move[-1].lower()
        move = [int(move[1])-1,ord(move[0])-97,int(move[3])-1,ord(move[2])-97]
        p = self.board[move[0]][move[1]].moveout()
        cls = {'n':Knight(p.colour,None,None,self),'b':Bishop(p.colour,None,None,self),'r':Rook(p.colour,None,None,self),'q':Queen(p.colour,None,None,self)}
        try: 
            piece = cls[prom]
        except:
            print(f'{prom} is not a valid promotion')
            return
        piece.x, piece.y = move[1], move[0]
        piece.has_moved = p.has_moved
        self.board[move[2]][move[3]].movein(piece)
        piece.move(move[3],move[2])
        self.wmove = not self.wmove
        self.ep = '-'
        self.prom = [] 
        
    def playraw(self,move):
        if type(move) == list:
            self.board[move[2]][move[3]].movein(self.board[move[0]][move[1]].moveout())
            self.board[move[2]][move[3]].piece.move(move[3],move[2])
            if self.board[move[2]][move[3]].piece.name().lower()=='p' and self.ep == (move[2],move[3]):
                dir = 1 if self.wmove else -1
                self.board[move[2]-dir][move[3]].moveout()
            elif self.board[move[2]][move[3]].piece.name().lower() == 'k':
                if self.wmove:
                    self.K = (move[3], move[2])
                else:
                    self.k = (move[3], move[2])
        else:
            y = 0 if self.wmove else 7
            if move ==  'O-O':
                self.board[y][6].movein(self.board[y][4].moveout())
                self.board[y][6].piece.move(6,y)
                self.board[y][5].movein(self.board[y][7].moveout())
                self.board[y][5].piece.move(5,y)
                if self.wmove:
                    self.K = (6, y)
                else:
                    self.k = (6, y)
            else:
                self.board[y][2].movein(self.board[y][4].moveout())
                self.board[y][2].piece.move(2,y)
                self.board[y][3].movein(self.board[y][0].moveout())
                self.board[y][3].piece.move(3,y)
                if self.wmove:
                    self.K = (2, y)
                else:
                    self.k = (2, y)
    def play(self,move):
        if self.active:
            if move in self.legal:
                if move[0]!='O':
                    move = [int(move[1])-1,ord(move[0])-97,int(move[3])-1,ord(move[2])-97]
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
        self.isActive()
        #self.movenum += 1
        #self.fifty = 0 if self.board[self.K[1]][self.K[0]].piece.has_moved else 5    
    def pseudolegalmoves(self):
        return [element for y in range(8) for x in range(8) if self.board[y][x].occupied and self.board[y][x].piece.colour == self.wmove for element in self.board[y][x].piece.legalmoves()]
    def get_legalmoves(self):
        pseudo = self.pseudolegalmoves()
        legal = []
        oldK = self.K[::]
        oldk = self.k[::]
        old = deepcopy(self.board)
        for move in pseudo:
            self.playraw(move)
            if type(move)==list:
                x, y = (self.K if self.wmove else self.k)
                if not self.board[y][x].piece.check():
                    m = self.board[move[0]][move[1]].name+self.board[move[2]][move[3]].name
                    if move in self.prom:
                        m+="Prom"  
                    legal.append(m)
            else:
                y = 0 if self.wmove else 7
                if (move ==  'O-O' and not self.board[y][6].piece.check()) or (move == 'O-O-O' and not self.board[y][2].piece.check()):
                    legal.append(move)
            
            self.board = deepcopy(old)
            self.K = oldK
            self.k = oldk
        return legal
    def legalmoves(self):
        if not self.legal:
            self.legal = self.get_legalmoves()
        return self.legal

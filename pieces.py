class Pieces:
    def __init__(self,colour,x,y,board,has_moved=False):
        self.colour = colour
        self.x = x
        self.y = y
        self.has_moved = has_moved
        self.board = board
    def __deepcopy__(self, memo):
        new_piece = self.__class__.__new__(self.__class__)
        memo[id(self)] = new_piece
        for key, value in self.__dict__.items():
            setattr(new_piece, key, value)
        return new_piece
    def move(self,x,y):
        self.x = x
        self.y = y
        self.has_moved = True
class Pawn(Pieces):
    def __init__(self,colour,x,y,board,has_moved=False):
        super().__init__(colour,x,y,board,has_moved)
        self.dir = 1 if self.colour else -1
    def name(self) -> str:
        return 'P' if self.colour else 'p'  
    def legalmoves(self) -> list:
        legalmoves = []
        if not self.board.board[self.y+self.dir][self.x].occupied: 
            legalmoves.append([self.y,self.x,self.y+self.dir,self.x])
            if not self.has_moved and not self.board.board[self.y+self.dir*2][self.x].occupied:
                legalmoves.append([self.y,self.x,self.y+self.dir*2,self.x])
        if  self.x + 1 < 8 and self.board.board[self.y+self.dir][self.x+1].occupied and self.board.board[self.y+self.dir][self.x+1].piece.colour!= self.colour:
            legalmoves.append([self.y,self.x,self.y+self.dir,self.x+1])
        if  self.x - 1 >= 0 and self.board.board[self.y+self.dir][self.x-1].occupied and self.board.board[self.y+self.dir][self.x-1].piece.colour!= self.colour:
            legalmoves.append([self.y,self.x,self.y+self.dir,self.x-1])
        if (self.x + 1 < 8 and self.board.ep==(self.y+self.dir,self.x+1)) or (self.x - 1 >= 0 and self.board.ep==(self.y+self.dir,self.x-1)):
            legalmoves.append([self.y,self.x,self.board.ep[0],self.board.ep[1]])
        if self.has_moved and self.y in [1,6]:
            add = [x for x in legalmoves if x not in self.board.prom]
            self.board.prom.extend(add)
        return legalmoves
class Knight(Pieces):
    def name(self) -> str:
        return 'N' if self.colour else 'n'
    def legalmoves(self) -> list:
        legalmoves = []
        for jump in [(2, -1), (-2, -1), (2, 1), (-2, 1), (1, -2), (-1, -2), (1, 2), (-1, 2)]:
            x, y = self.x + jump[0], self.y + jump[1]
            if 0 <= x < 8 and 0 <= y < 8 and (not self.board.board[y][x].occupied or (self.board.board[y][x].piece.colour != self.colour)):
                legalmoves.append([self.y, self.x, y, x])
        return legalmoves
class Rook(Pieces):
    def name(self) -> str:
        return 'R' if self.colour else 'r'
    def legalmoves(self) -> list:
        legalmoves = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            x, y = self.x + dx, self.y + dy
            while 0 <= x < 8 and 0 <= y < 8:
                if not self.board.board[y][x].occupied:
                    legalmoves.append([self.y, self.x, y, x])
                else:
                    if self.board.board[y][x].piece.colour != self.colour:
                        legalmoves.append([self.y, self.x, y, x])
                    break
                x, y = x + dx, y + dy
        return legalmoves
class Bishop(Pieces):
    def name(self) -> str:
        return 'B' if self.colour else 'b'
    def legalmoves(self) -> list:
        legalmoves = []
        for dy, dx in [(1, 1), (-1, -1), (-1, 1), (1, -1)]:
            y, x = self.y + dy, self.x + dx
            while 0 <= y < 8 and 0 <= x < 8:
                if not self.board.board[y][x].occupied:
                    legalmoves.append([self.y, self.x, y, x])
                else:
                    if self.board.board[y][x].piece.colour != self.colour:
                        legalmoves.append([self.y, self.x, y, x])
                    break
                y, x = y + dy, x + dx
        return legalmoves
class Queen(Pieces):
    def name(self) -> str:
        return 'Q' if self.colour else 'q'
    def legalmoves(self) -> list:
        legalmoves = Rook(self.colour,self.x,self.y,self.board).legalmoves() + Bishop(self.colour,self.x,self.y,self.board).legalmoves()
        return legalmoves
class King(Pieces):
    def name(self) -> str:
        return 'K' if self.colour else 'k'
    def legalmoves(self) -> list:
        legalmoves = []
        for step in [(0,1),(1, 1), (-1, -1), (1, -1), (-1, 1), (-1, 1),(1,0),(-1,0),(0,-1)]:
            x, y = self.x + step[0], self.y + step[1]
            if 0 <= x < 8 and 0 <= y < 8 and (not self.board.board[y][x].occupied or (self.board.board[y][x].piece.colour != self.colour)) and not self.nearKing(x,y):
                legalmoves.append([self.y, self.x, y, x])
        cast = self.board.wcast if self.colour else self.board.bcast
        if not self.has_moved and any(cast):
            if not any(self.board.board[self.y][x].occupied or self.check(x,self.y) or self.nearKing(x,self.y) for x in range(self.x + 1, self.x + 3)) and cast[0] and self.board.board[self.y][self.x + 3].occupied and not self.board.board[self.y][self.x + 3].piece.has_moved and self.board.board[self.y][self.x + 3].piece.colour == self.colour and self.board.board[self.y][self.x + 3].piece.name().lower() == 'r':
                legalmoves.append('O-O')
            if not any(self.board.board[self.y][x].occupied or self.check(x,self.y) or self.nearKing(x,self.y) for x in range(self.x - 1, self.x - 4, -1)) and cast[1] and self.board.board[self.y][self.x - 4].occupied and not self.board.board[self.y][self.x - 4].piece.has_moved and self.board.board[self.y][self.x - 4].piece.colour == self.colour and self.board.board[self.y][self.x - 4].piece.name().lower() == 'r':
                legalmoves.append('O-O-O')
        return legalmoves         
    def check(self, x=None, y=None):
        if x is None and y is None:
            x, y = self.x, self.y
        pieces = {Rook:['r','q','R','Q'], Bishop:['b','q','B','Q'], Knight:['n','N']}
        for piece in pieces:
            if any([self.board.board[sq[2]][sq[3]].piece.name() in pieces[piece] if self.board.board[sq[2]][sq[3]].occupied and self.colour!= self.board.board[sq[2]][sq[3]].piece.colour else False for sq in piece(self.colour,x,y,self.board).legalmoves()]):
                return True
        dir = 1 if self.colour else -1
        for offset in [-1,1]:
            if  0 <= x + offset < 8 and self.board.board[y+dir][x+offset].occupied and self.board.board[y+dir][x+offset].piece.colour!= self.colour and self.board.board[y+dir][x+offset].piece.name().lower()=='p':
                return True
        return False
    def nearKing(self,x,y):
        for step in [(0,1),(1, 1), (-1, -1), (1, -1), (-1, 1), (-1, 1),(1,0),(-1,0),(0,-1)]:
            x2, y2 = x + step[0], y + step[1]
            if 0 <= x2 < 8 and 0 <= y2 < 8 and (self.board.board[y2][x2].occupied and self.board.board[y2][x2].piece.colour != self.colour and self.board.board[y2][x2].piece.name().lower()=='k'):
                return True
        return False

const sq = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'};
let beingDragged;
let lastX;
let lastY;
function init(pieces){
let ChessBoard = document.createElement('div');
ChessBoard.setAttribute('class','chessboard');
if (pieces){
    for (let i = 0; i <8; i++)  {
        let tr = document.createElement('div');
        tr.setAttribute('class','row')
        for (let j = 7; j >-1; j--) {
            let td = document.createElement('div');
            td.id = sq[j]+(i+1)
            if ((i + j) % 2 == 1) {
                td.setAttribute('class', 'square white');
                tr.appendChild(td);
            }
            else {
                td.setAttribute('class', 'square black');
                tr.appendChild(td);
            }
        }
        ChessBoard.appendChild(tr);
    }
}
else{
    for (let i = 7; i >-1; i--) {
    let tr = document.createElement('div');
    tr.setAttribute('class','row')
    for (let j = 0; j < 8; j++) {
        let td = document.createElement('div');
        td.id = sq[j]+(i+1)
        if ((i + j) % 2 == 1) {
            td.setAttribute('class', 'square white');
            tr.appendChild(td);
        }
        else {
            td.setAttribute('class', 'square black');
            tr.appendChild(td);
        }
    }
    ChessBoard.appendChild(tr);
    }
}
document.body.appendChild(ChessBoard);
} 


function drawboard(board){
for (let i = 0; i <8; i++){
    for (let j = 0; j<8; j++){
        let square = document.getElementById(sq[j]+(i+1))
        square.innerHTML = '';
        if (board[i][j] !=='•'){
            let img = document.createElement('img');
            img.setAttribute('id',board[i][j])
            img.src = "../static/images/" + board[i][j]+".svg";
            img.addEventListener('dragstart',function(e){
                beingDragged = e.target;
                start = e.target.parentNode.id
            });
            img.addEventListener('touchstart', function(e) {
                beingDragged = img;
                start = e.target.parentNode.id;
                img.style.zIndex = 1;
            });
            img.addEventListener("touchmove", function(e) {
                e.preventDefault();
                lastX =e.touches[0].clientX 
                lastY = e.touches[0].clientY
                img.style.left=e.touches[0].clientX-img.width/2+"px";
                img.style.top=e.touches[0].clientY-img.height/2+"px";
            });
            img.addEventListener("touchend", function(e) {
                e.preventDefault()
                img.style.zIndex = "";
                let sq = document.elementsFromPoint(lastX,lastY)[1]
                if (sq.tagName=="IMG"){
                    sq = sq.parentNode
                }
                sq.textContent = '';
                sq.append(img)
                img.style.left = "50%"
                img.style.top = "50%"
            });
            square.appendChild(img);
        }
    }
}
    
}

function sidepieces(pieces,i){
let spare = document.createElement('div');
spare.setAttribute('class','spare');
spare.innerHTML = ''
spare.id = i
pieces.forEach(piece => {
    let img = document.createElement('img');
    img.id = "sp"
    img.src = "../static/images/" + piece+".svg";
    img.addEventListener('dragstart',function(e){
        beingDragged = e.target.cloneNode(true);
        start = e.target.parentNode.id
        //spare.remove()
        //sidepieces(pieces,i);
    });
        img.addEventListener('touchstart', function(e) {
        beingDragged = img;
        start = e.target.parentNode.id;
        img.style.zIndex = 1;
    });
    img.addEventListener("touchmove", function(e) {
        e.preventDefault();
        lastX =e.touches[0].clientX 
        lastY = e.touches[0].clientY
        img.style.left=e.touches[0].clientX-img.width/2+"px";
        img.style.top=e.touches[0].clientY-img.height/2+"px";
    });
    img.addEventListener("touchend", function(e) {
        e.preventDefault()
        img.style.zIndex = "";
        let sq = document.elementsFromPoint(lastX,lastY)[1]
        if (sq.tagName=="IMG"){
            sq = sq.parentNode
        }
        sq.textContent = '';
        sq.append(img)
        img.style.left = "50%"
        img.style.top = "50%"
    });
    spare.appendChild(img);
})
document.body.appendChild(spare);
}
init(false)

let squares = document.querySelectorAll('.square')
squares.forEach(square => {
    square.addEventListener('drop',function(e){
    square.textContent = '';
    square.append(beingDragged)
    });

    square.addEventListener('dragover',function(e){
    e.preventDefault()
    });
});
let b = [['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R'], ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'], ['•', '•', '•', '•', '•', '•', '•', '•'], ['•', '•', '•', '•', '•', '•', '•', '•'], ['•', '•', '•', '•', '•', '•', '•', '•'], ['•', '•', '•', '•', '•', '•', '•', '•'], ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'], ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r']]
drawboard(b)
sidepieces(['P','N', 'B', 'R', 'Q', 'K'],'bot')
sidepieces(['p','n', 'b', 'r', 'q', 'k'],'top')
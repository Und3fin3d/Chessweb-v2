const socketio = io()
socketio.on('redirect', (dest) => {
  window.location = dest;
});
const sq = {0: 'a', 1: 'b', 2: 'c', 3: 'd', 4: 'e', 5: 'f', 6: 'g', 7: 'h'}
let drag
let beingDragged
let start
let lastX
let lastY
let over
let overlay = document.createElement('div')
let wmove
let count = false

function init(pieces){
  let ChessBoard = document.createElement('div')
  ChessBoard.setAttribute('class','chessboard')
  if (pieces){
    for (let i = 0; i <8; i++)  {
      let tr = document.createElement('div')
      tr.setAttribute('class','row')
      for (let j = 7; j >-1; j--) {
        let td = document.createElement('div')
          td.id = sq[j]+(i+1)
        if ((i + j) % 2 == 1) {
          td.setAttribute('class', 'square white')
          tr.appendChild(td)
        }
        else {
          td.setAttribute('class', 'square black')
          tr.appendChild(td)
        }
      }
      ChessBoard.appendChild(tr)
    }
  }
  else{
    for (let i = 7; i >-1; i--) {
      let tr = document.createElement('div')
      tr.setAttribute('class','row')
      for (let j = 0; j < 8; j++) {
        let td = document.createElement('div')
          td.id = sq[j]+(i+1)
        if ((i + j) % 2 == 1) {
          td.setAttribute('class', 'square white')
          tr.appendChild(td)
        }
        else {
          td.setAttribute('class', 'square black')
          tr.appendChild(td)
        }
      }
      ChessBoard.appendChild(tr)
    }
  }
  document.body.appendChild(ChessBoard)
  ChessBoard.appendChild(overlay)
} 

function time() {
  let tim = document.getElementsByClassName('tim')
  if(tim[Math.abs(colour-wmove)].innerHTML>0){
  tim[Math.abs(colour-wmove)].innerHTML -=1

  timer = setTimeout(time, 1000)
  }
  else if (!isNaN(tim[Math.abs(colour-wmove)].innerHTML) && !isNaN(parseFloat(tim[Math.abs(colour-wmove)].innerHTML))){
    socketio.emit("timeout")
  }
}

let legalmoves
socketio.on('update',function(data){
  legalmoves = data.moves
  drawboard(data.board)
  let targets = document.querySelectorAll('.target')
  removehigh(targets,'target')
  let square = document.getElementById(data.square)
  if (square != null){
    square.classList.add('target')
  }
  let check = document.querySelectorAll('.highlight3')
  removehigh(check,'highlight3')
  if (document.getElementById(data.checks) != null){
    document.getElementById(data.checks).classList.add('highlight3')
  }
  let tim = document.getElementsByClassName('tim')
  if (colour){
    tim = Array.from(tim)
    tim.reverse()

  }
  wmove = data.move
  tim[0].innerHTML = data.black 
  tim[1].innerHTML = data.white
  if (!count){
    time()
    count = true

  }

  

})
socketio.on('names',function(data){
  let names = document.getElementsByClassName('tle')
  if (colour){
    names = Array.from(names)
    names.reverse()

  }
  names[0].innerHTML = data.black
  names[1].innerHTML = data.white
})

socketio.on('over', async function(data){
  const board = document.getElementsByClassName("chessboard")
  await new Promise(resolve => setTimeout(resolve, 3000))
  board[0].remove()
  const t = document.getElementById("t")
  t.remove()
  const b = document.getElementById("bo")
  b.remove()
  let play = document.createElement('div')
  socketio.emit("over")
  play.setAttribute('class','home')
  play.innerHTML = "Play again?"
  play.onclick = function() {
    if (sess['game'][1] == 'challenge'){
      socketio.emit("challengeAgain")
    }
    else{
      socketio.emit("pair",{data : [sess['game'][1],sess['increment']]})
    }
    let load = document.createElement('div')
    load.classList.add("load")
    play.innerHTML = ''
    play.appendChild(load)

  }
  let home = document.createElement('div')
  home.setAttribute('class','home')
  home.innerHTML = "Homepage"
  home.onclick = function(){
    socketio.emit("home")
  }
  document.body.appendChild(play)
  document.body.appendChild(home)
})
function send(move){
  socketio.emit("move", { data: move })
}

function drawboard(board){
  for (let i = 0; i <8; i++){
    for (let j = 0; j<8; j++){
      let square = document.getElementById(sq[j]+(i+1))
      square.innerHTML = ''
      if (board[i][j] !=='•'){
        let img = document.createElement('img')
        img.setAttribute('id',board[i][j])
        img.src = "../static/images/" + board[i][j]+".svg"
        img.addEventListener('dragstart',function(e){
          beingDragged = e.target
          start = e.target.parentNode.id
        })
        img.addEventListener('touchstart', function(e) {
          beingDragged = img
          start = e.target.parentNode.id
          img.style.zIndex = 1
        })
        img.addEventListener("touchmove", function(e) {
          if (isLowerCase(beingDragged.id)==colour){
            e.preventDefault()
            lastX =e.touches[0].clientX 
            lastY = e.touches[0].clientY
            img.style.left=(e.touches[0].clientX-square.getBoundingClientRect().left)+"px"
            img.style.top=(e.touches[0].clientY-square.getBoundingClientRect().top)+"px"
            let tar = document.elementsFromPoint(lastX,lastY)[1]
            if (tar != document.getElementById(start)){
              if(tar.tagName=="DIV" && !tar.hasChildNodes()){
                if(over!=null){
                  over.classList.remove('highlight')
                  over.classList.remove('highlight2')
                }
                over = tar
                over.classList.add('highlight')
              }
              else if(tar.tagName=="IMG" && isLowerCase(tar.id) != isLowerCase(img.id)){
                if(over!=null){
                  over.classList.remove('highlight')
                  over.classList.remove('highlight2')
                }
                over = tar.parentNode
                over.classList.add('highlight2')
              }
            }
          }
        })
        img.addEventListener("touchend", function(e) {
          if (isLowerCase(beingDragged.id)==colour){
            e.preventDefault()
            img.style.zIndex = ""
            let squares =  document.elementsFromPoint(lastX,lastY)
            let sq = null
            for (let square of squares) {
              if (square && square.classList.contains('square')) {
                  sq = square
                  break
              }
            }
            let move = start + sq.id
            if (isLowerCase(img.id)==colour){
              if (img.id.toLowerCase()=='k'){
                if(start.substring(0,1)=='e'){
                  if(sq.id.substring(0,1)=='c'){
                    move = 'O-O-O'
                  }
                  if(sq.id.substring(0,1)=='g'){
                    move = 'O-O'
                  }
                }
              }
              if (legalmoves.includes(move)){
                if(sq.children.length != 0){
                  if (isLowerCase(sq.children[0].id) != isLowerCase(img.id)){
                    sq.textContent = ''
                    sq.append(img)
                    img.style.left = "50%"
                    img.style.top = "50%"
                    send(move)
                    over.classList.remove('highlight')
                    over.classList.remove('highlight2')
                  }
                }
                else{
                  sq.append(img)
                  img.style.left = "50%"
                  img.style.top = "50%"
                  send(move)
                  over.classList.remove('highlight')
                  over.classList.remove('highlight2')
                }
              }
              else if (legalmoves.includes(move+'Prom')){
                sq.innerHTML = ''
                over.classList.remove('highlight2')
                for (let i = 7; i >4; i--) {
                  let s = document.getElementById(sq.id.substring(0,1)+i)
                  s.innerHTML = ''
                }
                overlay.classList.add('overlay')
                fillProm(['Q','N','B','R'],move)
                sq.appendChild(promotion)
              }
              else{
                  img.style.top = "50%"
                  img.style.left = "50%"
                  over.classList.remove('highlight')
                  over.classList.remove('highlight2')
              }
            }
          }
      })
        square.appendChild(img)
      }
    }
  }
}

function isLowerCase(str){
    return str == str.toLowerCase() && str != str.toUpperCase()
}
function removehigh(targets,clas){
  targets.forEach(target =>{
    target.classList.remove(clas)
  })
}
socketio.on('challenge', (data) => {
  socketio.emit('challengePair')
})

init(colour)
send('initiation')

let promotion
promotion = document.createElement('div')
promotion.setAttribute('class','promotion')
function fillProm(pieces,move){
  promotion.innerHTML = ''
  pieces.forEach(piece => {
    let x = document.createElement("INPUT")
    x.setAttribute("type", "image")
    x.src = "../static/images/"+piece+".svg"
    x.addEventListener('click',function(e){
      send(move+piece)
      overlay.classList.remove('overlay')
    })
    
    x.addEventListener('mouseover',function(e){
      let y = document.querySelectorAll('.highlight')
      removehigh(y,'highlight')
      x.classList.add('highlight')
    })
    x.addEventListener('dragstart',function(e){
      e.preventDefault()
    })
    promotion.appendChild(x)
  })
}

let squares = document.querySelectorAll('.square')
squares.forEach(square => {
    square.addEventListener('drop',function(e){
      let move = start + square.id
      if (isLowerCase(beingDragged.id)==colour){
        if (beingDragged.id.toLowerCase()=='k'){
          if(start.substring(0,1)=='e'){
            if(square.id.substring(0,1)=='c'){
              move = 'O-O-O'
            }
            if(square.id.substring(0,1)=='g'){
              move = 'O-O'
            }
          }
        }
        if (legalmoves.includes(move)){
          if(square.children.length != 0){
            if (isLowerCase(e.target.id) != isLowerCase(beingDragged.id)){
              square.textContent = ''
              square.append(beingDragged)
              send(move)
              square.classList.remove('highlight')
              square.classList.remove('highlight2')
            }
          }
          else{
            e.target.append(beingDragged)
            send(move)
            e.target.classList.remove('highlight')
            square.classList.remove('highlight2')
          }
        }
        else if (legalmoves.includes(move+'Prom')){
          square.innerHTML = ''
          square.classList.remove('highlight2')
          for (let i = 7; i >4; i--) {
            let s = document.getElementById(square.id.substring(0,1)+i)
            s.innerHTML = ''
          }
          overlay.classList.add('overlay')
          fillProm(['Q','N','B','R'],move)
          square.appendChild(promotion)
        }
        else{
            e.target.classList.remove('highlight')
            square.classList.remove('highlight2')
        }
    }

    });  
    square.addEventListener('dragover',function(e){
      e.preventDefault()
    });  
    square.addEventListener('dragenter',function(e){
      if (isLowerCase(beingDragged.id)==colour){
        if(e.target.tagName =='IMG'){
          if (isLowerCase(e.target.id) != isLowerCase(beingDragged.id)){
            if(e.target.parentNode.classList.contains('target')){
              e.target.parentNode.classList.remove('target')
              e.target.parentNode.classList.add('highlight2')
              setTimeout(()=> e.target.parentNode.classList.add('target'),1000)//eeeee
            }
            else{
              e.target.parentNode.classList.add('highlight2')
            }
          
          }
        }
        else{
          if(square.children.length == 0){
              e.target.classList.add('highlight')
          }
        }
      }
    });  
    square.addEventListener('dragleave',function(e){
      e.target.classList.remove('highlight')
      e.target.parentNode.classList.remove('highlight2')
    });  
})

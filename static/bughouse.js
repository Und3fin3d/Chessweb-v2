const socketio = io()
socketio.on('redirect', (dest) => {
  window.location = dest
})

const meta = window.gameMeta || {}
const sess = meta.session || {}
const boardIndex = meta.bug_board ?? 0
const playerColour = (meta.bug_colour || 'white').toLowerCase()
const isBlack = playerColour === 'black'
const partnerIndex = boardIndex ^ 1
const sq = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

const boardHost = document.getElementById('primary-board')
const partnerHost = document.getElementById('secondary-board')
const primaryPool = document.getElementById('primary-pool')
const secondaryPool = document.getElementById('secondary-pool')
const primaryNote = document.getElementById('primary-note')
const secondaryNote = document.getElementById('secondary-note')
const primaryLabel = document.getElementById('primary-label')
const turnIndicator = document.getElementById('turn-indicator')
const toast = document.getElementById('game-toast')
const overlayRoot = document.getElementById('overlay-root')
const homeBtn = document.getElementById('home-btn')
const againBtn = document.getElementById('again-btn')
const nameNodes = [document.querySelector('[data-role="top-name"]'), document.querySelector('[data-role="bottom-name"]')]
const clockNodes = [document.querySelector('[data-role="top-clock"]'), document.querySelector('[data-role="bottom-clock"]')]
if (isBlack) {
  nameNodes.reverse()
  clockNodes.reverse()
}

primaryLabel.textContent = 'Your board'
if (homeBtn) {
  homeBtn.addEventListener('click', () => socketio.emit('home'))
}
if (againBtn) {
  againBtn.disabled = true
  againBtn.addEventListener('click', queueBughouseRematch)
}

const mainBoard = buildBoard(boardHost, isBlack, 'main')
const partnerBoard = buildBoard(partnerHost, false, 'partner')

const state = {
  legal: [],
  board: [],
  partnerBoard: [],
  pool: [],
  partnerPool: [],
  selected: null,
  dropPiece: null,
  dropNode: null,
  boardIndex,
  partnerIndex,
  timers: [
    { white: 0, black: 0 },
    { white: 0, black: 0 }
  ],
  turns: [true, true],
  raf: null,
  finished: false,
  timeoutSent: false
}

Object.values(mainBoard).forEach(square => {
  square.addEventListener('click', () => handleSquareClick(square.dataset.square))
})

toastMessage('Waiting for players...')
socketio.emit('bug_initiate')

socketio.on('bug_state', (data) => {
  if (!data || !data.boards) return
  state.legal = data.legal[boardIndex] || []
  state.board = data.boards[boardIndex] || []
  state.partnerBoard = data.boards[partnerIndex] || []
  state.pool = data.pools[boardIndex] || []
  state.partnerPool = data.pools[partnerIndex] || []
  state.turns = data.turns || [true, true]
  state.timers = data.timers ? data.timers.map(clock => ({ ...clock })) : state.timers
  state.finished = false
  state.timeoutSent = false
  renderBoard(mainBoard, state.board)
  renderBoard(partnerBoard, state.partnerBoard)
  applyChecks(data.checks)
  applyLastMoves(data.lastMove)
  updateNames(data.names)
  renderPools()
  updateTurnIndicator()
  updateClockDisplays()
  startTimerLoop()
})

socketio.on('bug_over', ({ message }) => {
  state.finished = true
  if (againBtn) {
    againBtn.disabled = false
  }
  toastMessage(message || 'Game over')
  socketio.emit('over')
})

socketio.on('challenge', () => {
  socketio.emit('challengePair')
})

function queueBughouseRematch () {
  if (!sess || !sess.game) return
  againBtn.disabled = true
  socketio.emit('bugmatch', { data: [sess.game[1], sess.increment || 0] })
}

function buildBoard (container, flipped, prefix) {
  container.innerHTML = ''
  const squares = {}
  if (flipped) {
    for (let rank = 0; rank < 8; rank++) {
      const row = document.createElement('div')
      row.classList.add('row')
      for (let file = 7; file >= 0; file--) {
        const squareId = sq[file] + (rank + 1)
        const square = document.createElement('div')
        square.classList.add('square')
        square.dataset.square = squareId
        square.id = `${prefix}-${squareId}`
        square.classList.add((rank + file) % 2 === 0 ? 'white' : 'black')
        row.appendChild(square)
        squares[squareId] = square
      }
      container.appendChild(row)
    }
  } else {
    for (let rank = 7; rank >= 0; rank--) {
      const row = document.createElement('div')
      row.classList.add('row')
      for (let file = 0; file < 8; file++) {
        const squareId = sq[file] + (rank + 1)
        const square = document.createElement('div')
        square.classList.add('square')
        square.dataset.square = squareId
        square.id = `${prefix}-${squareId}`
        square.classList.add((rank + file) % 2 === 0 ? 'white' : 'black')
        row.appendChild(square)
        squares[squareId] = square
      }
      container.appendChild(row)
    }
  }
  return squares
}

function renderBoard (map, boardData) {
  for (let rank = 0; rank < 8; rank++) {
    for (let file = 0; file < 8; file++) {
      const squareId = sq[file] + (rank + 1)
      const square = map[squareId]
      if (!square) continue
      square.innerHTML = ''
      const piece = boardData[rank] && boardData[rank][file]
      if (piece && piece !== '•') {
        const img = document.createElement('img')
        img.id = piece
        img.src = `../static/images/${piece}.svg`
        square.appendChild(img)
      }
      square.classList.remove('highlight3', 'last-move', 'target', 'highlight')
    }
  }
}

function applyChecks (checks = []) {
  document.querySelectorAll('.highlight3').forEach(node => node.classList.remove('highlight3'))
  const mainCheck = checks[boardIndex]
  if (mainCheck && mainBoard[mainCheck]) {
    mainBoard[mainCheck].classList.add('highlight3')
  }
  const partnerCheck = checks[partnerIndex]
  if (partnerCheck && partnerBoard[partnerCheck]) {
    partnerBoard[partnerCheck].classList.add('highlight3')
  }
}

function applyLastMoves (moves = []) {
  document.querySelectorAll('.last-move').forEach(node => node.classList.remove('last-move'))
  const primary = moves[boardIndex]
  if (primary && primary.to && mainBoard[primary.to]) {
    mainBoard[primary.to].classList.add('last-move')
  }
  if (primary && primary.from && mainBoard[primary.from]) {
    mainBoard[primary.from].classList.add('last-move')
  }
  const partner = moves[partnerIndex]
  if (partner && partner.to && partnerBoard[partner.to]) {
    partnerBoard[partner.to].classList.add('last-move')
  }
  if (partner && partner.from && partnerBoard[partner.from]) {
    partnerBoard[partner.from].classList.add('last-move')
  }
}

function updateNames (names = []) {
  const primary = names[boardIndex] || { white: 'White', black: 'Black' }
  const partner = names[partnerIndex] || { white: 'White', black: 'Black' }
  nameNodes[0].textContent = primary.black
  nameNodes[1].textContent = primary.white
  if (primaryNote) {
    primaryNote.textContent = `You are playing as ${playerColour === 'white' ? 'White' : 'Black'}`
  }
  if (secondaryNote) {
    secondaryNote.textContent = `${partner.white} vs ${partner.black}`
  }
}

function renderPools () {
  renderPool(primaryPool, state.pool, playerColour, true)
  renderPool(secondaryPool, state.partnerPool, playerColour === 'white' ? 'black' : 'white', false)
}

function renderPool (container, pool, colour, interactive) {
  if (!container) return
  container.innerHTML = ''
  const pieces = pool.filter(piece => colour === 'white' ? piece === piece.toUpperCase() : piece === piece.toLowerCase())
  if (!pieces.length) {
    const span = document.createElement('span')
    span.classList.add('player-status')
    span.textContent = 'No reserve pieces'
    container.appendChild(span)
    return
  }
  const counts = {}
  pieces.forEach(piece => {
    const key = piece.toUpperCase()
    counts[key] = (counts[key] || 0) + 1
  })
  Object.entries(counts).forEach(([piece, count]) => {
    const chip = document.createElement('div')
    chip.classList.add('pool-chip')
    const icon = document.createElement('img')
    const symbol = colour === 'white' ? piece : piece.toLowerCase()
    icon.src = `../static/images/${symbol}.svg`
    const label = document.createElement('span')
    label.textContent = `×${count}`
    chip.appendChild(icon)
    chip.appendChild(label)
    if (interactive) {
      chip.addEventListener('click', () => {
        if (state.dropNode) {
          state.dropNode.classList.remove('active')
        }
        state.dropPiece = piece
        state.dropNode = chip
        chip.classList.add('active')
      })
    }
    container.appendChild(chip)
  })
}

function handleSquareClick (squareId) {
  if (state.finished) return
  if (state.dropPiece) {
    attemptDrop(squareId)
    return
  }
  const piece = pieceAt(squareId)
  if (piece && belongsToPlayer(piece)) {
    selectSquare(squareId)
    return
  }
  if (state.selected) {
    attemptMove(state.selected, squareId)
  }
}

function pieceAt (squareId) {
  const { rank, file } = squareToIndices(squareId)
  return state.board[rank] && state.board[rank][file]
}

function belongsToPlayer (piece) {
  return playerColour === 'white' ? piece === piece.toUpperCase() : piece === piece.toLowerCase()
}

function selectSquare (squareId) {
  clearHighlights()
  state.selected = squareId
  const square = mainBoard[squareId]
  if (square) {
    square.classList.add('target')
  }
  const moves = state.legal.filter(move => move.startsWith(squareId))
  moves.forEach(move => {
    const target = move.slice(2, 4)
    if (mainBoard[target]) {
      mainBoard[target].classList.add('highlight')
    }
  })
}

function attemptMove (from, to) {
  let move = from + to
  const piece = pieceAt(from)
  if (piece && piece.toLowerCase() === 'k' && from[0] === 'e') {
    if (to[0] === 'c') {
      move = 'O-O-O'
    } else if (to[0] === 'g') {
      move = 'O-O'
    }
  }
  if (state.legal.includes(move)) {
    sendBugMove(move)
    clearHighlights()
  } else if (state.legal.includes(move + 'Prom')) {
    openPromotion(move)
  } else {
    clearHighlights()
  }
}

function attemptDrop (squareId) {
  const { rank, file } = squareToIndices(squareId)
  if (state.board[rank] && state.board[rank][file] !== '•') {
    clearDrop()
    return
  }
  if (state.dropPiece === 'P' && (rank === 0 || rank === 7)) {
    toastMessage('Cannot drop a pawn on the first or last rank')
    return
  }
  const symbol = playerColour === 'white' ? state.dropPiece : state.dropPiece.toLowerCase()
  sendBugMove(`${symbol}@${squareId}`)
  clearDrop()
}

function clearHighlights () {
  state.selected = null
  Object.values(mainBoard).forEach(square => square.classList.remove('highlight', 'target'))
}

function clearDrop () {
  state.dropPiece = null
  if (state.dropNode) {
    state.dropNode.classList.remove('active')
    state.dropNode = null
  }
}

function openPromotion (move) {
  if (!overlayRoot) {
    sendBugMove(move + 'Q')
    return
  }
  overlayRoot.innerHTML = ''
  overlayRoot.classList.add('overlay')
  const menu = document.createElement('div')
  menu.classList.add('promotion-menu')
  ;['Q', 'R', 'B', 'N'].forEach(piece => {
    const input = document.createElement('input')
    input.type = 'image'
    input.src = `../static/images/${piece}.svg`
    input.addEventListener('click', () => {
      sendBugMove(move + piece)
      overlayRoot.classList.remove('overlay')
      overlayRoot.innerHTML = ''
    })
    menu.appendChild(input)
  })
  overlayRoot.appendChild(menu)
}

function sendBugMove (move) {
  socketio.emit('bugmove', { data: { move, board: state.boardIndex } })
}

function updateTurnIndicator () {
  if (!turnIndicator) return
  const isWhiteTurn = state.turns[boardIndex]
  const playersTurn = (playerColour === 'white' && isWhiteTurn) || (playerColour === 'black' && !isWhiteTurn)
  turnIndicator.textContent = playersTurn ? 'Your move' : 'Waiting'
}

function updateClockDisplays () {
  const clocks = state.timers[boardIndex] || { white: 0, black: 0 }
  clockNodes[0].textContent = formatTime(clocks.black)
  clockNodes[1].textContent = formatTime(clocks.white)
}

function startTimerLoop () {
  if (state.raf) {
    cancelAnimationFrame(state.raf)
  }
  let last = performance.now()
  const loop = (now) => {
    const delta = (now - last) / 1000
    last = now
    state.turns.forEach((isWhiteTurn, idx) => {
      const runningColour = isWhiteTurn ? 'white' : 'black'
      state.timers[idx][runningColour] = Math.max(0, state.timers[idx][runningColour] - delta)
    })
    updateClockDisplays()
    maybeFlag()
    if (!state.finished) {
      state.raf = requestAnimationFrame(loop)
    }
  }
  state.raf = requestAnimationFrame(loop)
}

function maybeFlag () {
  const clocks = state.timers[boardIndex]
  if (!clocks) return
  const remaining = clocks[playerColour]
  if (remaining <= 0 && !state.timeoutSent) {
    socketio.emit('bug_timeout', { board: state.boardIndex, colour: playerColour })
    state.timeoutSent = true
  }
}

function squareToIndices (squareId) {
  const file = squareId.charCodeAt(0) - 97
  const rank = parseInt(squareId[1], 10) - 1
  return { rank, file }
}

function formatTime (seconds) {
  const value = Math.max(0, Math.floor(seconds))
  const mins = String(Math.floor(value / 60)).padStart(2, '0')
  const secs = String(value % 60).padStart(2, '0')
  return `${mins}:${secs}`
}

function toastMessage (message) {
  if (!toast) return
  toast.textContent = message
  toast.classList.add('active')
  setTimeout(() => toast.classList.remove('active'), 2000)
}

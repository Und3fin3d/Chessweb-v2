let background = '#121012'
let text
let tim
const socket = io()
socket.on('redirect', (dest) => {
    window.location = dest
})
document.body.style.backgroundColor = background
document.getElementById("menu").style.opacity = "1"

window.scrollTo(0, 0)

cur_tab = 0
tab(0)
function tab(new_tab){
    document.getElementsByClassName('tab')[cur_tab].classList.remove("active")
    document.getElementsByClassName('tab')[new_tab].classList.add("active")
    if (new_tab != cur_tab){
        let nam = document.getElementsByClassName("tab")[new_tab].dataset.name
        let type = document.getElementsByClassName("tab")[new_tab].dataset.type
        let vals = document.getElementsByClassName("val")
        vals[cur_tab].style.opacity = "0"
        setTimeout(function(){
            vals[cur_tab].style.display = "none"
            document.getElementById(nam).style.display = type
            vals[new_tab].style.opacity = "0"
            cur_tab = new_tab
        }, 200)
        setTimeout(function(){
            vals[new_tab].style.opacity = "1"
        }, 300)
    }   
}

function startGame(time){
    socket.emit("pair", { data: time })
    if (tim!=undefined){
        document.getElementById(tim).innerHTML = text
    }
    let load = document.createElement('div')
    load.classList.add("load")
    tim = time[0] + time[1]
    text = document.getElementById(tim).innerHTML
    
    document.getElementById(tim).innerHTML = ''
    document.getElementById(tim).appendChild(load)
}

function bugGame(time) {
    socket.emit("bugmatch", { data: time })
    if (tim!=undefined){
        document.getElementById(tim).innerHTML = text
    }
    let load = document.createElement('div')
    load.classList.add("load")
    tim = 'bh' + (time[0] + time[1])
    text = document.getElementById(tim).innerHTML
    
    document.getElementById(tim).innerHTML = ''
    document.getElementById(tim).appendChild(load)
}

// Custom games lobby functionality
let lobby = document.getElementById("lobby")
let lobbyRefreshInterval = null

// Fetch and display custom games
function refreshLobby() {
    socket.emit("listCustomGames")
}

// Create a custom game from the current board position
function createCustomGame() {
    const fen = exportBoardToFEN()
    const timeControl = parseInt(document.getElementById("customTimeControl").value)
    const increment = parseInt(document.getElementById("customIncrement").value)
    
    socket.emit("createCustomGame", {
        fen: fen,
        time: timeControl,
        increment: increment
    })
}

// Join a specific custom game
function joinCustomGame(gameId) {
    socket.emit("joinCustomGame", { gameId: gameId })
}

// Render lobby with custom games
function renderLobby(games) {
    // Clear existing content
    lobby.innerHTML = ''
    
    if (games.length === 0) {
        let emptyMsg = document.createElement("div")
        emptyMsg.classList.add("item")
        emptyMsg.style.textAlign = "center"
        emptyMsg.style.color = "#888"
        emptyMsg.innerHTML = "<p>No custom games available. Create one in the Customise tab!</p>"
        lobby.appendChild(emptyMsg)
        return
    }
    
    for (let game of games) {
        let new_obj = document.createElement("div")
        new_obj.classList.add("item")
        new_obj.style.cursor = "pointer"
        new_obj.setAttribute("data-game-id", game.id)
        new_obj.onclick = function() { joinCustomGame(game.id) }
        
        let positionType = game.isStandard ? "Standard" : "Custom"
        let authBadge = game.authenticated ? "✓ " : ""
        
        let new_title = document.createElement("p")
        new_title.innerHTML = `${authBadge}${game.creator} <span style="float: right; color: #4CAF50;">${positionType}</span>`
        new_title.style.fontWeight = "bold"
        new_title.style.marginBottom = "5px"
        
        let new_desc = document.createElement("p")
        new_desc.style.fontSize = "0.9em"
        new_desc.style.color = "#aaa"
        let incText = game.increment > 0 ? `+${game.increment}` : ""
        new_desc.innerHTML = `⏱️ ${game.time} min${incText} &nbsp;|&nbsp; Position: ${game.fen}`
        
        new_obj.appendChild(new_title)
        new_obj.appendChild(new_desc)
        
        // Hover effect
        new_obj.addEventListener("mouseenter", function() {
            this.style.background = "#2a2a2a"
        })
        new_obj.addEventListener("mouseleave", function() {
            this.style.background = ""
        })
        
        lobby.appendChild(new_obj)
    }
}

// Socket event handlers for custom games
socket.on('customGamesList', (data) => {
    renderLobby(data.games)
})

socket.on('customGameCreated', (data) => {
    // Show success message or loading indicator
    let load = document.createElement('div')
    load.classList.add("load")
    let btn = document.querySelector('#custom-controls button')
    if (btn) {
        btn.innerHTML = ''
        btn.appendChild(load)
    }
})

// Start auto-refreshing lobby when on lobby tab
function startLobbyRefresh() {
    if (!lobbyRefreshInterval) {
        refreshLobby() // Initial load
        lobbyRefreshInterval = setInterval(refreshLobby, 3000) // Refresh every 3 seconds
    }
}

function stopLobbyRefresh() {
    if (lobbyRefreshInterval) {
        clearInterval(lobbyRefreshInterval)
        lobbyRefreshInterval = null
    }
}

// Override tab function to handle lobby refresh
let originalTab = tab
window.tab = function(new_tab) {
    originalTab(new_tab)
    // Tab index 1 is the lobby
    if (new_tab === 1) {
        startLobbyRefresh()
    } else {
        stopLobbyRefresh()
    }
}

let loggedin = sess._fresh
let profile = document.getElementById("profile")
let login = document.getElementsByClassName("login")
let username = document.getElementById("name")
let sec = document.getElementsByClassName("sect")[0]
username.innerHTML = sess.username
if (loggedin){
    login[0].remove()
    
}
else{
    login[1].remove()
    sec.innerHTML = '\n                    <p class="title">Stats</p>\n                    Statistics are not measured on unregistered accounts\n'
}

let custom = document.getElementById("custom")
let board = document.getElementsByClassName("chessboard")[0]
let spares = document.getElementsByClassName("spare")
custom.appendChild(board)
Array.from(spares).forEach(spare => {
    custom.appendChild(spare)
})
if (loggedin){
    socket.emit("getFriendList")
}

// Initial lobby load
refreshLobby()

function sendFriendRequest() {
    const friendUsername = document.getElementById("friendUsername").value
    if (friendUsername) {
        socket.emit("addFriend", friendUsername)
    }
}

function playRoundRobin() {
    // Implement the logic for Round Robin game mode
    console.log("Round Robin game mode selected")
}

function playBughouse() {
    // Implement the logic for Bughouse game mode
    console.log("Bughouse game mode selected")
}

function playChallenge() {
    const friendSelect = document.getElementById('friendSelect')
    const selectedFriend = friendSelect.value

    if (selectedFriend) {
        socket.emit('challengeFriend', selectedFriend)
    } else {
        alert('Please select a friend to challenge.')
    }
}

socket.on('friendAdded', (data) => {
    alert(`${data.friend} has been added as a friend.`)
    socket.emit("getFriendList")

})

socket.on('error', (data) => {
    const friendInput = document.getElementById('friendUsername')
    friendInput.classList.add('shake')
    setTimeout(() => {
        friendInput.classList.remove('shake')
    }, 500)

    alert(data.message)
})

socket.on('friendList', (data) => {
    const Selects = [document.getElementById('friendSelect'),document.getElementsByClassName('Robin')[0],document.getElementsByClassName('Bug')[0]]
    Selects.forEach(friendSelect =>{
        console.log(friendSelect)
        friendSelect.innerHTML = ''
        

        if (data.friends.length > 0) {
            data.friends.forEach(friend => {
                const option = document.createElement('option')
                option.value = friend.username
                option.textContent = friend.username
                friendSelect.appendChild(option)
            })
        } else {
            const option = document.createElement('option')
            option.value = ''
            option.textContent = 'No friends available'
            friendSelect.appendChild(option)
        }
    })
})

socket.on('challenge', (data) => {
    socket.emit('challengePair')
})



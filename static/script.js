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
    text = document.getElementById(time[0]+time[1]).innerHTML
    tim = time[0] + time[1]
    document.getElementById(time[0]+time[1]).innerHTML = ''
    document.getElementById(time[0]+time[1]).appendChild(load)
}

let items = [ 
    ["User 1", "Time constraint Game mode Rules they have setup"],
    ["User 2", "Time constraint Game mode Rules they have setup"],
    ["User 3", "Time constraint Game mode Rules they have setup"],
    ["User 4", "Time constraint Game mode Rules they have setup"],
    ["User 5", "Time constraint Game mode Rules they have setup"],
    ["User 6", "Time constraint Game mode Rules they have setup"]
]

let lobby = document.getElementById("lobby")

for (let i = 0; i < items.length; i++){
    let new_obj = document.createElement("div")
    new_obj.classList.add("item")
    new_obj.style.cursor = "pointer"
    new_obj.setAttribute("id", i)

    let new_title = document.createElement("p")
    new_title.innerHTML = items[i][0]
    let new_desc = document.createElement("p")
    new_desc.innerHTML = items[i][1]

    new_obj.appendChild(new_title)
    new_obj.appendChild(new_desc)

    lobby.appendChild(new_obj)
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
    const friendSelect = document.getElementById('friendSelect')
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

socket.on('challenge', (data) => {
    socket.emit('challengePair')
})



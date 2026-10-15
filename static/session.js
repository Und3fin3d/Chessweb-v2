function showSessionNotice() {
    if (document.getElementById('session-notice')) return
    const notice = document.createElement('dialog')
    notice.id = 'session-notice'
    const message = document.createElement('p')
    message.textContent = 'Your session changed. Reload this page to continue.'
    const reload = document.createElement('button')
    reload.textContent = 'Reload page'
    reload.onclick = () => window.location.reload()
    notice.append(message, reload)
    notice.addEventListener('cancel', event => event.preventDefault())
    document.body.appendChild(notice)
    notice.showModal()
}

function connectSession() {
    const connection = io()
    connection.on('disconnect', reason => {
        if (reason === 'io server disconnect') showSessionNotice()
    })
    connection.on('connect_error', e => {
        if (e.message === 'Connection rejected by server') showSessionNotice()
    })
    return connection
}

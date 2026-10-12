function connectSession() {
    const connection = io()
    connection.on('disconnect', reason => {
        if (reason !== 'io server disconnect') return
        const notice = document.createElement('dialog')
        const message = document.createElement('p')
        message.textContent = 'Your session changed. Reload this page to continue.'
        const reload = document.createElement('button')
        reload.textContent = 'Reload page'
        reload.onclick = () => window.location.reload()
        notice.append(message, reload)
        notice.addEventListener('cancel', event => event.preventDefault())
        document.body.appendChild(notice)
        notice.showModal()
    })
    return connection
}

(() => {
    if (window.webspan) {
        return
    }

    let nextId = 1

    const pending = new Map()

    function send(url) {
        const iframe = document.createElement("iframe")

        iframe.style.display = "none"
        iframe.src = url

        document.documentElement.appendChild(iframe)

        setTimeout(() => {
            iframe.remove()
        }, 0)
    }

    function call(method, data = null) {
        const id = String(nextId++)

        return new Promise((resolve, reject) => {
            pending.set(id, {
                resolve,
                reject,
            })

            const params = new URLSearchParams()

            params.set("id", id)
            params.set("method", method)
            params.set("data", JSON.stringify(data))

            send(
                "webspan://call?"
                + params.toString()
            )
        })
    }

    function resolve(id, response) {
        const request = pending.get(id)

        if (!request) {
            return
        }

        pending.delete(id)

        if (response.ok) {
            request.resolve(response.result)
            return
        }

        const error = new Error(
            response.error?.message
            ?? "Unknown Python error"
        )

        error.name =
            response.error?.type
            ?? "PythonError"

        request.reject(error)
    }

    window.webspan = {
        call,
        _resolve: resolve,
    }
})()

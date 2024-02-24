if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/serviceworker.js')
        .then(success_msg => console.log('Zzz Service Worker registered OK', success_msg))
        .catch(error_msg => console.log('Zzz Service Worker register FAILED', error_msg));
}

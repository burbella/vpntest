self.addEventListener("install", event => {
    console.log("Zzz Service Worker installed");
});

self.addEventListener("activate", event => {
    console.log("Zzz Service Worker activated");
});

const CACHE_NAME = 'workout-v2';
const ASSETS_TO_CACHE = [
    '/static/manifest.json'
];

// Install event - cache assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                return cache.addAll(ASSETS_TO_CACHE);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => caches.delete(name))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - network first for navigation, cache for assets
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;
    
    // Skip external resources
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }
    
    // For navigation requests (HTML pages), always go to network
    // This prevents issues with redirects
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => {
                    // Only serve cached fallback if network fails
                    return caches.match('/plan') || caches.match('/');
                })
        );
        return;
    }
    
    // For other requests (CSS, JS, images), use cache-first strategy
    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }
                
                return fetch(event.request)
                    .then((response) => {
                        // Cache successful responses for static assets
                        if (response.ok && event.request.url.includes('/static/')) {
                            const responseClone = response.clone();
                            caches.open(CACHE_NAME)
                                .then((cache) => cache.put(event.request, responseClone));
                        }
                        return response;
                    });
            })
    );
});
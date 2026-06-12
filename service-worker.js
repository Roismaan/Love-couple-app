// Service Worker для PWA - couple-app
const CACHE_NAME = 'couple-app-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/firebase-config.js',
    'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=Poppins:wght@300;400;500;600&display=swap',
    'https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.0/dist/confetti.browser.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js'
];

// Установка Service Worker
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Кэшируем статические ресурсы');
            return cache.addAll(STATIC_ASSETS.map(url => {
                return new Request(url, { mode: 'no-cors' });
            })).catch(err => {
                console.warn('[SW] Не удалось кэшировать некоторые ресурсы:', err);
            });
        })
    );
    self.skipWaiting();
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => {
                        console.log('[SW] Удаляем старый кэш:', name);
                        return caches.delete(name);
                    })
            );
        })
    );
    self.clients.claim();
});

// Перехват запросов — Network First для Firebase, Cache First для статики
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Firebase запросы — всегда сеть
    if (url.hostname.includes('firebase') ||
        url.hostname.includes('googleapis') ||
        url.hostname.includes('gstatic') ||
        url.hostname.includes('firebaseio')) {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(JSON.stringify({ error: 'Offline' }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }

    // Статические ресурсы — Cache First
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(event.request).then((response) => {
                if (!response || response.status !== 200) {
                    return response;
                }
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(event.request, responseClone);
                });
                return response;
            });
        })
    );
});

// Push-уведомления
self.addEventListener('push', (event) => {
    console.log('[SW] Push получен');

    let notificationData = {
        title: '❤️ Наша история',
        body: 'Новое сообщение от любимого человека',
        icon: '',
        badge: '',
        vibrate: [200, 100, 200, 100, 200],
        data: { url: '/' },
        actions: [
            { action: 'open', title: 'Открыть ❤️' },
            { action: 'close', title: 'Закрыть' }
        ]
    };

    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = { ...notificationData, ...data };
        } catch (e) {
            notificationData.body = event.data.text();
        }
    }

    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            vibrate: notificationData.vibrate,
            data: notificationData.data,
            actions: notificationData.actions,
            requireInteraction: false,
            silent: false
        })
    );
});

// Клик по уведомлению
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'close') return;

    const urlToOpen = (event.notification.data && event.notification.data.url) || '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
            for (const client of clientList) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// Синхронизация в фоне
self.addEventListener('sync', (event) => {
    if (event.tag === 'background-sync') {
        console.log('[SW] Фоновая синхронизация');
    }
});
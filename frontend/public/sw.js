/* 서비스 워커 — 보수적 캐싱 전략.
 *
 * - /assets/* (해시 자산): cache-first — 파일명이 내용 해시라 영원히 안전.
 * - 내비게이션(문서): network-first, 오프라인일 때만 캐시된 셸로 폴백 —
 *   index.html no-cache 배포 전략(재배포 즉시 반영)을 깨지 않는다.
 * - /api/*: 캐시하지 않는다(항상 신선한 데이터, 실패는 앱 UI가 처리).
 */
const SHELL_CACHE = 'shell-v1'
const ASSET_CACHE = 'assets-v1'

self.addEventListener('install', (event) => {
  self.skipWaiting()
  event.waitUntil(caches.open(SHELL_CACHE))
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/')) return // 항상 네트워크

  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icons/')) {
    event.respondWith(
      caches.open(ASSET_CACHE).then(async (cache) => {
        const hit = await cache.match(event.request)
        if (hit) return hit
        const res = await fetch(event.request)
        if (res.ok) cache.put(event.request, res.clone())
        return res
      }),
    )
    return
  }

  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const copy = res.clone()
          caches.open(SHELL_CACHE).then((c) => c.put('/', copy))
          return res
        })
        .catch(() => caches.match('/')),
    )
  }
})

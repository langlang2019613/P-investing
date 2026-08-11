/* 飘投资研究库 service worker — 离线缓存
   CACHE 版本号由 build.py 自动更新；版本变化触发客户端重新缓存全部资源。

   设计要点（2026-08-11 修订，修复 Safari/WebKit 下离线打开白屏的问题）：
   - data.json 体积大（8MB+ 且持续增长），不放进 install 阶段的批量 addAll。
     实测在 WebKit 下，addAll 里混入一个大文件会导致整个批量缓存静默失败
     （install 事件不报错，但 cache 里最终 0 条记录），offline 时白屏。
     现在 data.json 只走 fetch 时的"网络优先、成功后 cache.put"这条路径，
     App 首次联网加载时自然就会把它缓存下来，且单文件 put 不受批量操作
     牵连、失败了也不影响其余 shell 资源。
   - install 阶段改成逐个资源 fetch + put（Promise.allSettled），而不是
     caches.addAll(shell) 的"一个失败全部失败"语义，个别资源加载失败
     不会导致整个离线缓存都装不上。
   - 导航请求（用户直接访问/刷新任意路径）离线且未命中缓存时，兜底返回
     缓存的 index.html——因为这是纯前端 hash 路由单页应用，任何路径都
     能由 index.html + app.js 正确渲染。 */
const CACHE = 'pi-20260812003506';
const SHELL = [
  './',
  'index.html',
  'css/app.css',
  'js/app.js',
  'js/marked.min.js',
  'manifest.json',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-180.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) =>
      Promise.allSettled(
        SHELL.map((url) =>
          fetch(url, { cache: 'no-store' }).then((res) => {
            if (res && res.ok) return cache.put(url, res);
          }).catch(() => {})
        )
      )
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;

  // data.json: 网络优先（拿最新内容），成功则更新缓存；失败回退缓存（离线可用）
  if (url.pathname.endsWith('/data.json')) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }

  // 导航请求（地址栏直接打开/刷新任意路径）：离线且未命中缓存时，
  // 兜底返回缓存的 index.html——单页应用任何路径都能正确渲染。
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
          return res;
        })
        .catch(() =>
          caches.match(e.request).then((hit) => hit || caches.match('index.html'))
        )
    );
    return;
  }

  // 其余资源（css/js/图标等）: 缓存优先，未命中则联网取并补缓存
  e.respondWith(
    caches.match(e.request).then((hit) => hit || fetch(e.request).then((res) => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
      }
      return res;
    }).catch(() => hit))
  );
});

import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import http from 'node:http';
import { after, before, test } from 'node:test';
import { fileURLToPath } from 'node:url';

let published = true;
let resources = [];
let upstreamAuthorization = '';
const article = { slug: 'safe-article', title: 'Useful <script> content', excerpt: 'A safe "description"',
  author: 'Editorial', category: 'Guides', tags: [], cover: '', cover_alt: '', published_at: '2026-10-12T00:00:00Z', updated_at: '2026-10-12T00:00:00Z', body: '# A heading\n\n<script>alert("unsafe")</script>', seo_title: '', seo_description: '' };
const upstream = http.createServer((req, res) => {
  upstreamAuthorization = req.headers.authorization || '';
  res.setHeader('Content-Type', 'application/json');
  if (req.url === '/api/v1/website/manifest') return res.end(JSON.stringify({resources}));
  if (new URL(req.url,'http://localhost').pathname === '/api/v1/website/posts') return res.end(JSON.stringify(published ? [article] : []));
  if (req.url === '/api/v1/website/posts/safe-article' && published) return res.end(JSON.stringify(article));
  if (req.url === '/api/v1/auth/logout') { res.statusCode = 204; return res.end(); }
  res.statusCode = 404; res.end(JSON.stringify({ detail: 'Not found' }));
});
let child;
let origin;
before(async () => {
  await new Promise(resolve => upstream.listen(0, '127.0.0.1', resolve));
  const reserve = http.createServer();
  await new Promise(resolve => reserve.listen(0, '127.0.0.1', resolve));
  const port = reserve.address().port;
  await new Promise(resolve => reserve.close(resolve));
  origin = `http://127.0.0.1:${port}`;
  child = spawn(process.execPath, [fileURLToPath(new URL('../server.mjs', import.meta.url))], { env: { ...process.env,
    PORT: String(port), API_ORIGIN: `http://127.0.0.1:${upstream.address().port}`,
    WEBSITE_PUBLIC_URL: 'https://website.example.test' }, stdio: 'ignore' });
  for (let attempt = 0; attempt < 100; attempt++) {
    try { if ((await fetch(`${origin}/healthz`)).ok) return; } catch { /* Wait for process startup. */ }
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error('Website server did not start');
});
after(async () => { child?.kill(); await new Promise(resolve => upstream.close(resolve)); });

test('returns crawlable, escaped article content and security headers', async () => {
  const response = await fetch(`${origin}/blog/safe-article`);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Useful &lt;script&gt; content/);
  assert.match(html, /&lt;script&gt;alert/);
  assert.doesNotMatch(html, /<script>alert/);
  const bootstrap = JSON.parse(html.match(/<script type="application\/json" id="website-bootstrap">([\s\S]*?)<\/script>/)[1]);
  assert.equal(bootstrap.post.title, article.title);
  assert.equal(bootstrap.post.body, article.body);
  assert.match(html, /https:\/\/website\.example\.test\/blog\/safe-article/);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.match(response.headers.get('content-security-policy'), /object-src 'none'/);
});

test('marks owner pages as private to crawlers and returns real unknown-route 404s', async () => {
  const admin = await fetch(`${origin}/admin`);
  assert.equal(admin.headers.get('x-robots-tag'), 'noindex, nofollow');
  assert.equal((await fetch(`${origin}/missing-page`)).status, 404);
  assert.equal((await fetch(`${origin}/assets/%2e%2e%2fserver.mjs`)).status, 404);
});

test('preserves authenticated proxy headers and empty logout responses', async () => {
  const response = await fetch(`${origin}/api/v1/auth/logout`, { method: 'POST',
    headers: { Authorization: 'Bearer test-session' } });
  assert.equal(response.status, 204);
  assert.equal(await response.text(), '');
  assert.equal(upstreamAuthorization, 'Bearer test-session');
});

test('removes an unpublished article from HTML and the dynamic sitemap', async () => {
  const initial = await (await fetch(`${origin}/sitemap.xml`)).text();
  assert.match(initial, /safe-article/);
  published = false;
  assert.equal((await fetch(`${origin}/blog/safe-article`)).status, 404);
  const current = await (await fetch(`${origin}/sitemap.xml`)).text();
  assert.doesNotMatch(current, /safe-article/);
});

test('server-renders managed pages and forms, honors noindex and safe redirect parameters', async () => {
  resources = [
    {id:'form',kind:'form',key:'contact-us',title:'Contact form',data:{fields:[{key:'name',label:'Your name',type:'text',required:true},{key:'email',label:'Work email',type:'email',required:true}]}},
    {id:'page',kind:'page',key:'managed-page',title:'Managed <script> page',data:{route:'/managed-page',index:false,description:'Private indexing policy',blocks:[{id:'h',type:'hero',title:'Managed <script> page',body:'Complete content before JavaScript'},{id:'f',type:'form',form_key:'contact-us'}]}},
    {id:'redirect',kind:'redirect',key:'redirect',title:'Redirect',data:{source:'/old-managed',target:'/managed-page',status:308}}
  ];
  try {
    const response = await fetch(`${origin}/managed-page`);
    assert.equal(response.status,200);
    const html = await response.text();
    assert.match(html,/data-ssr="true"/);
    assert.match(html,/Complete content before JavaScript/);
    assert.match(html,/<form/);
    assert.match(html,/Work email/);
    assert.doesNotMatch(html,/<script> page/);
    assert.match(html,/noindex, nofollow/);
    assert.doesNotMatch(await (await fetch(`${origin}/sitemap.xml`)).text(),/managed-page/);
    const redirect = await fetch(`${origin}/old-managed?utm_source=partner&utm_campaign=hello&email=private@example.com`,{redirect:'manual'});
    assert.equal(redirect.status,308);
    assert.equal(redirect.headers.get('location'),'/managed-page?utm_source=partner&utm_campaign=hello');
    resources = [];
    assert.equal((await fetch(`${origin}/managed-page`)).status,404);
  } finally {resources=[];}
});

test('RSS includes published summaries and escapes source text', async () => {
  published=true;
  const response=await fetch(`${origin}/feed.xml`);
  assert.equal(response.status,200);
  assert.match(response.headers.get('content-type'),/application\/rss\+xml/);
  assert.match(await response.text(),/Useful &lt;script&gt; content/);
  published=false;
  assert.doesNotMatch(await (await fetch(`${origin}/feed.xml`)).text(),/safe-article/);
});

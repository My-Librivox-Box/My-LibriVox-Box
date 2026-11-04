// My LibriVox Box — download relay (Cloudflare Worker)
//
// The Internet Archive doesn't let web pages read its files, so the app can't pull an MP3
// itself to save into the folder you chose. This relay fetches the file and hands it back.
// It only fetches from archive.org, so it can't be used for anything else.
//
// Setup: Cloudflare dashboard › Workers & Pages › Create › Hello World › Deploy,
// then Edit code, replace everything with this file, and Deploy again.

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': '*',
  'Access-Control-Expose-Headers': 'Content-Length, Content-Type'
};
const fromArchive = host => host === 'archive.org' || host.endsWith('.archive.org');
const text = (body, status = 200) => new Response(body, { status, headers: { ...CORS, 'Content-Type': 'text/plain; charset=utf-8' } });

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: CORS });
    const url = new URL(request.url);
    if (url.pathname === '/ping') return text('librivox-relay 1');

    let target;
    try { target = new URL(url.searchParams.get('url') || ''); } catch (e) { return text('missing url', 400); }
    if (!/^https?:$/.test(target.protocol) || !fromArchive(target.hostname)) return text('only archive.org files', 403);

    // follows the archive's redirect to its file servers
    const upstream = await fetch(target.toString(), { redirect: 'follow', headers: { 'User-Agent': 'LibriVoxBox-relay/1' } });
    if (!fromArchive(new URL(upstream.url).hostname)) return text('redirected off archive.org', 403);

    const headers = new Headers(CORS);
    for (const h of ['content-type', 'content-length']) { const v = upstream.headers.get(h); if (v) headers.set(h, v); }
    return new Response(upstream.body, { status: upstream.status, headers });   // streamed straight through
  }
};

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = Number(process.env.PORT || 4173);
const ROOT = path.join(__dirname, 'site');

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml; charset=utf-8',
};

function send(res, status, body, headers = {}) {
  res.writeHead(status, headers);
  res.end(body);
}

http
  .createServer((req, res) => {
    const urlPath = req.url === '/' ? '/index.html' : req.url.split('?')[0];
    const safePath = path.normalize(urlPath).replace(/^(\.\.[/\\])+/, '');
    const filePath = path.join(ROOT, safePath);

    if (!filePath.startsWith(ROOT)) {
      send(res, 403, 'Forbidden');
      return;
    }

    fs.readFile(filePath, (err, data) => {
      if (err) {
        send(res, 404, 'Not found');
        return;
      }

      const ext = path.extname(filePath);
      send(res, 200, data, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
    });
  })
  .listen(PORT, () => {
    console.log(`AgroShield site running at http://127.0.0.1:${PORT}`);
  });

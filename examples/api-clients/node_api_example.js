#!/usr/bin/env node
// Minimal Node.js example calling curllm API using values from examples/.env
// No external dependencies required.

const fs = require('fs');
const path = require('path');
const { URL } = require('url');
const https = require('https');
const http = require('http');

function loadEnv(envPath) {
  try {
    const txt = fs.readFileSync(envPath, 'utf8');
    for (const line of txt.split(/\r?\n/)) {
      if (!line || line.trim().startsWith('#')) continue;
      const idx = line.indexOf('=');
      if (idx === -1) continue;
      const key = line.slice(0, idx).trim();
      const val = line.slice(idx + 1).trim();
      if (!(key in process.env)) process.env[key] = val;
    }
  } catch (_) {}
}

const ENV_PATH = path.join(__dirname, '.env');
if (fs.existsSync(ENV_PATH)) loadEnv(ENV_PATH);

function asBool(v, def = false) {
  if (v == null) return def;
  const s = String(v).toLowerCase();
  return s === '1' || s === 'true' || s === 'yes' || s === 'on';
}

const API_HOST = process.env.CURLLM_API_HOST || 'http://localhost:8000';
const payload = {
  url: process.env.API_URL || 'https://ceneo.pl',
  data: process.env.API_INSTRUCTION || 'Find all products under 150zł and extract names, prices and urls',
  visual_mode: asBool(process.env.API_VISUAL_MODE, false),
  stealth_mode: asBool(process.env.API_STEALTH_MODE, true),
  captcha_solver: asBool(process.env.API_CAPTCHA_SOLVER, true),
  use_bql: asBool(process.env.API_USE_BQL, false),
  headers: {}
};
if (process.env.ACCEPT_LANGUAGE) {
  payload.headers['Accept-Language'] = process.env.ACCEPT_LANGUAGE;
}

async function postJsonFetch(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { raw: text }; }
}

function postJsonHttp(urlStr, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const data = JSON.stringify(body);
    const opts = {
      method: 'POST',
      hostname: u.hostname,
      port: u.port || (u.protocol === 'https:' ? 443 : 80),
      path: u.pathname + (u.search || ''),
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    };
    const mod = u.protocol === 'https:' ? https : http;
    const req = mod.request(opts, (res) => {
      let chunks = '';
      res.setEncoding('utf8');
      res.on('data', (d) => (chunks += d));
      res.on('end', () => {
        try { resolve(JSON.parse(chunks)); } catch { resolve({ raw: chunks }); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

(async () => {
  const endpoint = API_HOST.replace(/\/$/, '') + '/api/execute';
  try {
    let out;
    if (typeof fetch === 'function') {
      out = await postJsonFetch(endpoint, payload);
    } else {
      out = await postJsonHttp(endpoint, payload);
    }
    console.log(JSON.stringify(out, null, 2));
  } catch (e) {
    console.error('Request failed:', e && e.message ? e.message : e);
    process.exit(1);
  }
})();

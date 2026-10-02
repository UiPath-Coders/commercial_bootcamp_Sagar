#!/usr/bin/env node
/**
 * Commercial Bootcamp mock ERP: Lab 3 PO API + Lab 4 browser portal.
 *
 * Local mode is intentionally frictionless. Hosted mode is enabled with
 * BOOTCAMP_AUTH_MODE=required and protects every /api route with a signed,
 * expiring participant token. The browser exchanges the token for a secure
 * HttpOnly cookie; API clients send `Authorization: Bearer <token>`.
 */
import { createServer } from 'node:http';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import { dirname, join, extname, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyAccessToken, createAccessToken } from './auth.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8080);
const AUTH_REQUIRED = String(process.env.BOOTCAMP_AUTH_MODE || 'off').toLowerCase() === 'required';
const SIGNING_SECRET = process.env.BOOTCAMP_SIGNING_SECRET || '';
// Shared cohort passphrase that lets a participant mint their own token from the tracker.
// The signing secret never leaves the server; this key is just a "you're in the workshop" gate.
// The bootcamp key is static and published on the tracker's Lab 3/4 page (ERP_COHORT_KEY in the
// lab-tracker repo), so it is always accepted here regardless of the environment. The ERP holds
// only synthetic data. BOOTCAMP_COHORT_KEY may add a second, environment-specific key (tests).
const STATIC_COHORT_KEY = 'cfo-invoice-2026-bb6579';
const COHORT_KEY = process.env.BOOTCAMP_COHORT_KEY || '';
const COHORT_KEYS = [STATIC_COHORT_KEY, COHORT_KEY].filter(Boolean);
const TOKEN_MINT_MAX_HOURS = Number(process.env.BOOTCAMP_TOKEN_MAX_HOURS || 12);
const SESSION_COOKIE = 'bootcamp_session';
const MAX_BODY_BYTES = Number(process.env.BOOTCAMP_MAX_BODY_BYTES || 65536);
const RATE_LIMIT_PER_MINUTE = Number(process.env.BOOTCAMP_RATE_LIMIT_PER_MINUTE || 120);
const PORTAL_RATE_LIMIT_PER_MINUTE = Number(process.env.BOOTCAMP_PORTAL_RATE_LIMIT_PER_MINUTE || 600);
const LOGIN_LIMIT_PER_MINUTE = Number(process.env.BOOTCAMP_LOGIN_LIMIT_PER_MINUTE || 20);
const PORTAL_USERNAME = 'ap_user';
const PORTAL_PASSWORD = 'passwod';
const ALLOWED_ORIGINS = new Set(
  String(process.env.BOOTCAMP_ALLOWED_ORIGINS || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean),
);

if (AUTH_REQUIRED && Buffer.byteLength(SIGNING_SECRET) < 32) {
  throw new Error('BOOTCAMP_SIGNING_SECRET must contain at least 32 bytes when hosted auth is required');
}

const PO = JSON.parse(readFileSync(join(ROOT, 'data', 'purchase-orders.json'), 'utf8'));
const VENDORS = JSON.parse(readFileSync(join(ROOT, 'data', 'vendors.json'), 'utf8')).vendors;

/** Hosted postings are partitioned by the signed token subject. They remain synthetic and in memory. */
const postingsByParticipant = new Map();
let postingSeq = 1;
const rateWindows = new Map();

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

const SECURITY_HEADERS = {
  'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
  'Referrer-Policy': 'no-referrer',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
};

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function corsHeaders(req) {
  const origin = req.headers.origin;
  if (!origin || !ALLOWED_ORIGINS.has(origin)) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '600',
    Vary: 'Origin',
  };
}

/**
 * The self-service mint endpoint is reachable from the tracker in any browser, so it
 * echoes the caller's origin. It is safe to open because it carries no data and hands
 * back a token only when the shared cohort key matches. The data /api routes stay strict.
 */
function mintCorsHeaders(req) {
  const origin = req.headers.origin;
  if (!origin) return {};
  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '600',
    Vary: 'Origin',
  };
}

function cohortKeyMatches(supplied) {
  const provided = String(supplied ?? '');
  if (!provided) return false;
  const a = Buffer.from(provided);
  return COHORT_KEYS.some((key) => {
    const b = Buffer.from(key);
    return a.length === b.length && timingSafeEqual(a, b);
  });
}

function baseUrl(req) {
  const proto = String(req.headers['x-forwarded-proto'] || 'http').split(',')[0].trim();
  const host = req.headers['x-forwarded-host'] || req.headers.host || `localhost:${PORT}`;
  return `${proto}://${host}`;
}

function send(req, res, status, body, headers = {}) {
  const isJson = typeof body !== 'string' && !Buffer.isBuffer(body);
  const payload = isJson ? JSON.stringify(body, null, 2) : body;
  res.writeHead(status, {
    ...SECURITY_HEADERS,
    ...corsHeaders(req),
    'Content-Type': isJson ? MIME['.json'] : headers['Content-Type'] || 'text/plain; charset=utf-8',
    ...headers,
  });
  res.end(payload);
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let bytes = 0;
    let tooLarge = false;
    req.on('data', (chunk) => {
      bytes += chunk.length;
      if (bytes > MAX_BODY_BYTES) {
        tooLarge = true;
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      if (tooLarge) return reject(new HttpError(413, `Request body exceeds ${MAX_BODY_BYTES} bytes`));
      const raw = Buffer.concat(chunks).toString('utf8');
      if (!raw.trim()) return resolve({});
      try {
        return resolve(JSON.parse(raw));
      } catch {
        return reject(new HttpError(400, 'Body is not valid JSON'));
      }
    });
    req.on('error', reject);
  });
}

function parseCookies(req) {
  return Object.fromEntries(
    String(req.headers.cookie || '')
      .split(';')
      .map((part) => part.trim())
      .filter(Boolean)
      .map((part) => {
        const separator = part.indexOf('=');
        return separator === -1 ? [part, ''] : [part.slice(0, separator), decodeURIComponent(part.slice(separator + 1))];
      }),
  );
}

function accessToken(req) {
  const authorization = String(req.headers.authorization || '');
  if (authorization.toLowerCase().startsWith('bearer ')) return authorization.slice(7).trim();
  const urlToken = new URL(req.url, 'http://localhost').searchParams.get('access_token');
  if (urlToken) return urlToken;
  return parseCookies(req)[SESSION_COOKIE] || '';
}

function identity(req) {
  if (!AUTH_REQUIRED) return { ok: true, participantId: 'local', expiresAt: null };
  return verifyAccessToken(accessToken(req), SIGNING_SECRET);
}

function remoteKey(req) {
  const forwarded = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  return forwarded || req.socket.remoteAddress || 'unknown';
}

function withinRateLimit(key, limit) {
  const minute = Math.floor(Date.now() / 60000);
  const previous = rateWindows.get(key);
  const current = previous?.minute === minute ? previous : { minute, count: 0 };
  current.count += 1;
  rateWindows.set(key, current);
  if (rateWindows.size > 2000) {
    for (const [entryKey, entry] of rateWindows) if (entry.minute < minute - 1) rateWindows.delete(entryKey);
  }
  return current.count <= limit;
}

function requireIdentity(req, res) {
  const auth = identity(req);
  if (!auth.ok) {
    send(req, res, 401, { error: 'Authentication required', reason: auth.reason });
    return null;
  }
  const isPortalSession = auth.participantId.startsWith('portal-');
  const rateKey = isPortalSession ? `api:portal:${remoteKey(req)}` : `api:${auth.participantId}`;
  const rateLimit = isPortalSession ? PORTAL_RATE_LIMIT_PER_MINUTE : RATE_LIMIT_PER_MINUTE;
  if (!withinRateLimit(rateKey, rateLimit)) {
    send(req, res, 429, { error: 'Too many requests; retry after the next minute' }, { 'Retry-After': '60' });
    return null;
  }
  return auth;
}

function participantPostings(participantId) {
  if (!postingsByParticipant.has(participantId)) postingsByParticipant.set(participantId, []);
  return postingsByParticipant.get(participantId);
}

const norm = (value) => String(value ?? '').trim().toLowerCase();

function searchVendors(query) {
  const needle = norm(query);
  if (!needle) return [];
  return VENDORS.filter((vendor) => norm(vendor.vendorName).includes(needle) || norm(vendor.taxId) === needle);
}

function lookupPo(poNumber) {
  const key = String(poNumber ?? '').trim().toUpperCase();
  return { po: (PO.responses[key] ?? PO.default).po };
}

function serveStatic(req, res, urlPath) {
  const rel = normalize(urlPath.replace(/^\/portal\/?/, '') || 'index.html').replace(/^(\.\.[/\\])+/, '');
  const publicRoot = join(ROOT, 'public');
  const file = join(publicRoot, rel === '' || rel === '.' ? 'index.html' : rel);
  if (!file.startsWith(publicRoot) || !existsSync(file)) return send(req, res, 404, 'Not found');
  const ext = extname(file);
  return send(req, res, 200, readFileSync(file), { 'Content-Type': MIME[ext] || 'application/octet-stream' });
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const { pathname } = url;

  try {
    if (req.method === 'OPTIONS') {
      // The self-service mint endpoint is deliberately open to any browser origin.
      if (pathname === '/auth/token') return send(req, res, 204, '', mintCorsHeaders(req));
      const origin = req.headers.origin;
      if (origin && !ALLOWED_ORIGINS.has(origin)) return send(req, res, 403, { error: 'Origin is not allowed' });
      return send(req, res, 204, '');
    }

    // Public liveness endpoint. It contains no private data and is used by Cloud Run and the labs.
    if (pathname === '/health' && req.method === 'GET') return send(req, res, 200, PO.health);

    // Self-service token mint for the tracker widget: cohort key in, signed participant token out.
    // The signing secret stays on the server; participants only ever hold the cohort key and their token.
    if (pathname === '/auth/token' && req.method === 'POST') {
      const cors = mintCorsHeaders(req);
      if (!withinRateLimit(`mint:${remoteKey(req)}`, LOGIN_LIMIT_PER_MINUTE)) {
        return send(req, res, 429, { error: 'Too many token requests; retry after the next minute' }, { ...cors, 'Retry-After': '60' });
      }
      if (Buffer.byteLength(SIGNING_SECRET) < 32) {
        return send(req, res, 503, { error: 'Token minting is not configured on this server' }, cors);
      }
      const body = await readJson(req);
      if (!cohortKeyMatches(body.cohortKey)) {
        return send(req, res, 401, { error: 'Invalid cohort key' }, cors);
      }
      const hours = Math.min(TOKEN_MINT_MAX_HOURS, Math.max(1, Number(body.hours) || TOKEN_MINT_MAX_HOURS));
      let token;
      try {
        token = createAccessToken({ participantId: body.participantId, secret: SIGNING_SECRET, ttlHours: hours });
      } catch (error) {
        return send(req, res, 400, { error: error.message }, cors);
      }
      const verified = verifyAccessToken(token, SIGNING_SECRET);
      const root = baseUrl(req);
      return send(req, res, 200, {
        participantId: verified.participantId,
        token,
        expiresAt: verified.expiresAt,
        apiBaseUrl: root,
        apiUrl: `${root}/api/po-lookup?access_token=${encodeURIComponent(token)}`,
        portalUrl: `${root}/portal/`,
      }, cors);
    }

    // The browser portal uses intentionally shared workshop credentials. The data is
    // synthetic; the machine-facing API remains protected by signed participant URLs.
    if (pathname === '/auth/login' && req.method === 'POST') {
      if (!withinRateLimit(`login:${remoteKey(req)}`, LOGIN_LIMIT_PER_MINUTE)) {
        return send(req, res, 429, { error: 'Too many sign-in attempts; retry after the next minute' }, { 'Retry-After': '60' });
      }
      if (!AUTH_REQUIRED) return send(req, res, 200, { authenticated: true, participantId: 'local', displayName: PORTAL_USERNAME, expiresAt: null });
      const body = await readJson(req);
      if (String(body.username || '') !== PORTAL_USERNAME || String(body.password || '') !== PORTAL_PASSWORD) {
        return send(req, res, 401, { error: 'The training username or password is incorrect.' });
      }
      const participantId = `portal-${randomBytes(8).toString('hex')}`;
      const token = createAccessToken({ participantId, secret: SIGNING_SECRET, ttlHours: TOKEN_MINT_MAX_HOURS });
      const auth = verifyAccessToken(token, SIGNING_SECRET);
      const remainingSeconds = Math.max(1, Math.floor((new Date(auth.expiresAt).getTime() - Date.now()) / 1000));
      return send(req, res, 200, { authenticated: true, participantId, displayName: PORTAL_USERNAME, expiresAt: auth.expiresAt }, {
        'Set-Cookie': `${SESSION_COOKIE}=${encodeURIComponent(token)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${remainingSeconds}`,
      });
    }

    // Backward compatibility for already-issued participant portal links.
    if (pathname === '/auth/session' && req.method === 'POST') {
      if (!withinRateLimit(`login:${remoteKey(req)}`, LOGIN_LIMIT_PER_MINUTE)) {
        return send(req, res, 429, { error: 'Too many sign-in attempts; retry after the next minute' }, { 'Retry-After': '60' });
      }
      if (!AUTH_REQUIRED) return send(req, res, 200, { authenticated: true, participantId: 'local', expiresAt: null });
      const body = await readJson(req);
      const auth = verifyAccessToken(body.accessToken, SIGNING_SECRET);
      if (!auth.ok) return send(req, res, 401, { error: 'Invalid or expired access token', reason: auth.reason });
      const remainingSeconds = Math.max(1, Math.floor((new Date(auth.expiresAt).getTime() - Date.now()) / 1000));
      return send(req, res, 200, { authenticated: true, participantId: auth.participantId, expiresAt: auth.expiresAt }, {
        'Set-Cookie': `${SESSION_COOKIE}=${encodeURIComponent(body.accessToken)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${remainingSeconds}`,
      });
    }

    if (pathname === '/auth/status' && req.method === 'GET') {
      const auth = identity(req);
      if (!auth.ok) return send(req, res, 401, { authenticated: false, reason: auth.reason });
      return send(req, res, 200, {
        authenticated: true,
        participantId: auth.participantId,
        displayName: auth.participantId.startsWith('portal-') ? PORTAL_USERNAME : auth.participantId,
        expiresAt: auth.expiresAt,
      });
    }

    if (pathname === '/auth/logout' && req.method === 'POST') {
      return send(req, res, 200, { ok: true }, {
        'Set-Cookie': `${SESSION_COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`,
      });
    }

    if (pathname.startsWith('/api/')) {
      const auth = requireIdentity(req, res);
      if (!auth) return;

      if (pathname === '/api/po-lookup' && req.method === 'POST') {
        const body = await readJson(req);
        if (!body.poNumber) return send(req, res, 400, { error: 'poNumber is required' });
        return send(req, res, 200, lookupPo(body.poNumber));
      }
      if (pathname.startsWith('/api/po-lookup/') && req.method === 'GET') {
        return send(req, res, 200, lookupPo(decodeURIComponent(pathname.slice('/api/po-lookup/'.length))));
      }
      if (pathname === '/api/vendors' && req.method === 'GET') {
        const query = url.searchParams.get('q');
        return send(req, res, 200, { vendors: query === null ? VENDORS : searchVendors(query) });
      }
      if (pathname === '/api/postings' && req.method === 'GET') {
        return send(req, res, 200, { postings: participantPostings(auth.participantId) });
      }
      if (pathname === '/api/postings' && req.method === 'POST') {
        const body = await readJson(req);
        const required = ['vendorId', 'invoiceNumber', 'poNumber', 'totalAmount'];
        const missing = required.filter((key) => body[key] === undefined || body[key] === '');
        if (missing.length) return send(req, res, 400, { error: `Missing fields: ${missing.join(', ')}` });
        const vendor = VENDORS.find((item) => item.vendorId === body.vendorId);
        if (!vendor) return send(req, res, 404, { error: `Unknown vendorId ${String(body.vendorId).slice(0, 80)}` });
        const invoiceNumber = String(body.invoiceNumber).trim();
        const poNumber = String(body.poNumber).trim().toUpperCase();
        const totalAmount = Number(body.totalAmount);
        if (!invoiceNumber || invoiceNumber.length > 100 || !poNumber || poNumber.length > 100) {
          return send(req, res, 400, { error: 'Invoice Number and PO Number must be 1-100 characters' });
        }
        if (!Number.isFinite(totalAmount) || totalAmount <= 0 || totalAmount > 10_000_000) {
          return send(req, res, 400, { error: 'Total Amount must be a positive number no greater than 10000000' });
        }
        const posting = {
          postingId: `AP-${new Date().getFullYear()}-${String(postingSeq++).padStart(5, '0')}`,
          status: 'SUBMITTED_FOR_PAYMENT',
          vendorId: vendor.vendorId,
          vendorName: vendor.vendorName,
          invoiceNumber,
          poNumber,
          totalAmount,
          currency: vendor.currency,
          submittedAt: new Date().toISOString(),
        };
        participantPostings(auth.participantId).unshift(posting);
        return send(req, res, 201, posting);
      }
      if (pathname === '/api/postings' && req.method === 'DELETE') {
        participantPostings(auth.participantId).length = 0;
        return send(req, res, 200, { ok: true, cleared: true });
      }
      return send(req, res, 404, { error: 'API route not found' });
    }

    if (pathname === '/' || pathname === '/portal') {
      res.writeHead(302, { ...SECURITY_HEADERS, Location: '/portal/' });
      return res.end();
    }
    if (pathname.startsWith('/portal/')) return serveStatic(req, res, pathname);

    return send(req, res, 404, { error: 'Not found', hint: 'API: GET /health, POST /api/po-lookup. Portal: /portal/' });
  } catch (error) {
    const status = error instanceof HttpError ? error.status : 500;
    const message = status >= 500 ? 'Internal server error' : error.message;
    if (status >= 500) console.error(error);
    return send(req, res, status, { error: message });
  }
});

server.listen(PORT, () => {
  console.log(`Mock ERP (Globex Manufacturing) listening on http://localhost:${PORT}`);
  console.log(`  Security: ${AUTH_REQUIRED ? 'signed participant tokens required' : 'local open mode'}`);
  console.log(`  API     → GET  http://localhost:${PORT}/health`);
  console.log(`          → POST http://localhost:${PORT}/api/po-lookup`);
  console.log(`  Portal  → http://localhost:${PORT}/portal/`);
});

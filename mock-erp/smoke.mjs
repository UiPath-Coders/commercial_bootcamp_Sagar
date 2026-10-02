/** Smoke suite for both clone-friendly local mode and protected Cloud Run mode. */
import { spawn } from 'node:child_process';
import { createAccessToken } from './auth.mjs';

const SECRET = 'test-only-signing-secret-with-more-than-32-bytes';
const COHORT = 'test-cohort-key';

const expect = (condition, message) => {
  if (!condition) throw new Error(`FAIL: ${message}`);
  console.log(`ok  ${message}`);
};

async function withServer(port, env, test) {
  const server = spawn(process.execPath, ['server.mjs'], {
    env: { ...process.env, PORT: String(port), ...env },
    stdio: 'ignore',
  });
  const base = `http://localhost:${port}`;
  try {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      try {
        if ((await fetch(`${base}/health`)).ok) break;
      } catch {
        // The child process is still starting.
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    await test(base);
  } finally {
    server.kill();
  }
}

async function localMode(base) {
  const health = await (await fetch(`${base}/health`)).json();
  expect(health.ok === true && health.service === 'erp-po-api', 'local: GET /health');

  const hit = await (await fetch(`${base}/api/po-lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vendorName: 'Vertex Analytics Corp.', poNumber: 'PO-2026-0405', invoiceTotal: 22700, currency: 'USD' }),
  })).json();
  expect(hit.po.found === true && hit.po.openAmount === 22700, 'local: POST /api/po-lookup known PO');

  const miss = await (await fetch(`${base}/api/po-lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ poNumber: 'PO-0000-0000' }),
  })).json();
  expect(miss.po.found === false && miss.po.openAmount === 0, 'local: POST /api/po-lookup unknown PO');

  const vendors = await (await fetch(`${base}/api/vendors?q=pacific`)).json();
  expect(vendors.vendors.length === 1 && vendors.vendors[0].vendorId === 'V-1010', 'local: GET /api/vendors?q=pacific');

  const posted = await (await fetch(`${base}/api/postings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vendorId: 'V-1001', invoiceNumber: 'NW-88214', poNumber: 'PO-2026-0431', totalAmount: 4155.4 }),
  })).json();
  expect(posted.status === 'SUBMITTED_FOR_PAYMENT' && posted.postingId.startsWith('AP-'), 'local: POST /api/postings');

  const portal = await fetch(`${base}/portal/`);
  const html = await portal.text();
  expect(portal.status === 200 && html.includes('id="btn-post-invoice"') && html.includes('id="auth-form"'), 'local: GET /portal/ serves the AP portal');

  const cleared = await (await fetch(`${base}/api/postings`, { method: 'DELETE' })).json();
  expect(cleared.cleared === true, 'local: DELETE /api/postings');
}

async function protectedMode(base) {
  const tokenAxel = createAccessToken({ participantId: 'axel', secret: SECRET, ttlHours: 1 });
  const tokenMaria = createAccessToken({ participantId: 'maria', secret: SECRET, ttlHours: 1 });
  const bearerAxel = { Authorization: `Bearer ${tokenAxel}` };
  const bearerMaria = { Authorization: `Bearer ${tokenMaria}` };

  const health = await fetch(`${base}/health`);
  expect(health.ok, 'hosted: health remains public');
  expect(health.headers.get('content-security-policy')?.includes("default-src 'self'"), 'hosted: security headers are present');

  const unauthenticated = await fetch(`${base}/api/vendors`);
  expect(unauthenticated.status === 401, 'hosted: API rejects requests without a token');

  const portalLogin = await fetch(`${base}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'ap_user', password: 'passwod' }),
  });
  const portalCookie = portalLogin.headers.get('set-cookie');
  expect(portalLogin.ok && portalCookie?.includes('HttpOnly') && portalCookie.includes('Secure'), 'hosted: shared portal credentials create a secure session');

  const rejectedPortalLogin = await fetch(`${base}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'ap_user', password: 'wrong' }),
  });
  expect(rejectedPortalLogin.status === 401, 'hosted: portal rejects an incorrect training password');

  const lookup = await fetch(`${base}/api/po-lookup`, {
    method: 'POST',
    headers: { ...bearerAxel, 'Content-Type': 'application/json' },
    body: JSON.stringify({ poNumber: 'PO-2026-0431' }),
  });
  expect(lookup.ok && (await lookup.json()).po.found === true, 'hosted: bearer token authorizes Lab 3');

  const signIn = await fetch(`${base}/auth/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ accessToken: tokenAxel }),
  });
  const cookie = signIn.headers.get('set-cookie');
  expect(signIn.ok && cookie?.includes('HttpOnly') && cookie.includes('Secure') && cookie.includes('SameSite=Lax'), 'hosted: portal token becomes a secure cookie');

  const cookieStatus = await fetch(`${base}/auth/status`, { headers: { Cookie: cookie.split(';')[0] } });
  expect(cookieStatus.ok && (await cookieStatus.json()).participantId === 'axel', 'hosted: cookie identifies the participant');

  const postingBody = JSON.stringify({ vendorId: 'V-1001', invoiceNumber: 'NW-88214', poNumber: 'PO-2026-0431', totalAmount: 4155.4 });
  await fetch(`${base}/api/postings`, { method: 'POST', headers: { ...bearerAxel, 'Content-Type': 'application/json' }, body: postingBody });
  const axelPostings = await (await fetch(`${base}/api/postings`, { headers: bearerAxel })).json();
  const mariaPostings = await (await fetch(`${base}/api/postings`, { headers: bearerMaria })).json();
  expect(axelPostings.postings.length === 1 && mariaPostings.postings.length === 0, 'hosted: postings are isolated per participant');

  const allowed = await fetch(`${base}/api/vendors`, { headers: { ...bearerAxel, Origin: 'https://allowed.example' } });
  expect(allowed.headers.get('access-control-allow-origin') === 'https://allowed.example', 'hosted: configured CORS origin is echoed exactly');
  const blockedPreflight = await fetch(`${base}/api/vendors`, { method: 'OPTIONS', headers: { Origin: 'https://evil.example' } });
  expect(blockedPreflight.status === 403 && !blockedPreflight.headers.has('access-control-allow-origin'), 'hosted: unconfigured browser origin is rejected');

  const oversized = await fetch(`${base}/api/po-lookup`, {
    method: 'POST',
    headers: { ...bearerAxel, 'Content-Type': 'application/json' },
    body: JSON.stringify({ poNumber: 'x'.repeat(2048) }),
  });
  expect(oversized.status === 413, 'hosted: request-size limit is enforced');

  // Self-service token mint (the tracker widget's endpoint).
  const minted = await fetch(`${base}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Origin: 'https://tracker.example' },
    body: JSON.stringify({ cohortKey: COHORT, participantId: 'nina@uipath.com', hours: 8 }),
  });
  const mintedBody = await minted.json();
  expect(minted.ok && mintedBody.token && mintedBody.participantId === 'nina@uipath.com', 'hosted: mint issues a token for a valid cohort key');
  expect(minted.headers.get('access-control-allow-origin') === 'https://tracker.example', 'hosted: mint echoes the tracker origin (open CORS)');
  expect(mintedBody.portalUrl === `${base}/portal/`, 'hosted: mint returns the generic portal URL');
  expect(typeof mintedBody.apiUrl === 'string' && mintedBody.apiUrl.includes('/api/po-lookup?access_token='), 'hosted: mint returns a signed API URL');

  const mintedLookup = await fetch(`${base}/api/po-lookup`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${mintedBody.token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ poNumber: 'PO-2026-0431' }),
  });
  expect(mintedLookup.ok && (await mintedLookup.json()).po.found === true, 'hosted: a minted token authorizes the API');

  const urlLookup = await fetch(mintedBody.apiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ poNumber: 'PO-2026-0431' }),
  });
  expect(urlLookup.ok && (await urlLookup.json()).po.found === true, 'hosted: the signed API URL authorizes a lookup without a separate header');

  const wrongKey = await fetch(`${base}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cohortKey: 'not-the-key', participantId: 'nina@uipath.com' }),
  });
  expect(wrongKey.status === 401, 'hosted: mint rejects a wrong cohort key');

  const badId = await fetch(`${base}/auth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cohortKey: COHORT, participantId: 'bad id!!' }),
  });
  expect(badId.status === 400, 'hosted: mint rejects a malformed participant id');
}

try {
  await withServer(18080, { BOOTCAMP_AUTH_MODE: 'off' }, localMode);
  await withServer(18081, {
    BOOTCAMP_AUTH_MODE: 'required',
    BOOTCAMP_SIGNING_SECRET: SECRET,
    BOOTCAMP_COHORT_KEY: COHORT,
    BOOTCAMP_ALLOWED_ORIGINS: 'https://allowed.example',
    BOOTCAMP_MAX_BODY_BYTES: '1024',
    BOOTCAMP_RATE_LIMIT_PER_MINUTE: '1000',
  }, protectedMode);
  console.log('\nmock-erp smoke suite passed in local and protected modes');
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}

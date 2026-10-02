import { createHmac, timingSafeEqual } from 'node:crypto';

const TOKEN_VERSION = 1;

function encode(value) {
  return Buffer.from(value).toString('base64url');
}

function signature(payload, secret) {
  return createHmac('sha256', secret).update(payload).digest('base64url');
}

function safeEqual(left, right) {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function createAccessToken({ participantId, secret, expiresAt, ttlHours = 24 }) {
  const sub = String(participantId || '').trim();
  if (!sub || sub.length > 80 || !/^[a-zA-Z0-9._@-]+$/.test(sub)) {
    throw new Error('participantId must be 1-80 characters using letters, numbers, dot, underscore, @, or hyphen');
  }
  if (!secret || Buffer.byteLength(secret) < 32) {
    throw new Error('The signing secret must contain at least 32 bytes');
  }
  const now = Math.floor(Date.now() / 1000);
  const exp = expiresAt ? Math.floor(new Date(expiresAt).getTime() / 1000) : now + Number(ttlHours) * 3600;
  if (!Number.isFinite(exp) || exp <= now) throw new Error('Token expiration must be in the future');
  const payload = encode(JSON.stringify({ v: TOKEN_VERSION, sub, iat: now, exp }));
  return `${payload}.${signature(payload, secret)}`;
}

export function verifyAccessToken(token, secret, now = Math.floor(Date.now() / 1000)) {
  if (!secret || Buffer.byteLength(secret) < 32) return { ok: false, reason: 'server_not_configured' };
  const [payload, suppliedSignature, extra] = String(token || '').split('.');
  if (!payload || !suppliedSignature || extra || !safeEqual(signature(payload, secret), suppliedSignature)) {
    return { ok: false, reason: 'invalid_token' };
  }
  try {
    const claims = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    if (claims.v !== TOKEN_VERSION || typeof claims.sub !== 'string' || !claims.sub || !Number.isFinite(claims.exp)) {
      return { ok: false, reason: 'invalid_token' };
    }
    if (claims.exp <= now) return { ok: false, reason: 'expired_token' };
    return { ok: true, participantId: claims.sub, expiresAt: new Date(claims.exp * 1000).toISOString(), claims };
  } catch {
    return { ok: false, reason: 'invalid_token' };
  }
}

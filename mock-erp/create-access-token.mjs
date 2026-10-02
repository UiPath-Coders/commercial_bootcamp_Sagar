#!/usr/bin/env node
import { createAccessToken } from './auth.mjs';

const args = Object.fromEntries(process.argv.slice(2).map((part, index, all) => {
  if (!part.startsWith('--')) return [part, true];
  const key = part.slice(2);
  const next = all[index + 1];
  return [key, next && !next.startsWith('--') ? next : true];
}));

if (!args.participant || args.help) {
  console.error('Usage: BOOTCAMP_SIGNING_SECRET=... node create-access-token.mjs --participant <id> [--hours 24] [--base-url https://service]');
  process.exit(args.help ? 0 : 2);
}

const token = createAccessToken({
  participantId: args.participant,
  secret: process.env.BOOTCAMP_SIGNING_SECRET,
  ttlHours: Number(args.hours || 24),
});

console.log(`Participant: ${args.participant}`);
console.log(`Access token: ${token}`);
if (args['base-url']) {
  const baseUrl = String(args['base-url']).replace(/\/$/, '');
  console.log(`API base URL: ${baseUrl}`);
  console.log(`Signed API URL: ${baseUrl}/api/po-lookup?access_token=${encodeURIComponent(token)}`);
  console.log(`Portal URL: ${baseUrl}/portal/`);
  console.log('Portal login: ap_user / passwod');
}

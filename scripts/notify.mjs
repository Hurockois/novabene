// Envoie l'avis de parution aux appareils abonnés (Web Push).
// Appelé par .github/workflows/avis.yml après chaque nouvelle édition.
import { readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import webpush from 'web-push';

const pub = process.env.VAPID_PUBLIC_KEY;
const priv = process.env.VAPID_PRIVATE_KEY;
const raw = (process.env.PUSH_SUBSCRIPTIONS || '').trim();
if (!priv || !raw) { console.log('Avis désactivés : secrets VAPID_PRIVATE_KEY ou PUSH_SUBSCRIPTIONS absents.'); process.exit(0); }

let subs = [];
try { const j = JSON.parse(raw); subs = Array.isArray(j) ? j : [j]; }
catch { subs = raw.split(/\n+/).filter(Boolean).map((l) => JSON.parse(l)); }

const manual = process.env.GITHUB_EVENT_NAME === 'workflow_dispatch';
const changed = manual ? ['index.html'] : execSync('git diff --name-only HEAD~1 HEAD').toString().split('\n');
const editions = [];
if (changed.includes('index.html')) editions.push(['index.html', 'Novabene · Édition du matin', 'novabene-matin']);
if (changed.includes('soir.html')) editions.push(['soir.html', 'Novabene · Édition du soir', 'novabene-soir']);
if (!editions.length) { console.log('Aucune nouvelle édition.'); process.exit(0); }

const strip = (s) => s.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
webpush.setVapidDetails('https://hurockois.github.io/novabene/', pub, priv);

// Attendre que GitHub Pages serve la nouvelle version avant de prévenir,
// sinon l'avis ouvre l'ancienne édition.
const SITE = 'https://hurockois.github.io/novabene/';
async function attendreDeploiement(file, html) {
  const marque = (html.match(/<h2[^>]*>([\s\S]*?)<\/h2>/g) || []).slice(-3).join('') || html.slice(-500);
  for (let i = 0; i < 40; i++) {
    try {
      const r = await fetch(SITE + file + '?v=' + Date.now(), { cache: 'no-store' });
      if (r.ok && (await r.text()).includes(marque)) { console.log(`${file} en ligne après ${i * 15} s`); return; }
    } catch (_) {}
    await new Promise((res) => setTimeout(res, 15000));
  }
  console.log(`${file} : déploiement non confirmé après 10 min, envoi quand même`);
}

let failures = 0;
for (const [file, title, tag] of editions) {
  const html = readFileSync(file, 'utf8');
  if (!manual) await attendreDeploiement(file, html);
  const art = html.match(/<article[^>]*>[\s\S]*?<h2[^>]*>([\s\S]*?)<\/h2>/);
  const body = (manual ? 'Essai des avis de parution — ' : '') + (art ? strip(art[1]) : 'Une nouvelle édition vient de paraître.');
  const payload = JSON.stringify({ title, body, tag, url: './' + file });
  for (const s of subs) {
    try { await webpush.sendNotification(s, payload, { TTL: 6 * 3600, urgency: 'normal' }); console.log(`Avis envoyé : ${title} — ${body}`); }
    catch (e) { failures++; console.error(`Échec (${e.statusCode || '?'}) : ${e.body || e.message}`); }
  }
}
if (failures === subs.length * editions.length) process.exit(1);

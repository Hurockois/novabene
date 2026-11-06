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

const changed = execSync('git diff --name-only HEAD~1 HEAD').toString().split('\n');
const editions = [];
if (changed.includes('index.html')) editions.push(['index.html', 'Novabene · Édition du matin', 'novabene-matin']);
if (changed.includes('soir.html')) editions.push(['soir.html', 'Novabene · Édition du soir', 'novabene-soir']);
if (!editions.length) { console.log('Aucune nouvelle édition.'); process.exit(0); }

const strip = (s) => s.replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
webpush.setVapidDetails('https://hurockois.github.io/novabene/', pub, priv);

let failures = 0;
for (const [file, title, tag] of editions) {
  const html = readFileSync(file, 'utf8');
  const art = html.match(/<article[^>]*>[\s\S]*?<h2[^>]*>([\s\S]*?)<\/h2>/);
  const body = art ? strip(art[1]) : 'Une nouvelle édition vient de paraître.';
  const payload = JSON.stringify({ title, body, tag, url: './' + file });
  for (const s of subs) {
    try { await webpush.sendNotification(s, payload, { TTL: 6 * 3600, urgency: 'normal' }); console.log(`Avis envoyé : ${title} — ${body}`); }
    catch (e) { failures++; console.error(`Échec (${e.statusCode || '?'}) : ${e.body || e.message}`); }
  }
}
if (failures === subs.length * editions.length) process.exit(1);

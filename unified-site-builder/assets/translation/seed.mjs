// Authored translations only. The site owns publication checks, durable storage and AI fallback.
// No trimming/normalization: a change in the actual source text or public context invalidates a record.
const fail = () => { throw new TypeError('invalid_authored_translation'); };
function validateBlock(block) {
  if (!block || ['siteId', 'contentId', 'blockId', 'sourceLanguage'].some(key =>
    typeof block[key] !== 'string' || !block[key].trim()) ||
    typeof block.text !== 'string' || !block.text.trim() ||
    typeof block.context !== 'string') fail();
}
export async function sourceHash(text, context = '') {
  if (typeof text !== 'string' || typeof context !== 'string') fail();
  const bytes = new TextEncoder().encode(JSON.stringify(['source-v1', text, context]));
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
}
export async function makeAuthoredRecord(block, { targetLanguage = 'zh', translation, origin = 'seed' }) {
  validateBlock(block);
  if (!['seed', 'manual'].includes(origin) || typeof targetLanguage !== 'string' ||
    !targetLanguage.trim() || targetLanguage === block.sourceLanguage ||
    typeof translation !== 'string' || !translation.trim()) fail();
  return { siteId: block.siteId, contentId: block.contentId, blockId: block.blockId,
    sourceLanguage: block.sourceLanguage, targetLanguage,
    sourceHash: await sourceHash(block.text, block.context), translation, origin };
}
const identity = record => JSON.stringify(['authored-v1', record.siteId, record.contentId,
  record.blockId, record.sourceLanguage, record.targetLanguage, record.sourceHash]);
export async function findCurrentAuthored(block, targetLanguage, records) {
  validateBlock(block);
  const wanted = identity({ ...block, targetLanguage, sourceHash: await sourceHash(block.text, block.context) });
  const matches = records.filter(record => record && identity(record) === wanted &&
    ['manual', 'seed'].includes(record.origin) && typeof record.translation === 'string' && record.translation.trim());
  // Storage must uniquely constrain each origin/identity. Reject conflicting duplicate records.
  for (const origin of ['manual', 'seed']) {
    const group = matches.filter(record => record.origin === origin);
    if (new Set(group.map(record => record.translation)).size > 1) fail();
    if (group.length) return { translation: group[0].translation, origin };
  }
  return null; // Caller tries a current AI cache, then the engine; never returns English as a translation.
}
export function seedImportCandidates(existing, incoming) {
  // First initialization only. Persist candidates under a unique constraint/transaction;
  // this pure filter cannot guarantee atomicity across concurrent initializations.
  const seen = new Set(existing.map(identity));
  const additions = [];
  for (const record of incoming) {
    if (!record || record.origin !== 'seed' || typeof record.sourceHash !== 'string' ||
      !/^[a-f0-9]{64}$/.test(record.sourceHash) || typeof record.translation !== 'string' ||
      !record.translation.trim() || ['siteId', 'contentId', 'blockId', 'sourceLanguage', 'targetLanguage']
      .some(key => typeof record[key] !== 'string' || !record[key].trim()) ||
      record.sourceLanguage === record.targetLanguage) fail();
    const key = identity(record);
    if (!seen.has(key)) { additions.push({ ...record }); seen.add(key); }
  }
  return additions;
}

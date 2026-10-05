import { initTranslationEngine } from './engine.mjs';
import { sourceHash, findCurrentAuthored } from './seed.mjs';
import { translationProblems } from './quality.mjs';

// One service per site. Repository methods belong to the site's persistent database.
// withLock must coordinate persistent tasks across instances and recover expired leases.
export function createTranslationService({ siteId, languages, sourceLanguage = 'en', runtime,
  repository, glossary = { version: '1', entries: [] }, protectedTerms = [] }) {
  if (!siteId || !languages?.includes(sourceLanguage)) throw new Error('invalid_site_config');
  for (const method of ['getContent', 'getAuthored', 'getCached', 'putCached', 'withLock',
    'getEngineIdentity', 'putEngineIdentity']) {
    if (typeof repository?.[method] !== 'function') throw new Error('missing_repository_' + method);
  }
  if (typeof runtime?.reserveUsage !== 'function') throw new Error('missing_persistent_budget');
  const engine = initTranslationEngine({ ...runtime, supportedLanguages: languages,
    glossaryVersion: glossary.version });
  async function resolve({ contentId, targetLanguage, revision, blockIds }) {
    if (!languages.includes(targetLanguage)) throw new Error('unsupported_direction');
    const content = await repository.getContent(contentId);
    if (!content || content.status !== 'published') throw new Error('content_not_found');
    if (revision !== undefined && revision !== content.revision) return { status: 'partial',
      blocks: {}, reasonCode: 'stale_revision', revision: content.revision };
    const ids = blockIds ? new Set(blockIds) : null;
    if (ids && [...ids].some(id => !content.blocks.some(b => b.id === id))) throw new Error('invalid_block_ids');
    const blocks = content.blocks.filter(b => !ids || ids.has(b.id));
    if (targetLanguage === sourceLanguage) return { status: 'ready', blocks: Object.fromEntries(blocks.map(b => [b.id, b.text])) };
    const status = engine.engineStatus();
    const identity = status.configured ? status : await repository.getEngineIdentity(siteId);
    const result = {}; const errors = []; let pending = false;
    for (const block of blocks) {
      const authoredBlock = { siteId, contentId, blockId: block.id, sourceLanguage,
        text: block.text, context: block.context || content.context || '' };
      const authored = await findCurrentAuthored(authoredBlock, targetLanguage, await repository.getAuthored(authoredBlock));
      if (authored) { result[block.id] = authored.translation; continue; }
      const hash = await sourceHash(block.text, authoredBlock.context);
      const key = JSON.stringify([siteId, contentId, block.id, sourceLanguage, targetLanguage, hash,
        identity?.model, identity?.engineVersion, glossary.version]);
      const cached = identity ? await repository.getCached(key) : null;
      if (cached && !translationProblems(cached.translation).length) { result[block.id] = cached.translation; continue; }
      if (!status.configured) { errors.push('unconfigured'); continue; }
      try {
        const translated = await repository.withLock(key, async () => {
          const again = await repository.getCached(key);
          if (again && !translationProblems(again.translation).length) return again.translation;
          const [text] = await engine.callEngine([block.text], { sourceLanguage, targetLanguage,
            protectedTerms, glossary: glossary.entries, scope: content.kind || 'global', context: authoredBlock.context });
          const current = await repository.getContent(contentId);
          const currentBlock = current?.blocks?.find(b => b.id === block.id);
          if (current?.status !== 'published' || !currentBlock ||
              await sourceHash(currentBlock.text, currentBlock.context || current.context || '') !== hash) throw new Error('stale_revision');
          await repository.putCached(key, { translation: text, sourceHash: hash, targetLanguage,
            engine: status, glossaryVersion: glossary.version });
          await repository.putEngineIdentity(siteId, status);
          return text;
        });
        if (translated === undefined) pending = true; else result[block.id] = translated;
      } catch (error) { errors.push(error.code || error.message || 'provider_error'); }
    }
    const count = Object.keys(result).length;
    return { status: count === blocks.length ? 'ready' : count ? 'partial' : pending ? 'pending' :
      errors.every(e => e === 'unconfigured') ? 'unconfigured' : 'failed',
      blocks: result, revision: content.revision, engine: status,
      reasonCode: errors[0], retryAfterMs: pending ? 2000 : 0, qualityVerified: false };
  }
  return { resolve, engineStatus: engine.engineStatus };
}

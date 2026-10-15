// Backward-compatible content-model extensions for products, pages and articles.
// Existing items keep working: these helpers only add fields, never rename or drop them.

const LIMITS = {
  gallery: 12,
  specs: 80,
  faqs: 30,
  highlights: 12,
  options: 20,
  url: 2000,
  short: 400,
  long: 4000
};

function trimmed(value, max, label) {
  if (typeof value !== 'string') throw Object.assign(new Error('invalid_field:' + label), { code: 'invalid_field' });
  const out = value.trim();
  if (out.length > max) throw Object.assign(new Error('field_too_long:' + label), { code: 'field_too_long' });
  return out;
}

function optional(value, max, label) {
  if (value === undefined || value === null || value === '') return '';
  return trimmed(value, max, label);
}

function asArray(value, label, max) {
  if (value === undefined || value === null) return null;
  if (!Array.isArray(value)) throw Object.assign(new Error('invalid_field:' + label), { code: 'invalid_field' });
  if (value.length > max) throw Object.assign(new Error('too_many:' + label), { code: 'too_many' });
  return value;
}

function safeUrl(value, label) {
  const text = optional(value, LIMITS.url, label);
  if (!text) return '';
  if (text.startsWith('//') || !/^(\/|https?:\/\/)/.test(text)) throw Object.assign(new Error('invalid_url:' + label), { code: 'invalid_url' });
  return text;
}

export function normalizeGallery(value) {
  const list = asArray(value, 'gallery', LIMITS.gallery);
  if (!list) return [];
  return list.map((row, i) => {
    if (!row || typeof row !== 'object') throw Object.assign(new Error('invalid_field:gallery'), { code: 'invalid_field' });
    const url = safeUrl(row.url, 'gallery.url');
    if (!url) throw Object.assign(new Error('empty_url:gallery'), { code: 'invalid_field' });
    return { url, alt: optional(row.alt, LIMITS.short, 'gallery.alt'), caption: optional(row.caption, LIMITS.short, 'gallery.caption') };
  });
}

export function normalizeSpecs(value) {
  const list = asArray(value, 'specs', LIMITS.specs);
  if (!list) return [];
  return list.map(row => {
    if (!row || typeof row !== 'object') throw Object.assign(new Error('invalid_field:specs'), { code: 'invalid_field' });
    const label = trimmed(row.label ?? '', LIMITS.short, 'specs.label');
    const val = trimmed(String(row.value ?? ''), LIMITS.short, 'specs.value');
    if (!label && !val) throw Object.assign(new Error('empty_spec'), { code: 'invalid_field' });
    return { group: optional(row.group, 80, 'specs.group'), label, value: val, unit: optional(row.unit, 40, 'specs.unit') };
  });
}

export function normalizeFaqs(value) {
  const list = asArray(value, 'faqs', LIMITS.faqs);
  if (!list) return [];
  return list.map(row => {
    if (!row || typeof row !== 'object') throw Object.assign(new Error('invalid_field:faqs'), { code: 'invalid_field' });
    const q = trimmed(row.q ?? '', LIMITS.short, 'faqs.q');
    const a = trimmed(row.a ?? '', LIMITS.long, 'faqs.a');
    if (!q) throw Object.assign(new Error('empty_faq_question'), { code: 'invalid_field' });
    return { q, a };
  });
}

export function normalizeHighlights(value) {
  const list = asArray(value, 'highlights', LIMITS.highlights);
  if (!list) return [];
  return list.map((row, i) => trimmed(typeof row === 'string' ? row : String(row?.text ?? ''), LIMITS.short, 'highlights'));
}

export function normalizeOptions(value) {
  const list = asArray(value, 'options', LIMITS.options);
  if (!list) return [];
  return list.map(row => {
    if (!row || typeof row !== 'object') throw Object.assign(new Error('invalid_field:options'), { code: 'invalid_field' });
    return { label: trimmed(row.label ?? '', LIMITS.short, 'options.label'), value: optional(row.value, LIMITS.short, 'options.value') };
  });
}

// Fields every kind may carry. Pages use `sections`; products add specs/faqs/gallery.
const EXTENSION_FIELDS = {
  gallery: normalizeGallery,
  specs: normalizeSpecs,
  faqs: normalizeFaqs,
  highlights: normalizeHighlights,
  options: normalizeOptions
};

export const extensionFieldNames = Object.keys(EXTENSION_FIELDS);

// Merge administrable extension fields into an item. Unknown field names are ignored
// rather than rejected so older admins and scripts keep working.
export function applyExtensions(target, input) {
  for (const [name, normalize] of Object.entries(EXTENSION_FIELDS)) {
    if (input[name] === undefined) continue;
    target[name] = normalize(input[name]);
  }
  if (input.compareGroup !== undefined) target.compareGroup = optional(input.compareGroup, 80, 'compareGroup');
  if (input.badge !== undefined) target.badge = optional(input.badge, 40, 'badge');
  return target;
}

export function ensureExtensions(item) {
  return {
    gallery: [],
    specs: [],
    faqs: [],
    highlights: [],
    options: [],
    ...item
  };
}

// Comparison view needs a stable, flat row per product.
export function compareRows(items) {
  const keys = [];
  for (const item of items) for (const spec of ensureExtensions(item).specs) {
    const key = (spec.group || 'General') + '|' + spec.label;
    if (!keys.includes(key)) keys.push(key);
  }
  return keys.map(key => {
    const [group, label] = key.split('|');
    return {
      group,
      label,
      values: items.map(item => {
        const spec = ensureExtensions(item).specs.find(s => (s.group || 'General') === group && s.label === label);
        return spec ? [spec.value, spec.unit].filter(Boolean).join(' ') : '—';
      })
    };
  });
}

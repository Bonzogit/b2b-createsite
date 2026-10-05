// Deterministic checks detect malformed output; they do not certify semantic accuracy.
export function translationProblems(text) {
  if (typeof text !== 'string' || !text.trim()) return ['empty_output'];
  const problems = [];
  if (/[BВ]2[BВ][TТ]_[\w\u0400-\u04ff]+/iu.test(text)) problems.push('placeholder_leftover');
  const words = text.toLocaleLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
  for (let width = 1; width <= 5; width++) {
    for (let i = 0; i + width * 4 <= words.length; i++) {
      const phrase = words.slice(i, i + width).join(' ');
      if ([1, 2, 3].every(n => words.slice(i + n * width, i + (n + 1) * width).join(' ') === phrase)) {
        problems.push('repetitive_output'); return [...new Set(problems)];
      }
    }
  }
  return [...new Set(problems)];
}
export function assertTranslationQuality(text) {
  const problems = translationProblems(text);
  if (problems.length) {
    const error = new Error('quality_rejected'); error.code = 'quality_rejected'; error.problems = problems;
    throw error;
  }
  return text;
}

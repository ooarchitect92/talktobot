import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

const source = readFileSync(new URL('../src/starter-guides.ts', import.meta.url), 'utf8');
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText;
const { copyStarterGuide } = await import('data:text/javascript;base64,' + Buffer.from(output).toString('base64'));
const posts = JSON.parse(readFileSync(new URL('../../backend/src/northstar_api/website_starter_guides.json', import.meta.url), 'utf8'));
const guides = posts.map(({title, ...data}) => ({title, key: data.slug, data}));

test('every guide creates a distinct article and preserves its original content', () => {
  const drafts = guides.map(guide => copyStarterGuide(guide, []));
  assert.equal(new Set(drafts.map(draft => draft.body)).size, 3);
  assert.equal(new Set(drafts.map(draft => draft.title)).size, 3);
  drafts.forEach((draft, index) => {
    assert.equal(draft.body, posts[index].body);
    assert.equal(draft.id, undefined);
    assert.equal(draft.status, undefined);
    draft.tags.push('Independent draft');
    assert.ok(!guides[index].data.tags.includes('Independent draft'));
  });
});

test('reusing a guide avoids an existing article slug and never overwrites it', () => {
  const guide = guides[0];
  const draft = copyStarterGuide(guide, [{slug: guide.data.slug}, {slug: guide.data.slug + '-copy'}]);
  assert.equal(draft.slug, guide.data.slug + '-copy-2');
  assert.ok(draft.slug.length <= 120);
});

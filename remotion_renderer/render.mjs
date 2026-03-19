import fs from 'fs';
import path from 'path';
import {bundle} from '@remotion/bundler';
import {selectComposition, renderMedia, renderStill} from '@remotion/renderer';

const args = process.argv.slice(2);
const arg = (name) => {
  const idx = args.indexOf(name);
  return idx >= 0 ? args[idx + 1] : null;
};

const compositionId = arg('--composition') || 'VerticalClip';
const propsPath = arg('--props');
const outPath = arg('--out');
const thumbPath = arg('--thumb');

if (!propsPath || !outPath || !thumbPath) {
  console.error('Missing required args --props --out --thumb');
  process.exit(1);
}

const inputProps = JSON.parse(fs.readFileSync(propsPath, 'utf8'));
const entryPoint = path.resolve('./src/index.ts');
const bundled = await bundle({entryPoint});
const composition = await selectComposition({serveUrl: bundled, id: compositionId, inputProps});

await renderMedia({
  serveUrl: bundled,
  composition,
  codec: 'h264',
  outputLocation: outPath,
  inputProps,
});

await renderStill({
  serveUrl: bundled,
  composition,
  frame: 30,
  output: thumbPath,
  inputProps,
});

console.log(JSON.stringify({output: outPath, thumbnail: thumbPath}));

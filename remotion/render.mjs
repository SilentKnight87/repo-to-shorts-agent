import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {mkdir, readFile} from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {fileURLToPath} from 'node:url';

const COMPOSITION_ID = 'RepoShortsVideo';

const parseArgs = (argv) => {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === '--input' || token === '--output') {
      const value = argv[index + 1];
      if (!value || value.startsWith('--')) {
        throw new Error(`Missing value for ${token}`);
      }
      args[token.slice(2)] = value;
      index += 1;
    }
  }
  if (!args.input || !args.output) {
    throw new Error(
      'Usage: npm run render:remotion -- --input <manifest.json> --output <demo.mp4>',
    );
  }
  return args;
};

const loadManifest = async (inputPath) => {
  const raw = await readFile(inputPath, 'utf8');
  const manifest = JSON.parse(raw);
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
    throw new Error('Manifest must be a JSON object');
  }
  return manifest;
};

const main = async () => {
  const {input, output} = parseArgs(process.argv.slice(2));
  const inputPath = path.resolve(input);
  const outputPath = path.resolve(output);
  const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const entryPoint = path.join(projectRoot, 'remotion', 'src', 'index.ts');
  const inputProps = await loadManifest(inputPath);

  await mkdir(path.dirname(outputPath), {recursive: true});

  const serveUrl = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });
  const composition = await selectComposition({
    serveUrl,
    id: COMPOSITION_ID,
    inputProps,
  });

  await renderMedia({
    composition,
    serveUrl,
    codec: 'h264',
    outputLocation: outputPath,
    inputProps,
  });
};

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});

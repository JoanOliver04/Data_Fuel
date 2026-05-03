import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const here = dirname(fileURLToPath(import.meta.url));
const publicDir = join(here, "..", "public");
mkdirSync(publicDir, { recursive: true });

const targets = [
  { src: "screenshot-wide.svg", out: "screenshot-wide.png", width: 1280, height: 720 },
  { src: "screenshot-narrow.svg", out: "screenshot-narrow.png", width: 720, height: 1280 },
];

for (const t of targets) {
  const inPath = join(publicDir, t.src);
  const outPath = join(publicDir, t.out);
  await sharp(inPath, { density: 192 })
    .resize(t.width, t.height, { fit: "fill" })
    .png({ compressionLevel: 9 })
    .toFile(outPath);
  console.log(`✓ ${t.out} (${t.width}x${t.height})`);
}

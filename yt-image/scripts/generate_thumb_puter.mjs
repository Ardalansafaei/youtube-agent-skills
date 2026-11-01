#!/usr/bin/env node
/**
 * YouTube thumbnails via Puter.js (puter.ai.txt2img).
 * Stills stay on Pollinations. Prefer this for thumbs when PUTER_AUTH_TOKEN is set.
 *
 *   node generate_thumb_puter.mjs --file prompts.txt --out ./thumbs
 *   node generate_thumb_puter.mjs --prompt "..." --out ./thumbs --name thumb_A
 *
 * Auth: PUTER_AUTH_TOKEN in env or ../.env  (puter.com/dashboard#account)
 * Optional: --browser-auth to open Puter login once.
 */

import { createWriteStream } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";
import { createRequire } from "node:module";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = resolve(__dirname, "..");
const ENV_FILE = join(SKILL_DIR, ".env");
const DEFAULT_MODEL = "gpt-image-2";
const DEFAULT_SIZE = { width: 1280, height: 720 };

async function loadDotEnv(path) {
  try {
    const text = await readFile(path, "utf8");
    for (const raw of text.split(/\r?\n/)) {
      const line = raw.trim();
      if (!line || line.startsWith("#") || !line.includes("=")) continue;
      const i = line.indexOf("=");
      const key = line.slice(0, i).trim();
      let val = line.slice(i + 1).trim().replace(/^['"]|['"]$/g, "");
      if (key && process.env[key] === undefined) process.env[key] = val;
    }
  } catch {
    /* missing .env is fine */
  }
}

function parseArgs(argv) {
  const out = {
    file: null,
    prompt: null,
    out: null,
    name: "thumb_A",
    model: DEFAULT_MODEL,
    width: DEFAULT_SIZE.width,
    height: DEFAULT_SIZE.height,
    quality: "high",
    browserAuth: false,
    testMode: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === "--file") out.file = next();
    else if (a === "--prompt") out.prompt = next();
    else if (a === "--out") out.out = next();
    else if (a === "--name") out.name = next();
    else if (a === "--model") out.model = next();
    else if (a === "--width") out.width = Number(next());
    else if (a === "--height") out.height = Number(next());
    else if (a === "--quality") out.quality = next();
    else if (a === "--browser-auth") out.browserAuth = true;
    else if (a === "--test-mode") out.testMode = true;
    else if (!a.startsWith("-") && !out.prompt) out.prompt = a;
  }
  return out;
}

async function loadPrompts(file) {
  const text = await readFile(file, "utf8");
  const items = [];
  let i = 0;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim().replace(/^\uFEFF/, "");
    if (!line || line.startsWith("#")) continue;
    i += 1;
    if (line.includes("|")) {
      const [name, ...rest] = line.split("|");
      items.push({ name: name.trim(), prompt: rest.join("|").trim() });
    } else {
      items.push({ name: `thumb_${String(i).padStart(2, "0")}`, prompt: line });
    }
  }
  return items;
}

async function initPuter({ browserAuth }) {
  await loadDotEnv(ENV_FILE);
  const require = createRequire(import.meta.url);
  const { init, getAuthToken } = require("@heyputer/puter.js/src/init.cjs");
  let token = (process.env.PUTER_AUTH_TOKEN || "").trim();
  if (!token && browserAuth) {
    console.error("Opening Puter browser login…", { flush: true });
    token = await getAuthToken();
  }
  if (!token) {
    throw new Error(
      "Missing PUTER_AUTH_TOKEN. Create one at https://puter.com/dashboard#account " +
        "and put it in yt-image/.env — or pass --browser-auth"
    );
  }
  return init(token);
}

async function saveImageSrc(src, destPath) {
  if (!src) throw new Error("empty image src from Puter");
  if (typeof src === "string" && src.startsWith("data:")) {
    const m = src.match(/^data:([^;]+);base64,(.+)$/s);
    if (!m) throw new Error("unsupported data URI");
    await writeFile(destPath, Buffer.from(m[2], "base64"));
    return;
  }
  if (typeof src === "string" && /^https?:\/\//i.test(src)) {
    const res = await fetch(src);
    if (!res.ok) throw new Error(`download failed HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    await writeFile(destPath, buf);
    return;
  }
  throw new Error(`unsupported image src type: ${typeof src}`);
}

async function generateOne(puter, item, opts, outDir) {
  const image = await puter.ai.txt2img(item.prompt, {
    model: opts.model,
    quality: opts.quality,
    width: opts.width,
    height: opts.height,
    aspect_ratio: "16:9",
    test_mode: opts.testMode,
  });
  const src = image?.src ?? image?.toString?.() ?? image;
  const dest = join(outDir, `${item.name}.png`);
  await saveImageSrc(String(src), dest);
  const meta = {
    saved: dest,
    provider: "puter",
    model: opts.model,
    size: `${opts.width}x${opts.height}`,
    quality: opts.quality,
    prompt: item.prompt,
    time: new Date().toISOString(),
  };
  await writeFile(`${dest.replace(/\.png$/i, "")}.json`, JSON.stringify(meta, null, 2) + "\n");
  return dest;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.out) {
    console.error("ERROR: --out is required");
    process.exit(1);
  }
  await mkdir(args.out, { recursive: true });

  let items = [];
  if (args.file) items = await loadPrompts(args.file);
  else if (args.prompt) items = [{ name: args.name, prompt: args.prompt }];
  else {
    console.error("ERROR: provide --file or --prompt");
    process.exit(1);
  }

  const puter = await initPuter({ browserAuth: args.browserAuth });
  let ok = 0;
  let fail = 0;
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    console.log(`[${i + 1}/${items.length}] ${item.name} (puter)`);
    try {
      const dest = await generateOne(puter, item, args, resolve(args.out));
      console.log(dest);
      ok += 1;
    } catch (e) {
      console.error(`ERROR: ${e?.message || e}`);
      fail += 1;
    }
  }
  console.log(`SUMMARY ok=${ok} fail=${fail} out=${resolve(args.out)}`);
  process.exit(fail === 0 ? 0 : 2);
}

main().catch((e) => {
  console.error(`ERROR: ${e?.message || e}`);
  process.exit(1);
});

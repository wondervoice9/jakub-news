#!/usr/bin/env node
// Bootstraps the Android Gradle project from an existing twa-manifest.json
// without triggering Bubblewrap's interactive CLI prompts.
//
// Uses @bubblewrap/core directly — the same library the bubblewrap CLI wraps.
// Prerequisites (must be on $PATH or available to Gradle during the subsequent
// `bubblewrap build` step):
//   • JDK 17
//   • Android SDK with platforms;android-33 and build-tools;33.0.2
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { TwaGenerator, TwaManifest, ConsoleLog } from "@bubblewrap/core";

const cwd = process.cwd();
const manifestPath = resolve(cwd, "twa-manifest.json");
const raw = readFileSync(manifestPath, "utf8");
const json = JSON.parse(raw);

const manifest = new TwaManifest(json);
const err = manifest.validate();
if (err) {
  console.error("twa-manifest.json is invalid:", err);
  process.exit(1);
}

await manifest.saveToFile(manifestPath);

const log = new ConsoleLog("generate-twa");
const generator = new TwaGenerator();
await generator.createTwaProject(cwd, manifest, log);

log.info("Android project generated in " + cwd);

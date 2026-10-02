/**
 * Export raw biometric captures from MongoDB into the ML service's
 * training folder:
 *
 *   ml-service/data/collected/static/<date>.jsonl
 *   ml-service/data/collected/dynamic/<date>.jsonl
 *
 * Only samples with a trustworthy identity label are exported:
 *   - every enrollment sample
 *   - login samples that were ACCEPTED (rejected ones may be impostors)
 *
 * Usage (from server/):  npm run export-samples
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import mongoose from 'mongoose';

import { connectDatabase } from '../src/config/database.js';
import BiometricSample from '../src/models/BiometricSample.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const outputRoot = path.resolve(here, '..', '..', 'ml-service', 'data', 'collected');

const sessionId = (date) => `S${date.toISOString().slice(0, 10).replaceAll('-', '')}`;

async function exportKind(kind, stamp) {
  const directory = path.join(outputRoot, kind);
  fs.mkdirSync(directory, { recursive: true });

  const file = path.join(directory, `${stamp}.jsonl`);
  const stream = fs.createWriteStream(file, { encoding: 'utf-8' });

  const cursor = BiometricSample.find({
    kind,
    $or: [{ purpose: 'enrollment' }, { purpose: 'login', accepted: true }],
  })
    .sort({ createdAt: 1 })
    .cursor();

  let count = 0;
  for await (const doc of cursor) {
    stream.write(
      `${JSON.stringify({
        user_id: doc.user.toString(),
        session_id: sessionId(doc.createdAt),
        sample_id: doc._id.toString(),
        purpose: doc.purpose,
        sample: doc.sample,
      })}\n`,
    );
    count += 1;
  }

  await new Promise((resolve) => stream.end(resolve));
  console.log(`[export] ${kind}: ${count} samples -> ${file}`);
}

async function main() {
  await connectDatabase();
  const stamp = new Date().toISOString().replaceAll(':', '-').slice(0, 19);

  await exportKind('static', stamp);
  await exportKind('dynamic', stamp);

  await mongoose.disconnect();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

/* =============================================================================
 * FILE SUMMARY
 * -----------------------------------------------------------------------------
 * exportBiometricSamples.js closes the data loop between the web app and the
 * ML pipelines.  It streams labelled raw captures (enrollment samples and
 * accepted login samples, keyed by pseudonymous user id and a per-day session
 * id) from MongoDB into JSON-lines files under ml-service/data/collected/,
 * where the training (--collected / --finetune-real) and evaluation
 * pipelines pick them up to retrain and recalibrate on real users.
 * ========================================================================== */

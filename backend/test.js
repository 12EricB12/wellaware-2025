#!/usr/bin/env node

"use strict";

const path = require("path");
const { createWorker } = require("tesseract.js");

const [, , imagePath] = process.argv;
const image = path.resolve(__dirname, imagePath || "serum.jpeg");

console.log(`Recognizing ${image}`);

(async () => {
  const worker = await createWorker("eng", 1, {
    logger: (m) => console.log(m),
  });
  const {
    data: { text },
  } = await worker.recognize(image);
  console.log(text);
  await worker.terminate();
})();

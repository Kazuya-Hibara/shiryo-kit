#!/usr/bin/env node
// shiryo-kit: HTML デッキを Chrome の印刷で PDF にする（@page の用紙サイズ・背景色を使う。読み原稿 aside.notes は印刷しない）。
// 使い方: node html_pdf.mjs deck.html out.pdf
import { writeFileSync } from "node:fs";
import { openPage } from "./lib_cdp.mjs";

const [, , file, out] = process.argv;
if (!file || !out) { console.error("usage: node html_pdf.mjs deck.html out.pdf"); process.exit(2); }
let page;
try { page = await openPage(file, { scale: 1 }); } catch (e) { console.error(String(e.message || e)); process.exit(3); }
try {
  const { data } = await page.send("Page.printToPDF", {
    printBackground: true, preferCSSPageSize: true, displayHeaderFooter: false,
    marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0,
  });
  writeFileSync(out, Buffer.from(data, "base64"));
} catch (e) { console.error(String(e.message || e)); await page.close(); process.exit(4); }
await page.close();
console.log(`pdf → ${out}`);
process.exit(0);

// Copyright (c) 2026 Carnot AI Inc. (MIT) — derived from carnot-tech/consulting-pptx-skill scripts/lib_cdp.mjs
// Modifications for shiryo-kit (MIT): Chrome discovery for macOS / Windows / Linux, configurable startup wait
// (SHIRYO_CHROME_WAIT_MS), DevToolsActivePort-based endpoint discovery, actionable error messages.
//
// Chrome headless を DevTools Protocol で直接操作する最小ヘルパー（追加依存なし・Node 22+ の標準 WebSocket と fetch を使う）。
// html_dump.mjs / html_pdf.mjs から使う。
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, existsSync, readFileSync } from "node:fs";
import { tmpdir, homedir, platform } from "node:os";
import { join, resolve, delimiter } from "node:path";
import { pathToFileURL } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const HELP_INSTALL =
  "Google Chrome（または Microsoft Edge / Chromium）を入れてください。" +
  " macOS: https://www.google.com/chrome/ から入れる / Windows: Edge は最初から入っています（Chrome でも可）" +
  " / Linux: google-chrome か chromium を入れる。" +
  " 入っているのに見つからない時は、環境変数 CHROME_PATH にブラウザ本体のパスを入れて再実行してください。";

function onPath(names) {
  const dirs = (process.env.PATH || "").split(delimiter).filter(Boolean);
  const exts = platform() === "win32" ? ["", ".exe"] : [""];
  for (const n of names) for (const d of dirs) for (const e of exts) {
    const p = join(d, n + e);
    if (existsSync(p)) return p;
  }
  return null;
}

export function findChrome() {
  const env = process.env.CHROME_PATH || process.env.SHIRYO_CHROME_PATH;
  if (env) {
    if (existsSync(env)) return env;
    throw new Error(`CHROME_PATH に指定されたブラウザが見つかりません: ${env}。${HELP_INSTALL}`);
  }
  const os = platform();
  let cands = [];
  if (os === "darwin") {
    const apps = [
      "Google Chrome.app/Contents/MacOS/Google Chrome",
      "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
      "Chromium.app/Contents/MacOS/Chromium",
      "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
      "Brave Browser.app/Contents/MacOS/Brave Browser",
      "Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    ];
    for (const root of ["/Applications", join(homedir(), "Applications")]) for (const a of apps) cands.push(join(root, a));
  } else if (os === "win32") {
    const roots = [process.env.PROGRAMFILES, process.env["PROGRAMFILES(X86)"], process.env.LOCALAPPDATA,
      "C:/Program Files", "C:/Program Files (x86)"].filter(Boolean);
    const rels = ["Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe",
      "Chromium/Application/chrome.exe", "BraveSoftware/Brave-Browser/Application/brave.exe"];
    for (const rel of rels) for (const r of roots) cands.push(join(r, rel));
  } else {
    cands = ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser",
      "/snap/bin/chromium", "/usr/bin/microsoft-edge", "/opt/google/chrome/chrome"];
  }
  const hit = cands.find((p) => existsSync(p)) ||
    onPath(["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge"]);
  if (!hit) throw new Error(`Chrome が見つかりません。${HELP_INSTALL}`);
  return hit;
}

function waitMs() {
  const v = parseInt(process.env.SHIRYO_CHROME_WAIT_MS || "", 10);
  return Number.isFinite(v) && v > 0 ? v : 45000; // 初回起動（コールドスタート）が 8 秒を超える機種がある
}

export async function openPage(file, { width = 1400, height = 900, scale = 1, media = "print", hideNotes = true, joinCjkBreaks = true } = {}) {
  const CHROME = findChrome();
  const userDataDir = mkdtempSync(join(tmpdir(), "shiryo-chr-"));
  const args = [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    "--disable-extensions", "--disable-background-networking", "--disable-component-update",
    "--remote-debugging-port=0", `--user-data-dir=${userDataDir}`, "about:blank",
  ];
  if (platform() === "linux" && process.getuid && process.getuid() === 0) args.unshift("--no-sandbox");
  const chrome = spawn(CHROME, args, { stdio: ["ignore", "ignore", "pipe"] });
  let stderr = "", exited = null;
  chrome.stderr.on("data", (d) => { stderr = (stderr + d.toString()).slice(-2000); });
  chrome.on("exit", (code, sig) => { exited = { code, sig }; });
  chrome.on("error", (e) => { exited = { code: -1, sig: String(e.message || e) }; });

  let ws;
  const close = async () => {
    try { ws?.close(); } catch {}
    try { chrome.kill(); } catch {}
    await delay(300);
    try { rmSync(userDataDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch {}
  };

  // ポートは Chrome に選ばせ（衝突しない）、user-data-dir に書かれる DevToolsActivePort から読む
  const limit = waitMs();
  const t0 = Date.now();
  let endpoint;
  while (!endpoint && Date.now() - t0 < limit && !exited) {
    await delay(150);
    let port = null;
    try {
      const lines = readFileSync(join(userDataDir, "DevToolsActivePort"), "utf8").split(/\r?\n/);
      port = parseInt(lines[0], 10);
    } catch {}
    if (!port) {
      const m = stderr.match(/DevTools listening on ws:\/\/[^:]+:(\d+)\//);
      if (m) port = parseInt(m[1], 10);
    }
    if (!port) continue;
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (r.ok) endpoint = (await r.json()).webSocketDebuggerUrl;
    } catch {}
  }
  if (!endpoint) {
    await close();
    const why = exited
      ? `ブラウザが起動直後に終了しました（code=${exited.code} ${exited.sig || ""}）。${stderr.trim().split("\n").slice(-3).join(" / ")}`
      : `ブラウザの起動を ${Math.round(limit / 1000)} 秒待ちましたが応答がありませんでした。`;
    throw new Error(
      `Chrome devtools endpoint not ready: ${why}\n` +
      `対処: (1) もう一度実行する（初回は起動が遅いことがあります） (2) 待ち時間を延ばす: SHIRYO_CHROME_WAIT_MS=120000 を付けて実行` +
      ` (3) 別のブラウザを使う: CHROME_PATH にパスを入れる。使ったブラウザ: ${CHROME}`);
  }

  ws = new WebSocket(endpoint);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0, sessionId;
  const inflight = new Map(), events = [];
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && inflight.has(msg.id)) {
      const { resolve, reject } = inflight.get(msg.id);
      inflight.delete(msg.id);
      msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result);
    } else if (msg.method) events.push(msg);
  };
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const _id = ++id;
    inflight.set(_id, { resolve, reject });
    ws.send(JSON.stringify({ id: _id, method, params, ...(sessionId ? { sessionId } : {}) }));
  });

  const { targetId } = await send("Target.createTarget", { url: "about:blank" });
  ({ sessionId } = await send("Target.attachToTarget", { targetId, flatten: true }));
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: scale, mobile: false });
  // 印刷レイアウトで扱う（画面用のビューポート追従スケーラーの影響を受けない）
  await send("Emulation.setEmulatedMedia", { media });
  await send("Page.navigate", { url: pathToFileURL(resolve(file)).href });
  for (let i = 0; i < 300 && !events.some((e) => e.method === "Page.loadEventFired"); i++) await delay(100);

  const evaluate = async (fnOrExpr, arg) => {
    const expression = typeof fnOrExpr === "function"
      ? `(${fnOrExpr.toString()})(${JSON.stringify(arg ?? null)})` : fnOrExpr;
    const { result, exceptionDetails } = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (exceptionDetails) throw new Error(JSON.stringify(exceptionDetails).slice(0, 500));
    return result.value;
  };
  if (hideNotes) {
    // 読み原稿（aside.notes）はスライドに描かない（作者が CSS で隠し忘れても出さない）
    await evaluate(() => {
      const st = document.createElement("style");
      st.id = "__shiryo_notes_hidden";
      st.textContent = "aside.notes{display:none!important}";
      document.head.appendChild(st);
      return true;
    });
  }
  if (joinCjkBreaks) {
    // ソースの改行（字下げ込み）が和文と和文の間にある時は詰める（Chrome は空白として描くが、pptx・PDF では詰めて揃える）。
    // 作者が打った空白（改行を含まない）・&nbsp;・全角空白には触れない。html_dump.mjs / deck_html.py と同じ規則
    await evaluate(() => {
      const CJK = /[\u3000-\u9fff\uff00-\uffef]/;
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
        acceptNode: (n) => (n.parentElement && /^(SCRIPT|STYLE|TEXTAREA|PRE)$/.test(n.parentElement.tagName) ? 2 : 1),
      });
      const nodes = [];
      while (w.nextNode()) nodes.push(w.currentNode);
      let prev = "";
      nodes.forEach((n, i) => {
        let t = n.nodeValue;
        const nextChar = () => (nodes.slice(i + 1).map((m) => m.nodeValue.replace(/^[ \t\n\r\f]+/, "")).find((v) => v.length) || "")[0] || "";
        if (/^[ \t\n\r\f]*\n[ \t\n\r\f]*$/.test(t)) {
          if (CJK.test(prev) && CJK.test(nextChar())) n.nodeValue = "";
          return;
        }
        t = t.replace(/([\u3000-\u9fff\uff00-\uffef])[ \t\r\f]*\n[ \t\n\r\f]*(?=[\u3000-\u9fff\uff00-\uffef])/g, "$1");
        const lead = t.match(/^[ \t\r\f]*\n[ \t\n\r\f]*/);
        if (lead && CJK.test(prev) && CJK.test(t.slice(lead[0].length, lead[0].length + 1))) t = t.slice(lead[0].length);
        const trail = t.match(/[ \t\r\f]*\n[ \t\n\r\f]*$/);
        if (trail && trail.index > 0 && CJK.test(t[trail.index - 1])) {
          if (CJK.test(nextChar())) t = t.slice(0, trail.index);
        }
        if (t !== n.nodeValue) n.nodeValue = t;
        const tt = t.replace(/[ \t\n\r\f]+$/, "");
        if (tt) prev = tt[tt.length - 1];
      });
      return true;
    });
  }
  try { await evaluate("document.fonts ? document.fonts.ready.then(() => true) : true"); } catch {}
  await delay(800); // 画像
  return { send, evaluate, close };
}

// shiryo-kit: 見つかったブラウザのパスを表示する（build.py / doctor の事前確認用）。見つからなければ対処を表示して exit 3。
import { findChrome } from "./lib_cdp.mjs";
try { console.log(findChrome()); } catch (e) { console.error(String(e.message || e)); process.exit(3); }

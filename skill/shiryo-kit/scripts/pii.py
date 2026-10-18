"""shiryo-kit: メモリー・メモの file に個人情報らしいものが残っていないか探す（取りこぼしを少なくする側に倒す）。

check.py pii が使う。見つけるもの:
  name      人名らしいもの（「田中様」「佐藤さん」「山田 太郎氏」、「氏名: 〜」「担当者: 〜」、よくある名字 + 名）
  phone     電話番号（03-1234-5678 / 090-1234-5678 / 0312345678 / +81-90-…）
  email     メールアドレス
  postal    郵便番号（〒123-4567 / 123-4567）
  address   住所らしいもの（都道府県 + 市区町村 + 番地）
  mynumber  12 桁の数（マイナンバーらしいもの。4-4-4 区切りも）
  health    健康・障害に関する語が人名の近く（同じ行か前後 1 行）にある
  org       会社・事業所の名前 + 様 / 御中（「サンプル製作所 様」。顧問先の正式名）
許可リスト（--allow FILE、または対象フォルダ直下の pii-allowlist.txt）: 1 行 1 語。本人・事務所の名前・連絡先など、
  残してよい語を書く。見つけた文字がその語を含む（または語に含まれる）時は報告しない。# で始まる行はコメント。
表示は一部を伏せる（例: 田中様 → 田*様）。ログ経由で個人情報を広げないため。
"""
import re
from pathlib import Path

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml", ".csv", ".tsv", ".html", ".htm", ".xml", ".ini", ".toml", ""}

COMMON_SURNAMES = (
    "佐藤 鈴木 高橋 田中 伊藤 渡辺 渡部 山本 中村 小林 加藤 吉田 山田 佐々木 山口 松本 井上 木村 斎藤 斉藤 清水 山崎 池田 橋本 阿部 "
    "石川 山下 中島 石井 小川 前田 岡田 長谷川 藤田 後藤 近藤 村上 遠藤 青木 坂本 福田 太田 西村 藤井 金子 岡本 藤原 中野 三浦 原田 "
    "中川 松田 竹内 小野 田村 中山 和田 石田 森田 上田 柴田 酒井 工藤 横山 宮崎 宮本 内田 高木 安藤 島田 谷口 大野 高田 丸山 今井 "
    "河野 藤本 村田 武田 上野 杉山 増田 小山 大塚 平野 菅原 久保 松井 千葉 岩崎 桜井 木下 野口 松尾 菊地 野村 新井 永井 中田 川口 "
    "北村 安田 五十嵐 川崎 西田 吉川 辻 関 秋山 本田 久保田 須藤 小島 飯田 吉村 小松 岩田 山内 宮田 早川 大西 服部"
).split()
HONORIFIC = r"(?:様|さま|さん|氏|殿|先生|くん|君|ちゃん)"
# 敬称が付いても人名ではない語（末尾一致で除く）
NOT_NAME_END = ("皆様", "皆さま", "皆さん", "お客様", "客様", "お客さま", "ご担当者様", "担当者様", "担当者さん", "担当様",
                "利用者様", "関係者様", "ご家族様", "家族様", "奥様", "奥さん", "旦那様", "旦那さん", "お子様", "お子さん",
                "神様", "王様", "殿様", "同様", "仕様", "模様", "多様", "異様", "一様", "有様", "文様", "紋様", "図様",
                "様様", "貴社様", "御社様", "各社様", "先方様", "顧問先様", "会員様", "受講者様", "参加者様", "社長様",
                "社長さん", "部長さん", "課長さん", "店長さん", "大家さん", "屋さん", "母さん", "父さん", "兄さん", "姉さん",
                "婆さん", "爺さん", "赤ちゃん", "先生方", "講師の先生", "医師の先生", "人事の先生", "社労士の先生",
                "税理士の先生", "弁護士の先生", "皆様方", "各位", "ご一同様", "一同様", "ご担当さん",
                "パートさん", "アルバイトさん", "バイトさん", "スタッフさん", "パートナーさん", "ドライバーさん", "ヘルパーさん",
                "メンバーさん", "ユーザーさん", "オーナーさん", "医者さん", "社員さん", "職員さん", "従業員さん", "事務員さん",
                "新人さん", "業者さん", "常連さん", "看護師さん", "保育士さん", "パートの方さん")
NOT_NAME_PREFIX_CHARS = set("のをにがはでとへもや、。・「」（）()　 ")
HEALTH = ("診断名", "病名", "傷病名", "障害等級", "障害者手帳", "手帳", "精神", "うつ病", "鬱病", "適応障害", "双極性",
          "統合失調症", "発達障害", "ADHD", "自閉", "がん", "癌", "腫瘍", "糖尿病", "心疾患", "脳梗塞", "ヘルニア",
          "休職", "通院", "服薬", "投薬", "療養", "入院", "手術", "妊娠", "不妊", "流産", "介護認定", "要介護", "要支援",
          "既往歴", "持病", "障害年金", "労災", "診断書", "HIV", "感染症", "メンタル不調", "メンタル")
PREF = r"(?:北海道|東京都|大阪府|京都府|[一-龥]{2,3}県)"

RX = {
    "email": re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"(?<![\d\-])(?:\+81[\-\s]?\d{1,4}[\-\s]?\d{1,4}[\-\s]?\d{3,4}|0\d{1,4}[\-\s(（]\d{1,4}[\-\s)）]\d{3,4}|0[5789]0\d{8}|0\d{9})(?![\d\-])"),
    "postal": re.compile(r"〒\s?\d{3}[\-−ー]?\d{4}|(?<![\d\-])\d{3}[\-−]\d{4}(?![\d\-])"),
    "address": re.compile(PREF + r"[一-龥ぁ-んァ-ヶ]{1,12}?(?:市|区|町|村|郡)[一-龥ぁ-んァ-ヶ0-9０-９\-−ー丁目番地号の]{1,30}?\d+(?:丁目|番地?|号|[\-−ー]\d+)"),
    "mynumber": re.compile(r"(?<![\d\-])(?:\d{4}[\s\-]\d{4}[\s\-]\d{4}|\d{12})(?![\d\-])"),
    "name_hon": re.compile(r"([一-龥々ァ-ヶー]{1,5}(?:[ 　][一-龥々ぁ-んァ-ヶー]{1,4})?|[A-ZＡ-Ｚ])" + HONORIFIC + r"(?![々式子相態])"),
    "name_label": re.compile(r"(?:氏名|名前|お名前|担当者名?|代表者名?|代表取締役|社長|ご本人|本人|従業員名|相談者|申請者|被保険者)\s*[:：]\s*([^\s,、。|｜]{2,12})"),
    # 名字 + 名。1 字の名字（辻・関）は空白で区切った時だけ（「関係」「辻褄」を拾わない）
    "name_common": re.compile(r"(?:(?:" + "|".join(sorted((x for x in COMMON_SURNAMES if len(x) > 1), key=len, reverse=True))
                              + r")[ 　]?|(?:" + "|".join(x for x in COMMON_SURNAMES if len(x) == 1) + r")[ 　])[一-龥々]{1,2}(?![一-龥々])"),
    # 会社・事業所の名前 + 様 / 御中（顧問先の正式名。保存してよいと本人が言った時は許可リストへ）
    "org": re.compile(r"[一-龥々ァ-ヶーA-Za-zＡ-Ｚａ-ｚ0-9・]{1,20}(?:株式会社|有限会社|合同会社|製作所|工業|商事|商店|工務店|医院|"
                      r"クリニック|事務所|商会|産業|建設|運輸|会社|法人)[ 　]?(?:様|さま|御中)"),
}


def load_allow(paths):
    words = []
    for p in paths:
        p = Path(p).expanduser()
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                words.append(line)
    return words


def mask(s):
    s = s.strip()
    if len(s) <= 2:
        return s[0] + "*"
    if "@" in s:
        user, _, dom = s.partition("@")
        return user[:1] + "***@" + dom
    if re.fullmatch(r"[\d\-\s+()（）〒−]+", s):
        digits = [i for i, c in enumerate(s) if c.isdigit()]
        keep = set(digits[:2] + digits[-2:])
        return "".join(c if (not c.isdigit() or i in keep) else "*" for i, c in enumerate(s))
    return s[0] + "*" * (len(s) - 2) + s[-1]


def _allowed(text, allow):
    t = text.strip()
    return any(w in t or t in w for w in allow if w)


def scan_text(text, allow=()):
    """[(行番号, 種類, 見つけた文字)]"""
    found = []
    lines = text.splitlines()
    name_lines = set()
    for i, line in enumerate(lines, 1):
        for kind in ("email", "phone", "postal", "address", "mynumber", "org"):
            for m in RX[kind].finditer(line):
                s = m.group(0)
                if kind == "mynumber" and RX["phone"].fullmatch(s):
                    continue
                if not _allowed(s, allow):
                    found.append((i, kind, s))
        for m in RX["name_hon"].finditer(line):
            s = m.group(0)
            if s.endswith(NOT_NAME_END) or any(s.endswith(w) for w in NOT_NAME_END):
                continue
            core = m.group(1)
            if len(core) == 1 and not re.fullmatch(r"[A-ZＡ-Ｚ一-龥]", core):
                continue
            if _allowed(core, allow) or _allowed(s, allow):
                continue
            found.append((i, "name", s))
            name_lines.add(i)
        for m in RX["name_label"].finditer(line):
            s = m.group(1)
            if _allowed(s, allow):
                continue
            found.append((i, "name", m.group(0)))
            name_lines.add(i)
        for m in RX["name_common"].finditer(line):
            s = m.group(0)
            if _allowed(s, allow) or any(s in f[2] or f[2] in s for f in found if f[0] == i and f[1] == "name"):
                continue
            found.append((i, "name", s))
            name_lines.add(i)
    for i, line in enumerate(lines, 1):
        if not ({i - 1, i, i + 1} & name_lines):
            continue
        for w in HEALTH:
            if w in line:
                found.append((i, "health", w))
                break
    return found


def iter_files(target):
    p = Path(target)
    if p.is_file():
        yield p
        return
    for f in sorted(p.rglob("*")):
        if f.is_file() and f.suffix.lower() in TEXT_SUFFIXES and not any(part.startswith(".") for part in f.relative_to(p).parts):
            if f.name == "pii-allowlist.txt":
                continue
            yield f


def scan_path(target, allow_files=()):
    p = Path(target)
    allow_paths = list(allow_files)
    base = p if p.is_dir() else p.parent
    if (base / "pii-allowlist.txt").exists():
        allow_paths.append(base / "pii-allowlist.txt")
    allow = load_allow(allow_paths)
    results = []
    for f in iter_files(p):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ln, kind, s in scan_text(text, allow):
            results.append((f, ln, kind, s))
    return results

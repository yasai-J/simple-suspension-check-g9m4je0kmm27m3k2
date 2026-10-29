"""
簡易懸濁法の可否リスト（Excel）から、アプリ用の data.js を作るスクリプト。

使い方:
    pip install openpyxl
    python tools/build_data.py 簡易懸濁法の可否リスト.xlsx

リストを更新したら、このスクリプトを実行して data.js を差し替え、
sw.js の CACHE_VERSION の数字を1つ上げてから GitHub に push してください。

Excel の列（1行目は見出し）:
  A 薬品名 / B 粉砕 / C 簡易懸濁 / D 最小通過サイズ /
  E 条件55℃お湯(5分) / F 条件55℃お湯(10分 または 散剤の分散性 良・悪) /
  G 破壊後→55℃お湯(5分) / H 破壊後→55℃お湯(10分) /
  I マクロゴール含有(●) / J 備考欄
"""
import json
import re
import sys
import unicodedata as u
from datetime import date

import openpyxl

K = {"○": "ok", "〇": "ok", "×": "ng", "水溶": "water", "△": "cond", "": "none"}
F = {"○": "ok", "〇": "ok", "×": "ng", "―": "od", "ー": "od", "-": "od",
     "脱カプ": "cap", "△": "cond", "": "none"}


def s(v):
    return "" if v is None else str(v).strip()


def nk(v):
    return " ".join(u.normalize("NFKC", v).split())


def extract_alt(name, note):
    """備考欄の「〇〇へ処方変更」「〇〇へ変更」「〇〇注あり」から代替薬を取り出す"""
    if name.startswith("ユニフィル"):
        return {"to": ["テオドールドライシロップ"], "when": "", "how": "同じ1日量を分2で服用"}
    if name.startswith("ケタス"):
        return {"to": [], "when": "経管投与のとき", "how": "処方変更が必要（薬剤部へ相談）"}
    hits = list(re.finditer(r"([^。、:→()\s]+?)へ(処方変更|変更)", note))
    if hits:
        to, when = [], ""
        for h in hits:
            for t in re.split("あるいは|または", h.group(1)):
                t = t.strip(" 、")
                if t.startswith("粉砕処方は"):
                    t = t[5:]
                    when = when or "粉砕の指示のとき"
                t = re.sub(r"^.*ので", "", t)
                if t and t not in to:
                    to.append(t)
        pre = note[:hits[0].start()]
        if not when:
            if "粉砕、簡易懸濁" in pre:
                when = "粉砕・簡易懸濁の指示のとき"
            elif "粉砕" in pre[-12:]:
                when = "粉砕の指示のとき"
            elif "経管" in pre or "経管投与" in note[hits[0].end():hits[0].end() + 8]:
                when = "経管投与のとき"
        if when == "経管投与のとき" and "粉砕指示も" in note:
            when = "経管投与・粉砕指示のとき"
        how = "問い合わせ・提案" if re.search("提案|問い合わせ", note) else ""
        return {"to": to, "when": when, "how": how}
    m = re.search(r"([^。、\s]+?(注シリンジ|注))あり", note)
    if m:
        return {"to": [m.group(1)], "when": "", "how": "注射剤あり"}
    return None


def main(path, out="data.js"):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        r = list(r) + [None] * 10
        name = s(r[0])
        if (not name or name.isdigit() or name.startswith("=")
                or name.startswith("×の数") or name.startswith("割合")):
            continue
        n = nk(name)
        e, f, g, h = (nk(s(x)) for x in r[4:8])
        cond, disp = [], ""
        if e:
            cond.append("55℃お湯 " + e)
        if f in ("良", "悪"):
            disp = f
        elif f:
            cond.append("55℃お湯 " + f)
        if g:
            cond.append("錠剤破壊後 55℃お湯 " + ("5分" if g == "○" else g))
        if h:
            cond.append("錠剤破壊後 55℃お湯 " + h)
        note = nk(s(r[9]))
        item = {
            "n": n,
            "f": F.get(s(r[1]), "none"),
            "k": K.get(s(r[2]), "none"),
            "t": nk(s(r[3])).replace("FR", "Fr").replace("fr", "Fr"),
            "c": cond,
            "d": disp,
            "m": 1 if s(r[8]) else 0,
            "b": note,
        }
        alt = extract_alt(n, note)
        if alt:
            item["alt"] = alt
        rows.append(item)

    js = ("// 自動生成ファイル：直接編集せず tools/build_data.py で作り直してください\n"
          f"// 生成日 {date.today().isoformat()} ／ {len(rows)}品目\n"
          "window.KENDAKU_DATA = "
          + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n")
    open(out, "w", encoding="utf-8").write(js)
    print(f"{out} を作成しました（{len(rows)}品目、代替薬あり {sum('alt' in x for x in rows)}品目）")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("使い方: python tools/build_data.py <Excelファイル>")
    main(sys.argv[1])

#!/usr/bin/env python3
"""合并第二轮（补充核查）静态标注页导出的个人答案文件，生成与自部署版 server.py 相同格式的 audit2_export.json。

用法：
  python3 merge_exports.py exports/*.json                  # 打印每人进度，写出 audit2_export.json
  python3 merge_exports.py exports/*.json -o out.json      # 指定输出文件

每个输入文件是标注者在页面上点「导出答案」得到的 audit2_<名字>.json。
同名标注者的多个文件会被合并（后读入的覆盖同条目旧值）。
"""
import argparse
import glob
import json
import sys
import time

N_W, N_T = 128, 90  # A 抽取核查（W）/ B 对比文本核查（T）


def load(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict) or not isinstance(d.get("answers"), dict):
        raise ValueError("缺少 answers 字段，不是有效的导出文件")
    name = d.get("annotator") or d.get("uid")
    if not name or not isinstance(name, str):
        raise ValueError("缺少 annotator 字段")
    # 只保留合法的条目 id（W001-W128 / T001-T090）和 dict 值
    answers = {k: v for k, v in d["answers"].items()
               if isinstance(k, str) and len(k) == 4 and k[0] in "WT"
               and k[1:].isdigit() and isinstance(v, dict)}
    return name, answers


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="标注者导出的 audit2_*.json（支持通配符）")
    ap.add_argument("-o", "--output", default="audit2_export.json", help="输出文件（默认 audit2_export.json）")
    a = ap.parse_args()

    merged = {}
    n_files = 0
    for pat in a.files:
        paths = sorted(glob.glob(pat)) or ([pat] if glob.os.path.exists(pat) else [])
        if not paths:
            print(f"警告：没有文件匹配 {pat}", file=sys.stderr)
        for p in paths:
            try:
                name, answers = load(p)
            except Exception as e:  # noqa: BLE001
                print(f"跳过 {p}：{e}", file=sys.stderr)
                continue
            if name in merged:
                print(f"警告：标注者「{name}」有多个文件，{p} 中同条目的答案会覆盖旧值", file=sys.stderr)
            merged.setdefault(name, {}).update(answers)
            n_files += 1

    if not merged:
        print("没有成功读入任何答案文件。", file=sys.stderr)
        sys.exit(1)

    out = {"version": 2, "exported": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "annotators": [{"annotator": k, "uid": k, "answers": v} for k, v in sorted(merged.items())]}
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"{'标注者':<20}{'A 抽取':>9}{'B 对比':>9}")
    print("-" * 38)
    for k, v in sorted(merged.items()):
        nW = sum(1 for key in v if key.startswith("W"))
        nT = sum(1 for key in v if key.startswith("T"))
        flag = "" if (nW >= N_W and nT >= N_T) else "  <- 未完成"
        print(f"{k:<20}{nW:>5}/{N_W}{nT:>5}/{N_T}{flag}")
    print(f"\n已合并 {n_files} 个文件、{len(merged)} 位标注者 -> {a.output}")


if __name__ == "__main__":
    main()

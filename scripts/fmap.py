#!/usr/bin/env python3
"""功能地图通用查询入口（可跨项目使用）。

数据文件解析顺序：
  1. --data 指定的路径
  2. --site 指定的站点（技能目录 sites/<域名>/feature-map.yaml）
  3. 环境变量 FEATURE_MAP_FILE
  4. 从当前工作目录向上逐级查找 feature-map.yaml

用法（建议在项目根目录执行）：
    python <skill目录>/scripts/fmap.py 价格
    python <skill目录>/scripts/fmap.py 商品 编辑
    python <skill目录>/scripts/fmap.py 商品 --all
    python <skill目录>/scripts/fmap.py --list
    python <skill目录>/scripts/fmap.py 价格 --data path/to/feature-map.yaml
    python <skill目录>/scripts/fmap.py 充值 --site hy.ithinkai.cn
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("缺少 PyYAML，请先执行：python -m pip install pyyaml")

DATA_NAME = "feature-map.yaml"
SITES_DIR = Path(__file__).resolve().parent.parent / "sites"
ENV_VAR = "FEATURE_MAP_FILE"
SEPARATORS = re.compile(r"[\s,，、/]+")
EXACT_BONUS = 50


def find_data_file(explicit=None, site=None):
    """按约定顺序定位数据文件，找不到返回 None。"""
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        return path
    if site:
        return SITES_DIR / site / DATA_NAME
    env_path = os.environ.get(ENV_VAR)
    if env_path:
        return Path(env_path).expanduser()
    current = Path.cwd().resolve()
    for directory in [current, *current.parents]:
        candidate = directory / DATA_NAME
        if candidate.is_file():
            return candidate
    return None


def load_features(data_file):
    """读取并做最小校验，数据有问题时给出可定位的报错。"""
    if not data_file.is_file():
        sys.exit(f"找不到数据文件：{data_file}")
    data = yaml.safe_load(data_file.read_text(encoding="utf-8")) or {}
    features = data.get("features") or []
    for i, item in enumerate(features, 1):
        missing = [k for k in ("name", "where", "how") if not item.get(k)]
        if missing:
            sys.exit(f"数据错误：第 {i} 条记录缺少字段 {', '.join(missing)}")
    return features


def norm(text):
    """归一化：去空白，并把连字符/间隔符去掉，便于「记一笔完成」命中「记一笔-完成」。"""
    cleaned = re.sub(r"[-–—‐_·•]", "", str(text).lower())
    return "".join(cleaned.split())


def normalize_site(site):
    """允许传域名、完整 URL 或带路径的地址，统一成 sites/<域名> 可用的形式。"""
    value = site.strip()
    value = re.sub(r"^https?://", "", value, flags=re.I)
    return value.split("/")[0].lower()


def score_token(feature, token):
    """单个关键词打分：名称/别名完全匹配 > 前缀 > 包含，最后兜底查路径。"""
    query = norm(token)
    best = 0
    for name in [feature["name"], *feature.get("aliases", [])]:
        candidate = norm(name)
        if candidate == query:
            best = max(best, 100)
        elif candidate.startswith(query) or query.startswith(candidate):
            best = max(best, 80)
        elif query in candidate:
            best = max(best, 60)
        elif candidate in query:
            best = max(best, 40)
    if best == 0 and query in norm(feature["where"] + feature["how"]):
        best = 20
    return best


def score(feature, query):
    """多关键词：每个词都必须命中，得分累加；整词完全命中额外加权。"""
    tokens = [t for t in SEPARATORS.split(query) if t]
    if not tokens:
        return 0
    total = 0
    for token in tokens:
        s = score_token(feature, token)
        if s == 0:
            return 0
        total += s + (EXACT_BONUS if s == 100 else 0)
    return total


def render(feature, with_name=False):
    lines = []
    if with_name:
        lines.append(f"【{feature['name']}】")
    lines.append(f"功能在哪里：{feature['where']}")
    lines.append(f"怎么打开：{feature['how']}")
    return "\n".join(lines)


def validate(features):
    """维护期校验：字段完整、名称/别名全图唯一、每个名称都能自查询命中自己。"""
    errors = []
    owners = {}
    for i, f in enumerate(features, 1):
        missing = [k for k in ("name", "where", "how") if not f.get(k)]
        if missing:
            errors.append(f"第 {i} 条缺少字段：{', '.join(missing)}")
        for label in [f.get("name"), *f.get("aliases", [])]:
            if label:
                owners.setdefault(label, []).append(f.get("name") or f"第{i}条")
    for label, names in owners.items():
        if len(names) > 1:
            errors.append(f"名称/别名重复：{label} -> {', '.join(names)}")
    for f in features:
        name = f.get("name")
        if not name:
            continue
        best = max(features, key=lambda x: score(x, name))
        if score(best, name) == 0 or best["name"] != name:
            errors.append(f"自查询未命中：{name} -> {best.get('name')}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="按功能名或关键词查询功能地图")
    parser.add_argument("query", nargs="*", help="功能名或关键词，多个词用空格分隔")
    parser.add_argument("--data", help="feature-map.yaml 路径，默认从当前目录向上查找")
    parser.add_argument("--site", help="技能内置站点地图，例如 hy.ithinkai.cn（也接受完整 URL）")
    parser.add_argument("--all", action="store_true", help="列出所有匹配项")
    parser.add_argument("--list", action="store_true", help="列出全部功能")
    parser.add_argument("--check", action="store_true", help="校验地图：必填字段、名称/别名唯一、名称可自查询命中")
    args = parser.parse_args()

    data_file = find_data_file(args.data, normalize_site(args.site) if args.site else None)
    if data_file is None:
        print(f"未找到 {DATA_NAME}。", file=sys.stderr)
        print("请在项目根目录创建该文件，或用 --data 指定路径。", file=sys.stderr)
        print("可从 skill 的 examples/ 目录复制一份作为起点。", file=sys.stderr)
        sys.exit(2)

    features = load_features(data_file)

    if not features:
        print(f"功能地图为空：{data_file}", file=sys.stderr)
        print("请先添加功能条目，格式见 skill 的 README.md。", file=sys.stderr)
        sys.exit(2)

    if args.check:
        errors = validate(features)
        if errors:
            print(f"地图校验未通过：{data_file}")
            for e in errors:
                print(" -", e)
            sys.exit(1)
        print(f"地图校验通过：{data_file}（{len(features)} 条）")
        return

    if args.list:
        if not features:
            print("功能地图为空。")
            return
        width = max(len(f["name"]) for f in features)
        for f in features:
            print(f"{f['name'].ljust(width)}  {f['where']}")
        return

    query = " ".join(args.query).strip()
    if not query:
        parser.error("请提供功能名或关键词，例如：python fmap.py 价格")

    scored = [(score(f, query), f) for f in features]
    matched = [(s, f) for s, f in scored if s > 0]
    matched.sort(key=lambda pair: pair[0], reverse=True)

    if not matched:
        print(f"未找到匹配的功能：{query}", file=sys.stderr)
        print("可用 --list 查看全部功能。", file=sys.stderr)
        sys.exit(1)

    if args.all:
        for s, f in matched:
            print(render(f, with_name=True))
            print()
        return

    top = matched[0][0]
    best = [f for s, f in matched if s == top]
    for i, f in enumerate(best):
        if i:
            print()
        print(render(f, with_name=len(best) > 1))


if __name__ == "__main__":
    main()

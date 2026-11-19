---
name: feature-map
description: 跨项目查询「某个功能在界面的哪里、怎么点开」。用户问某功能在哪个菜单/页面、如何进入、操作步骤时使用。数据来自当前项目根目录的 feature-map.yaml，也可查询技能内置的站点地图（sites/<域名>/feature-map.yaml），脚本不绑定任何具体项目。
---

# 功能地图

回答「功能在哪里」和「怎么打开」这类界面导航问题。**只依据当前项目的 `feature-map.yaml` 回答，不要凭空猜测。**

本技能也是 `app-flowtest` 的上游：做功能测试时先读取并校验这里的地图（`fmap.py --list` / `--check`），再按地图条目在真机或浏览器逐项执行，最后每个被测对象单独出报告。

## 数据位置约定

脚本按以下顺序找数据文件，**不依赖技能自身的安装路径**：

1. 命令行 `--data <路径>`
2. 命令行 `--site <域名>`（读取技能目录 `sites/<域名>/feature-map.yaml`）
3. 环境变量 `FEATURE_MAP_FILE`
4. 从当前工作目录向上逐级查找 `feature-map.yaml`

因此每个项目各自维护一份地图：把 `feature-map.yaml` 放在项目根目录即可。

网站类产品没有代码仓库时，地图放在技能目录 `sites/<域名>/feature-map.yaml`，查询时用 `--site <域名>`（当前内置：`hy.ithinkai.cn` 75 条、`canvas.vbing.site` 73 条）。用户问的是某个已内置网站的功能、而当前项目没有地图时，直接用 `--site` 回答；`--site` 也接受完整 URL。

## 查询方式

在**目标项目根目录**执行（`<skill目录>` 指本 `SKILL.md` 所在目录）：

```powershell
python <skill目录>\scripts\fmap.py 设为壁纸
```

输出固定两行，直接转述给用户：

```
功能在哪里：壁纸详情 > 设为壁纸
怎么打开：打开壁纸详情 > 点「设为壁纸」> 选桌面/锁屏/桌面与锁屏同时设置
```

## 其他用法

| 场景 | 命令 |
| --- | --- |
| 用多个关键词缩小范围 | `python <skill目录>\scripts\fmap.py 我的 收藏` |
| 查看所有可能匹配项 | `python <skill目录>\scripts\fmap.py 会员 --all` |
| 浏览器全部已录入功能 | `python <skill目录>\scripts\fmap.py --list` |
| 校验地图（重复名/别名、缺字段、自查询） | `python <skill目录>\scripts\fmap.py --check` |
| 指定其他地图文件 | `python <skill目录>\scripts\fmap.py 价格 --data docs/feature-map.yaml` |
| 查询内置站点地图 | `python <skill目录>\scripts\fmap.py 充值 --site hy.ithinkai.cn` |

## 行为约定

- 命中：输出「功能在哪里」「怎么打开」两行；同一功能有多个并列最佳匹配时，每条带功能名分隔。
- 未命中：标准错误输出「未找到匹配的功能：X」，退出码 1。
- 找不到数据文件：提示创建 `feature-map.yaml` 或使用 `--data`，退出码 2。
- 新增/修改条目后立即生效，无需重启。

## 项目尚未接入时

如果脚本提示「未找到 feature-map.yaml」：

1. 如实告诉用户该项目还没有功能地图，不要编造位置。
2. 询问是否需要创建；确认后从技能目录 `examples/` 复制一份，或按 README 的格式在项目根目录新建 `feature-map.yaml`。
3. 新项目没有现成条目时，建议先录入 3-5 个最常用功能再查询。

数据格式、增改方法与示例见技能目录下的 `README.md` 与 `examples/`。

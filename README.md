# guoguo — 小学数学练习题生成器

自动生成小学一年级数学练习题。**一次运行 → 一个 PDF → 一页**，按 `TASKS` 列表顺序把所有题型拼到同一张纸上。

## 题型一览

| 命令名 | 题型 | 题目示例 | 默认布局 |
|--------|------|----------|----------|
| `chain-add` | 连加填空 | `2 + 3 + 4 = ▢` | 4 列 |
| `chain-sub` | 连减填空 | `10 - 5 - 4 = ▢` | 4 列 |
| `chain-mix` | 连加连减混合 | `2 + 5 - 4 = ▢`、`7 - 2 + 2 = ▢` | 4 列 |
| `blank-fill` | 括号填空 | `( ) + 3 = 7`、`9 - ( ) = 3` | 5 列 |
| `fill-op` | 填符号 | `5 ◯ 2 = 7`、`8 ◯ 7 = 1`（填 + 或 −） | 5 列 |
| `compare` | 比大小 | `3 + 3 ◯ 3 + 2`、`10 - 7 ◯ 1 + 2` | 4 列 |
| `adjacent` | 相邻数 | `（ ）4（ ）`、`1（ ）3` | 4 列 |

所有题目：
- 最终结果和中间结果都在 `[0, max_num]` 范围内
- 相邻单元格（上下、左右）不会出现同一道题
- 每次运行随机出题

## 环境

- Python 3.9+
- Windows（PDF 依赖 Microsoft Word COM）
- 依赖：`python-docx`、`pywin32`

```bash
pip install python-docx pywin32
```

## 使用方法

打开 `main.py`，编辑 `TASKS` 列表，然后运行：

```bash
python main.py
```

### TASKS 格式

每一行一个任务，格式 `('题型', 题数, max_num)`：

```python
TASKS = [
    ('chain-add',    20,   10),   # 20 道连加，10 以内
    ('chain-sub',    20,   10),   # 20 道连减
    ('chain-mix',    20,   10),   # 20 道连加连减混合
    ('blank-fill',   15,   10),   # 15 道括号填空
    # ('adjacent',   8,    12),   # 不要的用 # 注释掉
]
```

- **题数**：想出多少道。会按题型的 `IDEAL_COLS` 自动算行数
- **max_num**：数字范围上限，如 10 表示所有数字和结果在 `[0, 10]`

### 一页上限

不按固定行数硬算。每块先按题数算出想占的行数，再按**页面可用高度**分配：
页头、分节标题、块间空行、各题型行高（1.5cm；相邻数 1.6cm）都算进去。
总高超出时，从相对最满的一块逐行削减，每块至少保留 1 行。

生成前还会让 Word 实测一次页数，仍然超页就继续收紧，所以无论怎么改
`TASKS`，产出都严格是**一页**。被削掉的题数会打印出来：

```
  三、连加连减混合 16 题（4 行 × 4 列）
```

想让某块题多一些，就少放几个题型，或者把别块的题数调小。

### 输出

PDF 文件生成在当前目录，文件名按内容自动生成，形如：

```
综合练习_连加+连减+连加连减混合+括号填空_共67题.pdf
```

## 项目结构

```
guoguo/
├── main.py                     # 入口：改 TASKS，运行即可
├── README.md
└── src/guoguo/
    ├── __init__.py
    ├── core.py                 # 文档设置、去重填充、PDF 转换、行数分配
    ├── generators.py           # 各题型枚举算法（xxx_items）
    ├── renderers.py            # Word 单元格渲染（add_xxx_question）
    ├── adjacent.py             # 相邻数
    ├── blank_fill.py           # 括号填空
    ├── chain_add.py            # 连加
    ├── chain_sub.py            # 连减
    ├── chain_mix.py            # 连加连减混合
    ├── compare.py              # 比大小（两个算式比大小）
    └── fill_op.py              # 填符号（a ◯ b = c，填 + / −）
```

每个 sheet 模块都提供统一接口：

```python
module.add_section(doc, count, max_num)
```

`main.py` 遍历 `TASKS` 调用它们，拼到同一个 Document 再转 PDF。

## 自定义

### 添加新题型

1. 在 `generators.py` 增加 `xxx_items(max_num)`，返回 `[(key, data), ...]`
   - `key` 用于相邻去重（把交换律等价的归一化）
2. 在 `renderers.py` 增加 `add_xxx_question(para, ...)`，把一道题写入段落
3. 新建 `src/guoguo/xxx.py`，参考 `chain_add.py`：
   - 定义 `IDEAL_COLS` 和 `ROW_HEIGHT_CM`
   - 实现 `_add_table(doc, rows, cols, max_num)` 和 `add_section(doc, count, max_num, title=None)`
4. 在 `main.py` 的 `SHEETS` 字典注册

### 调整单页密度

- 加题 → 调大 `MAX_ROWS_PER_PAGE`
- 行高（`ROW_HEIGHT_CM`，所有题型默认 1.5cm）调小 → 一页能放更多
- 页边距在 `core.setup_document()` 里改

## 设计要点

- **相邻去重**：`core.fill_cells(rows, cols, items_for)` 实现，利用 `key` 判断左邻/上邻是否重复，重复就从后面交换一个来
- **自动布局**：`core.allocate_rows()` 按页面可用高度和各题型行高分配行数，生成后用 Word 实测页数，超页则继续收紧直到恰好一页
- **PDF 生成**：先用 python-docx 写 .docx，再通过 Word COM 转 PDF（Windows-only）

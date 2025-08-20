# DocDeck - PDF Header & Footer Tool

## 项目概述

DocDeck是一个专业的PDF页眉页脚处理工具，支持批量处理、中文字体、结构化输出等高级功能。项目采用模块化架构，使用PySide6构建现代化GUI界面。

## 当前状态 (2025-08-20)

### ✅ 已完成功能（近期要点）

#### 核心功能
- PDF批量处理：拖拽导入、递归目录扫描
- 页眉页脚添加：自定义文本、字体、位置、大小
- 页眉页脚检测与删除：智能检测算法，安全删除不破坏页面内容
- 文件解锁：加密/受限PDF解锁后保存
- A4规范化：自动将非标准尺寸PDF转换为A4
- 中文字体支持：系统字体检测、Type0字体嵌入（带ToUnicode，跨平台一致）
- 结构化输出：采用 /Artifact BDC/EMC + /Subtype /Header|/Footer 写入；附带 DocDeck 元数据（DDTemplate/DateFmt/Align/Unit/Version/Type），确保编辑互通

#### 预览与读取
- 所见即所得预览：PyMuPDF底图 + ReportLab文本层透明叠加（混合渲染），与最终输出一致
- 读取现有页眉/页脚：优先解析Artifact；缺失时可扩展为启发式候选；回填UI后可直接编辑
- 实时预览联动：修改文本/位置/字体后立即更新

#### UI与交互
- 模块化组件：设置面板、文件表、输出面板、工具栏、预览管理器
- 现代化UI设计：统一的样式系统、美观的控件设计、响应式布局
- 右键菜单：编辑页眉/页脚…、删除原页眉/页脚、删除文件
- 导入标注：检测前几页存在结构化页眉/页脚的文件，给予标记
- 状态显示：进度条与进度文本位于文件列表上方

#### 技术架构
- 控制器模式：ProcessingController处理业务逻辑
- 事件处理：EventHandlers管理交互
- 日志系统：错误追踪、用户操作、性能日志
- 配置管理：用户设置持久化

### 🔧 最近修复的重要问题

#### 页眉页脚检测算法优化 (2025-08-19 至 2025-08-20)
- **问题诊断**：深入分析了PDF处理后变成空白页的根本原因
- **算法设计**：设计了Artifact检测和启发式检测的优化方案
- **算法实施**：优化了Artifact检测和启发式检测算法
- **安全机制**：实现了备份、验证、回滚机制，确保删除过程安全
- **检测精度**：提高了页眉页脚检测的准确性和可靠性

#### UI布局优化 (2025-08-20)
- **布局重构**：重新设计了设置面板的布局结构
- **控件美化**：统一了所有控件的样式和交互效果
- **用户体验**：优化了控件间距、添加了悬停效果和焦点状态
- **功能整合**：移除了冗余控件，保持了功能的完整性

### ⚠️ 已知问题（动态更新）
- 预览细节一致性：极端旋转/非A4页面的偏移在少数样本下仍需验证
- Artifact 删除粒度：当前按片段粗删，后续仅删除带 DDVersion 的对象或按Header/Footer细化
- 图标列：当前以名称标记★，后续改为专用列

## 后续工作方向

### 🎯 短期目标 (1-2周)
- 独立"编辑页眉/页脚"对话框：展示解析到的Artifact/启发式候选、模板字符串、对齐、日期格式、位置；所见即所得预览；确定后写回
- 列表专用图标列：锁图标、结构化标记图标，不污染文件名
- 删除逻辑细化：仅删除DocDeck写入（含DDVersion）的Artifact；或提供"仅Header/仅Footer"选项
- 启发式读取：补齐无Artifact时的候选，并识别日期/页码模板
 - 检测集中：所有页眉/页脚检测与PDF信息读取统一由 `pdf_analyzer.PdfAnalyzer` 提供；`pdf_utils` 仅保留字体注册等非检测功能（兼容层保留一周期后移除检测实现）

### 🚀 中期目标 (1-2月)
- 架构优化：进一步瘦身ui_main，抽取编辑对话框模块与数据绑定
- 模板管理：页眉/页脚模板的保存/导入/导出
- 性能优化：大文件内存与缓存策略（预览基页缓存、文本层不缓存）

## 架构与规划（合并自执行计划/进度/设计文档）

- UI 模块化（保留）：`main_window.py`（≤300行，框架/菜单/信号）+ `ui/components/*` + `ui/dialogs/*`
- 预览职责：全部在 `ui/components/preview_manager.py` 内（PyMuPDF底图 + ReportLab文本层），主窗仅委托调用
- 业务职责分离：
  - 检测/分析：`pdf_analyzer.PdfAnalyzer`（页数、大小、metadata、字体、Artifact检测、启发式检测、报告）
  - 修改写入：`pdf_handler`（写入/删除/解锁/合并/A4规范化；删除优先精确移除Artifact，回退遮盖）
- 右键菜单：编辑页眉页脚、删除原页眉页脚、解锁、删除文件
- 设置面板：三列比例 1:2:2；结构化模式与中文字体同行排布
- 自动内存优化：≥300MB 自动启用，无需按钮

### 文档合并说明（本次清理）
已将以下文档的有效内容并入本 README 与 `TODO.md`，原文件已删除：
`UI_REFACTOR_EXEC_PLAN.md`、`UI_MAIN_REFACTOR_PLAN.md`、`REFACTORING_STRATEGY_REVISED.md`、`REFACTORING_PROGRESS.md`、`REFACTORING_COMPLETION_SUMMARY.md`、`REFACTOR_SUMMARY.md`、`DESIGN_PREVIEW_TYPE0.md`、`RECENT_FIXES_SUMMARY.md`、`HEADER_FOOTER_FIX_README.md`、`ISSUES.md`、`CHANGELOG.md`。

## 技术架构

```
DocDeck/
├── ui_main.py              # 主窗口与UI协调
├── controller.py           # 业务逻辑控制器
├── pdf_handler.py          # PDF处理核心（结构化写入、A4规范化等）
├── pdf_analyzer.py         # PDF分析（页数/大小/元数据/字体/Artifact+启发式检测/报告）
├── font_manager.py         # 字体管理（中文回退、检测）
├── type0_font_provider.py  # Type0字体载体注入（含ToUnicode）
├── geometry_context.py     # 几何坐标与A4规范化
├── ui/                     # UI组件、事件、i18n
│   ├── components/         # 模块化UI组件
│   ├── handlers/           # 事件处理器
│   └── i18n/              # 国际化支持
└── utils/                  # UI与排序工具
```

## 开发环境

- Python 3.9+
- PySide6、PyMuPDF (fitz)、pikepdf、ReportLab

### 安装与运行
```bash
pip install -r requirements.txt
python main.py
```

---

最后更新：2025-08-20 / 版本：2.2.0

# DocDeck 2.0.2

一个功能强大的PDF处理工具，支持批量添加页眉页脚、A4规范化、结构化输出和智能合并。

## ✨ 主要功能

### 🔧 核心功能
- **批量PDF处理**：支持单个文件、文件夹或递归目录扫描
- **智能页眉页脚**：可自定义字体、大小、位置和内容
- **A4规范化**：自动将各种尺寸的PDF调整为标准A4格式
- **结构化输出**：生成符合PDF规范的页眉页脚，可在Acrobat中正确识别
- **中文支持**：完整的Unicode和CID字体支持
- **实时预览**：渲染真实PDF页面，检测文本重叠

### 🎯 高级特性
- **多模式处理**：支持覆盖模式和结构化模式
- **字体管理**：自动检测系统字体，支持自定义字体
- **位置预设**：一键设置右上角/右下角标准位置
- **现有内容读取**：可读取已存在的结构化页眉页脚
- **PDF合并**：支持处理后的文件合并，可添加页码
- **命令行接口**：完整的CLI支持，适合自动化处理

### 🖥️ 跨平台支持
- **macOS**：原生应用包 (.app) 和磁盘镜像 (.dmg)
- **Windows**：可执行文件和压缩包
- **Linux**：可执行文件和压缩包

## 🚀 快速开始

### 图形界面版本

1. **下载安装**
   - 从 [Releases](https://github.com/yourusername/DocDeck/releases) 页面下载对应平台的安装包
   - 解压或安装到本地目录

2. **启动应用**
   ```bash
   # macOS
   open DocDeck.app
   
   # Windows/Linux
   ./DocDeck
   ```

3. **基本使用**
   - 点击"选择文件"或"选择文件夹"导入PDF
   - 设置页眉页脚内容和样式
   - 选择输出目录
   - 点击"开始处理"

### 命令行版本

```bash
# 基本批处理
python main.py --source "folder1" "file1.pdf" --output "output_dir"

# 启用结构化模式
python main.py --source "input_folder" --output "output_dir" --structured

# 启用A4规范化
python main.py --source "input_folder" --output "output_dir" --normalize-a4

# 自定义页眉位置和字体
python main.py --source "input_folder" --output "output_dir" \
  --header-text "公司名称" \
  --header-font "SimHei" \
  --header-size 16 \
  --header-x 100 \
  --header-y 800

# 合并输出文件并添加页码
python main.py --source "input_folder" --output "output_dir" \
  --merge \
  --add-page-numbers
```

## 📖 详细使用说明

### 页眉页脚设置

#### 文本内容
- **固定文本**：直接输入要显示的文本
- **自动编号**：使用 `{page}` 和 `{total}` 占位符
- **自定义格式**：支持前缀、后缀、起始编号、步长等

#### 位置控制
- **坐标系统**：使用点(pt)为单位，原点在页面左下角
- **预设位置**：
  - 右上角：距右边0.3cm，距上边0.8cm
  - 右下角：距右边0.3cm，距下边0.8cm
- **手动调整**：可精确设置X、Y坐标

#### 字体设置
- **字体名称**：支持系统已安装的字体
- **字体大小**：推荐使用14pt，适合打印
- **中文支持**：自动检测中文字体，支持固定字体模式

### 处理模式

#### 覆盖模式 (默认)
- 使用ReportLab在PDF上叠加文本
- 兼容性好，适合简单应用
- 不支持文本选择和搜索

#### 结构化模式
- 生成符合PDF规范的页眉页脚
- 可在Acrobat中正确识别和编辑
- 支持文本选择和搜索
- 自动处理字体嵌入和编码映射

### A4规范化

- **自动检测**：识别页面方向和尺寸
- **智能缩放**：保持内容比例，居中显示
- **旋转处理**：自动处理90°、180°、270°旋转
- **临时文件管理**：处理完成后自动清理

## 🛠️ 安装和构建

### 从源码构建

```bash
# 克隆仓库
git clone https://github.com/yourusername/DocDeck.git
cd DocDeck

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 构建可执行文件

```bash
# 安装PyInstaller
pip install pyinstaller

# 构建
pyinstaller --noconfirm --clean --windowed --name "DocDeck" main.py

# 构建macOS DMG (需要create-dmg或hdiutil)
bash build-mac.sh
```

## 📋 系统要求

- **Python**: 3.8+
- **操作系统**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **内存**: 建议4GB+
- **存储**: 至少500MB可用空间

### 依赖库
- **PySide6**: Qt6 GUI框架
- **PyPDF2**: PDF读写
- **PyMuPDF (fitz)**: PDF渲染和预览
- **pikepdf**: 高级PDF操作
- **ReportLab**: PDF生成和字体处理

## 🔧 配置选项

### 默认设置
```python
DEFAULT_FONT_NAME = "Helvetica"
DEFAULT_FONT_SIZE = 14
DEFAULT_HEADER_X = 21      # 0.3cm from left
DEFAULT_HEADER_Y = 28      # 0.8cm from top
DEFAULT_FOOTER_X = 21      # 0.3cm from left  
DEFAULT_FOOTER_Y = 28      # 0.8cm from bottom
```

### 配置文件
应用会自动创建配置文件保存用户设置，包括：
- 字体选择
- 位置偏好
- 输出目录
- 处理模式

## 🚨 故障排除

### 常见问题

**Q: 处理中文PDF时出现乱码**
A: 确保启用了"结构化模式"，或选择支持中文的字体

**Q: 预览不显示或显示错误**
A: 检查PDF文件是否损坏，或尝试重新导入文件

**Q: 构建失败**
A: 确保所有依赖已正确安装，检查Python版本兼容性

**Q: 内存不足错误**
A: 分批处理大文件，或增加系统虚拟内存

### 日志文件
应用会在 `logs/` 目录下生成详细的日志文件，包含：
- 处理过程信息
- 错误详情
- 性能统计

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发环境设置
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

### 代码规范
- 使用Python类型注解
- 遵循PEP 8代码风格
- 添加适当的注释和文档字符串
- 确保所有测试通过

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [PySide6](https://doc.qt.io/qtforpython/) - Qt6 Python绑定
- [PyPDF2](https://pypdf2.readthedocs.io/) - PDF处理库
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF渲染库
- [pikepdf](https://pikepdf.readthedocs.io/) - 现代PDF库
- [ReportLab](https://www.reportlab.com/) - PDF生成库

## 📞 支持

- **GitHub Issues**: [报告Bug](https://github.com/yourusername/DocDeck/issues)
- **讨论区**: [GitHub Discussions](https://github.com/yourusername/DocDeck/discussions)
- **文档**: [Wiki](https://github.com/yourusername/DocDeck/wiki)

---

**DocDeck 2.0.2** - 让PDF处理变得简单高效 🚀

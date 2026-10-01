# knowledge/raw —— 只读原始数据

本目录存放用户提供的知识库压缩包及其解压内容（`_知识库.zip`、`09p-滴天髓补注_*.zip`）。

- **只读语义**：规范化过程只读此目录，产出写入 `knowledge/normalized/`；禁止反向修改。
- **不入库**：原始内容含现代整理/今译（孙正治注译、赵嘉宁今译等），版权状态不适合再分发，
  故本目录被 .gitignore 排除；`MANIFEST.sha256` 记录 zip 校验和用于复现。
- **复现**：将两个 zip 放入本目录并 `unzip` 即可重建（校验和见 MANIFEST.sha256）。
- 内含 `_文本提取/` 全文 OCR（带 `===== PDF第N页 =====` 页码标记），页码约定见
  `docs/knowledge/02-KNOWLEDGE-AUDIT.md`。

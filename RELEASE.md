# Release Guide

このドキュメントは RX Scanner の新しいバージョンをリリースする手順を説明します。

## リリースプロセス概要

```
1. 開発完了・テスト
   ↓
2. バージョンタグ作成
   ↓
3. タグをpush
   ↓
4. CI/CDが自動実行
   ↓
5. GitHubリリース自動作成
```

## セマンティックバージョニング

バージョン番号は `vMAJOR.MINOR.PATCH` 形式を使用：

- **MAJOR**: 破壊的変更（v1.0.0 → v2.0.0）
- **MINOR**: 新機能追加（v1.0.0 → v1.1.0）
- **PATCH**: バグ修正（v1.0.0 → v1.0.1）

### 例

```
v0.1.0  初回リリース
v0.2.0  Excel出力機能追加
v0.2.1  OCRバグ修正
v1.0.0  正式版リリース
```

## リリース手順

### 1. 開発完了・品質確認

```bash
# すべてのテストが通ることを確認
poetry run pytest

# 型チェック
poetry run mypy rx_scanner/

# Lint
poetry run ruff check .

# ローカルでビルド確認
poetry run python -m build
```

### 2. バージョン番号の更新

以下のファイルでバージョン番号を更新：

**pyproject.toml**
```toml
[project]
version = "0.2.0"  # 新しいバージョン
```

**rx_scanner/main.py** (必要に応じて)
```python
__version__ = "0.2.0"
```

### 3. 変更をコミット

```bash
git add pyproject.toml rx_scanner/main.py
git commit -m "chore: bump version to 0.2.0"
git push origin main
```

### 4. CIの確認

**重要：タグをpushする前に、mainブランチでCIが通っていることを確認**

```bash
# GitHub ActionsでCIステータスを確認
# https://github.com/yukinagao719/rx-scanner/actions

# または、最新のmainでCIを実行
git checkout main
git pull origin main
git push origin main
```

### 5. タグ作成・プッシュ

```bash
# タグを作成（メッセージ付き推奨）
git tag -a v0.2.0 -m "Release version 0.2.0

- Add Excel export functionality
- Improve OCR accuracy
- Fix database search bug
"

# タグをプッシュ
git push origin v0.2.0
```

### 6. リリースビルドの監視

GitHub Actions タブで進行状況を確認：

1. **Build Executables** (約5-10分)
   - Windows build
   - macOS build

2. **Create Release** (約1分)
   - GitHubリリースページ作成
   - 実行ファイル添付

### 7. リリース確認

[GitHub Releases](https://github.com/yukinagao719/rx-scanner/releases) で確認：

- ✅ リリースノートが自動生成されている
- ✅ 2つの実行ファイルが添付されている
  - `rx-scanner-windows-x86_64.exe`
  - `rx-scanner-macos-x86_64`
- ✅ Source code (zip/tar.gz) が添付されている

### 8. リリースノート編集（オプション）

自動生成されたリリースノートを必要に応じて編集：

```markdown
## 🚀 RX Scanner v0.2.0

### ✨ New Features
- Excel形式でのエクスポート機能追加
- 薬剤検索の高速化

### 🐛 Bug Fixes
- OCR処理時のクラッシュを修正
- データベース検索のタイムアウト問題を解決

### 📝 Documentation
- ユーザーガイドを更新
```

## トラブルシューティング

### CI/CDが失敗した場合

```bash
# エラー内容を確認
# GitHub Actions タブ → 失敗したジョブ → ログ確認

# 問題を修正
git add .
git commit -m "fix: resolve CI issue"

# タグを削除・再作成
git tag -d v0.2.0
git push origin :refs/tags/v0.2.0

# 修正後、再度タグ作成
git tag -a v0.2.0 -m "Release version 0.2.0"
git push origin v0.2.0
```

### タグを間違えた場合

```bash
# ローカルのタグを削除
git tag -d v0.2.0

# リモートのタグを削除
git push origin :refs/tags/v0.2.0

# 正しいタグを作成し直す
git tag -a v0.2.0 -m "正しいメッセージ"
git push origin v0.2.0
```

### リリースを削除したい場合

1. GitHub Releases ページでリリースを削除
2. タグも削除する場合：
```bash
git push origin :refs/tags/v0.2.0
```

## ベストプラクティス

### ✅ 推奨

- 必ずテストをすべて通してからリリース
- セマンティックバージョニングに従う
- タグメッセージに変更内容を記載
- リリース前に main ブランチを最新に保つ

### ❌ 避けるべき

- テストが失敗している状態でリリース
- タグメッセージなしのリリース（`git tag v0.2.0`）
- バージョン番号の飛ばし（v0.1.0 → v0.3.0）

## リリース例

### 初回リリース（v0.1.0）

```bash
# バージョン更新
# pyproject.toml: version = "0.1.0"

git add pyproject.toml
git commit -m "chore: bump version to 0.1.0"
git push origin main

git tag -a v0.1.0 -m "Initial release

- Prescription OCR functionality
- Medicine database search
- CSV export
"
git push origin v0.1.0
```

### 機能追加リリース（v0.2.0）

```bash
# pyproject.toml: version = "0.2.0"

git add pyproject.toml
git commit -m "chore: bump version to 0.2.0"
git push origin main

git tag -a v0.2.0 -m "Feature release

- Add Excel export functionality
- Improve search performance
"
git push origin v0.2.0
```

### バグ修正リリース（v0.2.1）

```bash
# pyproject.toml: version = "0.2.1"

git add pyproject.toml
git commit -m "chore: bump version to 0.2.1"
git push origin main

git tag -a v0.2.1 -m "Bugfix release

- Fix OCR crash on large images
- Fix database connection timeout
"
git push origin v0.2.1
```

## 参考リンク

- [Semantic Versioning](https://semver.org/)
- [GitHub Releases Documentation](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)

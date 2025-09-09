# 🚀 多機能AIワークスペース - セットアップガイド

このアーカイブには**v1.0.0 Modular Handler Architecture**の完全版が含まれています。

## 📋 必要な環境

- **Python**: 3.8以上
- **OS**: Windows, macOS, Linux対応  
- **OpenAI API**: 有効なAPIキーが必要

## ⚡ クイックスタート

### 1. プロジェクト展開
```bash
# zipファイルを展開
unzip chainlit_workspace_v1.0.0.zip
cd chainlit_workspace_v1.0.0
```

### 2. 仮想環境設定
```bash
# 仮想環境作成
python -m venv .venv

# 仮想環境有効化
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. 依存関係インストール
```bash
pip install -r requirements.txt
```

### 4. 環境変数設定
```bash
# .envファイルを作成（.env.exampleを参考）
cp .env.example .env

# .envファイルを編集してAPIキーを設定
# OPENAI_API_KEY=your_api_key_here
```

### 5. アプリケーション起動
```bash
chainlit run app.py --host 0.0.0.0 --port 8000
```

### 6. ブラウザでアクセス
```
http://localhost:8000
```

## 🎯 主要機能

### コマンド一覧
- `/help` - ヘルプ表示
- `/persona` - ペルソナ管理
- `/vs` - ベクトルストア管理  
- `/stats` - 統計情報表示
- `/test` - システムテスト実行

### ファイルアップロード
- チャット画面でファイルをドラッグ&ドロップ
- 自動的にベクトルストアに追加
- チャット削除時に自動削除

### ペルソナ切り替え
- 設定パネルからペルソナを選択
- カスタムペルソナの作成・編集可能

## 🔧 トラブルシューティング

### よくある問題

**Q: 起動時にエラーが発生する**
```bash
# 依存関係を再インストール
pip install --upgrade -r requirements.txt
```

**Q: APIエラーが発生する**
- `.env`ファイルのAPIキーを確認
- OpenAI API使用量制限を確認

**Q: ファイルアップロードが動作しない** 
- `uploads/`ディレクトリの書き込み権限を確認
- ファイルサイズ制限（通常32MB）を確認

**Q: データベースエラーが発生する**
- `.chainlit/chainlit.db`を削除（初回起動時に自動作成）
- ディスク容量を確認

## 📚 ドキュメント

- **IMPLEMENTATION_SUMMARY_v1.0.md** - 詳細な実装報告書
- **README.md** - プロジェクト概要
- **docs/MODULAR_ARCHITECTURE_GUIDE.md** - アーキテクチャガイド
- **CLAUDE.md** - 開発制約・ルール

## 🚀 次期バージョン

**v2.0.0 Electron統合**の準備が完了しています。
ElectronとPython統合_詳細実装ガイド.mdを参照してください。

---

## 📞 サポート

このプロジェクトはModular Handler Architectureに基づいて構築されています。
問題が発生した場合は、実装報告書を参照してください。

**動作確認済み環境:**
- Python 3.8+ 
- Chainlit 2.6.8+
- OpenAI API v1.99.6+

---

*Happy Coding! 🎉*
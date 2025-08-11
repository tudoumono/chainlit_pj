# Chainlit公式機能への移行ガイド

## 🚀 Phase 5 公式機能版

手動のセッション管理から、Chainlitの組み込み機能に移行しました。

## 主な変更点

### ✅ 追加された機能

1. **Chainlit公式の履歴管理**
   - 自動的なセッション保存
   - UIからの履歴アクセス（左上のボタン）
   - 認証による保護

2. **認証システム**
   - ユーザー名/パスワードによるログイン
   - セッションの保護

3. **簡略化されたコード**
   - 手動のデータベース管理が不要
   - よりシンプルで保守しやすい

### ❌ 削除された機能

1. **手動のセッション管理**
   - `session_handler` モジュール
   - カスタムデータベース操作
   - `/sidebar`, `/search`, `/recent`, `/resume`, `/tag`, `/export` コマンド

2. **複雑なセッション操作**
   - セッションの検索
   - タグ機能
   - エクスポート機能

これらの機能は、Chainlitの公式UIで代替されます。

## 📝 使い方

### 1. アプリケーションの起動

```bash
cd F:\10_code\AI_Workspace_App_Chainlit
chainlit run app.py
```

### 2. ログイン

ブラウザでアプリケーションを開くと、ログイン画面が表示されます。

- **ユーザー名**: `admin`
- **パスワード**: `admin123` （.envファイルで変更可能）

### 3. 履歴の使用

- **新しい会話**: 通常通りメッセージを送信
- **履歴を見る**: 左上の履歴ボタンをクリック
- **過去の会話を再開**: 履歴リストから選択してクリック

### 4. 利用可能なコマンド

| コマンド | 説明 |
|---------|------|
| `/help` | ヘルプを表示 |
| `/model [モデル名]` | 使用するモデルを変更 |
| `/system [プロンプト]` | システムプロンプトを設定 |
| `/stats` | 統計情報を表示 |
| `/clear` | 新しい会話を開始 |
| `/setkey [APIキー]` | OpenAI APIキーを設定 |
| `/test` | API接続をテスト |
| `/status` | 現在の設定を表示 |

## 🔧 設定のカスタマイズ

### パスワードの変更

`.env` ファイルを編集：

```env
CHAINLIT_AUTH_SECRET="your-new-password-here"
```

### 認証を無効にする

認証が不要な場合は、`.chainlit/config.toml` から以下の行を削除またはコメントアウト：

```toml
# user_environment = "CHAINLIT_AUTH_SECRET,OPENAI_API_KEY"
```

`.env` から以下の行を削除：

```env
# CHAINLIT_AUTH_TYPE="credentials"
# CHAINLIT_AUTH_SECRET="admin123"
```

## 📊 データの移行

既存の `chat_history.db` のデータは、Chainlitの新しい形式には自動で移行されません。
必要な場合は、重要な会話を手動でコピー＆ペーストしてください。

新しいデータは `.chainlit/data/` ディレクトリに保存されます。

## ⚠️ 注意事項

1. **データのバックアップ**
   - 移行前に `chat_history.db` をバックアップしてください
   - 新しいシステムは異なる形式でデータを保存します

2. **機能の違い**
   - タグやエクスポート機能は現在利用できません
   - これらは将来のバージョンで再実装される可能性があります

3. **パフォーマンス**
   - 公式機能を使用することで、より安定した動作が期待できます
   - メモリ使用量が削減されます

## 🔄 ロールバック方法

以前のバージョンに戻したい場合：

1. Gitを使用している場合：
   ```bash
   git checkout HEAD~1 app.py
   ```

2. バックアップから復元：
   - 以前のapp.pyをバックアップから復元
   - `.chainlit/config.toml` の変更を元に戻す
   - `.env` の認証設定を削除

## 💡 トラブルシューティング

### ログインできない場合

1. `.env` ファイルを確認
2. パスワードが正しく設定されているか確認
3. ブラウザのキャッシュをクリア

### 履歴が表示されない場合

1. `.chainlit/config.toml` で `data_persistence = true` を確認
2. `.chainlit/data/` ディレクトリの権限を確認
3. ブラウザをリロード

### エラーが発生する場合

1. 依存関係を再インストール：
   ```bash
   pip install -r requirements.in
   ```

2. Chainlitを最新版に更新：
   ```bash
   pip install --upgrade chainlit
   ```

## 📚 参考リンク

- [Chainlit Data Persistence](https://docs.chainlit.io/data-persistence/history)
- [Chainlit Authentication](https://docs.chainlit.io/authentication/overview)
- [Chainlit Lifecycle Hooks](https://docs.chainlit.io/api-reference/lifecycle-hooks/on-chat-resume)

## 🎯 今後の展望

公式機能をベースに、以下の機能を追加予定：

1. カスタム認証プロバイダー
2. より高度な統計情報
3. エクスポート機能の再実装（公式APIを使用）
4. マルチユーザー対応

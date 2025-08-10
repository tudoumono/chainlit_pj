# Phase 2 動作確認チェックリスト

## Phase 2の概要
**設定管理機能**の実装：APIキーの永続保存、接続テスト、モデル選択など

## 新しく追加されたファイル
- `utils/config.py` - 設定管理モジュール
- `utils/__init__.py` - パッケージ初期化
- `app.py` - Phase 2版に更新

## 起動前の確認

### 1. 環境チェック
```bash
uv run python check_env.py
```
すべてグリーンになることを確認

### 2. アプリケーション起動
```bash
uv run chainlit run app.py
```

## 機能テスト

### 1. 初期画面の確認
- [ ] ウェルカムメッセージが表示される
- [ ] Version: 0.2.0 (Phase 2) が表示される
- [ ] APIキーの状態が表示される（未設定/設定済み）
- [ ] クイックアクションボタンが表示される

### 2. APIキー設定テスト
- [ ] チャットに `/setkey sk-xxxxxxx` を入力
- [ ] "APIキーを設定しました" メッセージが表示される
- [ ] 自動的に接続テストが実行される
- [ ] .envファイルにAPIキーが保存される

### 3. 接続テスト
- [ ] `/test` コマンドまたは「接続テスト」ボタンをクリック
- [ ] "接続テスト中..." メッセージが表示される
- [ ] 成功/失敗の結果が表示される
- [ ] 成功時：利用可能なモデル一覧が表示される

### 4. 設定状態の確認
- [ ] `/status` コマンドまたは「設定状態」ボタンをクリック
- [ ] 現在の設定が一覧表示される
- [ ] APIキーがマスク表示される（sk-****...xxxx）

### 5. モデル一覧の取得
- [ ] `/models` コマンドを入力
- [ ] 利用可能なGPTモデルの一覧が表示される

### 6. モデル変更
- [ ] `/setmodel gpt-4o` コマンドを入力
- [ ] モデルが変更される
- [ ] `/status` で変更が反映されていることを確認

### 7. 設定の永続性確認
- [ ] アプリを再起動（Ctrl+C → 再度起動）
- [ ] 設定したAPIキーとモデルが保持されている
- [ ] `/status` で設定が残っていることを確認

## コマンド一覧

| コマンド | 説明 | 例 |
|---------|------|-----|
| `/setkey` | APIキーを設定 | `/setkey sk-xxxxxxxxxx` |
| `/setmodel` | デフォルトモデルを設定 | `/setmodel gpt-4o-mini` |
| `/setproxy` | プロキシを設定 | `/setproxy http://proxy:8080` |
| `/test` | 接続テスト | `/test` |
| `/status` | 設定状態表示 | `/status` |
| `/models` | モデル一覧表示 | `/models` |

## トラブルシューティング

### ModuleNotFoundError: No module named 'utils'
```bash
# app.pyがあるディレクトリから実行
cd F:\10_code\AI_Workspace_App_Chainlit
uv run chainlit run app.py
```

### 接続テストが失敗する
1. APIキーが正しいか確認
2. インターネット接続を確認
3. プロキシが必要な環境か確認
4. OpenAI APIの状態を確認: https://status.openai.com/

### .envファイルが更新されない
```bash
# .envファイルの権限を確認
ls -la .env  # Unix/Linux
dir .env     # Windows

# 手動で編集
notepad .env  # Windows
nano .env     # Unix/Linux
```

## Phase 2 完了基準

以下がすべて確認できたら完了：
- ✅ APIキーの設定と保存ができる
- ✅ 接続テストが成功する
- ✅ モデル一覧が取得できる
- ✅ 設定が.envファイルに永続保存される
- ✅ アプリ再起動後も設定が保持される
- ✅ すべてのコマンドが正常に動作する

## 次のステップ

Phase 3（データベース基盤構築）に進む：
- `utils/session_handler.py` - SQLite3データベース管理
- セッション情報の保存
- メッセージ履歴の記録
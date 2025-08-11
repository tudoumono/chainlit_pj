# 🎯 履歴機能を今すぐ使う方法

## 最速で起動（Windows）

```cmd
start_inmemory.bat
```

## 最速で起動（Mac/Linux/Windows）

```bash
python check_and_start.py
```

## 動作確認

1. **ログイン**
   - ユーザー名: `admin`
   - パスワード: `admin123`

2. **履歴ボタンの確認**
   - ログイン後、**左上に履歴ボタンが表示されます**

3. **テスト**
   - メッセージを送信
   - 履歴ボタンをクリック
   - 過去の会話が表示される

## 重要な注意

### 現在の実装について

- ✅ **履歴UIは表示されます**
- ✅ **セッション中は履歴が保持されます**
- ⚠️ **アプリ再起動で履歴は消失します**（インメモリのため）

### なぜインメモリ版を使うのか？

ChainlitのSQLAlchemyDataLayerはSQLiteとの互換性が低く、「no such table」エラーが発生します。
インメモリ版なら確実に動作します。

## 永続的な履歴が必要な場合

PostgreSQLを使用してください：

1. PostgreSQLをインストール
2. データベースを作成
3. `.env`に接続文字列を追加：
   ```env
   POSTGRES_CONNECTION_STRING=postgresql+asyncpg://user:password@localhost/dbname
   ```

## トラブルシューティング

### 履歴ボタンが表示されない

1. **ブラウザのキャッシュをクリア**
   - Ctrl+F5
   - またはシークレットモードで開く

2. **起動時のログを確認**
   ```
   ✅ シンプルなインメモリデータレイヤーを使用
   ```
   が表示されているか確認

3. **別のブラウザで試す**

## ファイル一覧

- `app.py` - メインアプリケーション（インメモリ優先）
- `simple_data_layer.py` - インメモリデータレイヤー
- `auth.py` - 認証設定
- `start_inmemory.bat` - Windows用起動スクリプト
- `check_and_start.py` - 環境チェック付き起動スクリプト

## まとめ

**今すぐ履歴機能を使いたい場合は、インメモリ版で十分です。**

永続化が必要になったら、PostgreSQLをセットアップしてください。

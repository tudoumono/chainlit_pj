# バグ修正ガイド

## 修正内容

### 1. 設定が即座に反映されない問題 ✅ 修正済み

**問題**: `/setmodel`で設定変更後、`/status`で反映されない
**原因**: セッション内の設定が更新されていなかった
**解決策**: 
- `config_manager.get_all_settings()`を再実行してセッションを更新
- 環境変数を即座に更新

### 2. クォーテーション問題 ✅ 修正済み

**問題**: .envファイルに`DEFAULT_MODEL='gpt-4o'`のように保存される
**原因**: python-dotenvのデフォルト動作
**解決策**: 
- `set_key`で`quote_mode='never'`を使用
- 古いバージョンの場合はfallback処理

## 修正後の動作確認

```bash
# アプリ起動
uv run chainlit run app.py

# ブラウザでテスト
1. /setmodel gpt-4o
2. /status  # 即座に反映されるはず
3. .envファイルを確認 # クォーテーションなしで保存されるはず
```

## python-dotenvのアップグレード（必要な場合）

```bash
# 最新版にアップグレード
uv pip install --upgrade python-dotenv

# バージョン確認
uv pip show python-dotenv
```

## .envファイルの手動修正（必要な場合）

既にクォーテーション付きで保存されている場合：
```
# 修正前
DEFAULT_MODEL='gpt-4o'

# 修正後（手動で編集）
DEFAULT_MODEL=gpt-4o
```

## テスト手順

1. **設定変更の即座反映テスト**
   ```
   /setmodel gpt-4o
   /status
   # → DEFAULT_MODELがgpt-4oになっているか確認
   ```

2. **アプリ再起動不要テスト**
   ```
   /setmodel gpt-4o-mini
   /status
   # → 即座に変更が反映されるか確認
   ```

3. **.envファイル確認**
   ```
   # .envファイルを開いて確認
   DEFAULT_MODEL=gpt-4o-mini  # クォーテーションなし
   ```
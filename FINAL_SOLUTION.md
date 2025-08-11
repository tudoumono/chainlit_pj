# 履歴機能を有効にする最終解決策

## エラーの解決

`chainlit-sqlalchemy`パッケージはまだPyPIに公開されていません。代わりに、Chainlit本体に組み込まれているSQLAlchemyDataLayerを使用します。

## 必要な依存関係をインストール

```bash
# 必要なパッケージをインストール
pip install aiosqlite asyncpg sqlalchemy
```

## アプリケーションを起動

```bash
chainlit run app.py
```

## 3つの動作モード

アプリケーションは以下の優先順位でデータレイヤーを選択します：

### 1. SQLAlchemyDataLayer（組み込み）
- Chainlit本体に含まれるSQLAlchemyDataLayerを使用
- SQLiteまたはPostgreSQLに対応
- **注意**: SQLiteサポートは不完全な可能性があります

### 2. SimpleDataLayer（インメモリ）
- `simple_data_layer.py`を使用
- アプリケーション再起動で履歴が消失
- テスト用に最適

### 3. データレイヤーなし
- 履歴機能が無効
- 基本的なチャット機能のみ

## PostgreSQLを使用する場合（推奨）

より安定した履歴機能が必要な場合は、PostgreSQLを使用してください：

1. PostgreSQLをインストール・起動
2. データベースを作成
3. app.pyを編集して接続文字列を変更：

```python
cl_data._data_layer = SQLAlchemyDataLayer(
    conninfo="postgresql+asyncpg://user:password@localhost/dbname"
)
```

## 動作確認

1. **起動時のログを確認**
   ```
   ✅ SQLAlchemyデータレイヤー（SQLite）を使用
   ```
   または
   ```
   ✅ シンプルなインメモリデータレイヤーを使用
   ```

2. **ログイン**
   - ユーザー名: `admin`
   - パスワード: `admin123`

3. **`/debug`コマンドで状態確認**
   - データレイヤーの状態
   - 認証の状態
   - Chainlit設定

4. **履歴ボタンの確認**
   - 左上に履歴ボタンが表示される
   - クリックすると過去の会話が表示される

## トラブルシューティング

### 履歴が表示されない場合

1. **必要なパッケージを確認**
   ```bash
   pip list | grep -E "aiosqlite|asyncpg|sqlalchemy"
   ```

2. **認証を一時的に無効化**
   `.env`から以下をコメントアウト：
   ```env
   # CHAINLIT_AUTH_TYPE="credentials"
   # CHAINLIT_AUTH_SECRET="admin123"
   ```

3. **インメモリ版を強制的に使用**
   app.pyの先頭を編集：
   ```python
   import simple_data_layer
   ```

4. **ブラウザの問題を解決**
   - Ctrl+F5でハードリロード
   - シークレットモードで開く
   - 別のブラウザで試す

## 最小限の動作確認

履歴UIが表示されるだけで良い場合（永続化不要）：

1. 認証を無効化（上記参照）
2. `simple_data_layer.py`を使用
3. アプリケーションを起動

これで履歴ボタンが表示され、セッション中は履歴が保持されます（再起動で消失）。

## 完全な履歴機能を実現するには

1. PostgreSQLをセットアップ
2. 接続文字列を設定
3. 認証を有効化
4. アプリケーションを起動

これで永続的な履歴管理が可能になります。

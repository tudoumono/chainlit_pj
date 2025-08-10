# 🚀 uvを使った正しいセットアップ方法

## エラーの原因
`uv sync`は**パッケージのビルド**を試みますが、Chainlitアプリケーションは**単なるスクリプト**なのでビルドは不要です。

## ✅ 正しい手順（これだけでOK）

```bash
# 1. 依存関係を直接インストール
uv pip install -r requirements.in

# 2. 環境チェック
uv run python check_env.py

# 3. アプリ起動
uv run chainlit run app.py
```

## 📦 requirements.inの内容

必要最小限の依存関係：
- chainlit (Webフレームワーク)
- openai (AI API)
- python-dotenv (環境変数)
- aiosqlite (データベース)
- その他のサポートライブラリ

## 🔧 もしエラーが続く場合

### オプション1: 個別インストール
```bash
uv pip install chainlit
uv pip install openai
uv pip install python-dotenv
# ... 他のパッケージも同様
```

### オプション2: クリーンインストール
```bash
# 仮想環境を削除して作り直す
rm -rf .venv  # PowerShellなら: Remove-Item .venv -Recurse -Force
uv venv
uv pip install -r requirements.in
```

## 📝 pyproject.tomlについて

現在の`pyproject.toml`は**参考情報**として残してありますが、実際には使用しません。
将来的にパッケージ化が必要になった場合に使用します。

## ✨ これで完了！

上記の手順で問題なくChainlitアプリケーションが動作します。
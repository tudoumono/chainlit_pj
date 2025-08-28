# Chainlit UI機能チェック - MCP連携

## 概要

このディレクトリには、Chainlit UIの機能をMCP（Model Context Protocol）を活用して自動チェックするツールが含まれています。

## ファイル構成

```
test_scripts/
├── ui_checker.py           # Seleniumベースの自動UIテスト
├── mcp_ui_analyzer.py     # MCP連携の分析ツール
├── run_ui_analysis.sh     # 全体の実行スクリプト
└── README.md              # このファイル
```

## 使用方法

### 1. クイックスタート

```bash
# Chainlitアプリを起動（別ターミナル）
cd /root/mywork/chainlit_pj
chainlit run app.py --host 0.0.0.0 --port 8000

# UI分析実行
./test_scripts/run_ui_analysis.sh
```

### 2. 手動ステップ実行

#### Step 1: 分析環境セットアップ
```bash
python test_scripts/mcp_ui_analyzer.py
```

#### Step 2: スクリーンショット撮影
```bash  
python test_scripts/ui_checker.py
```

#### Step 3: Claude Codeでの分析
撮影されたスクリーンショットをClaude Codeに送信して分析：

```
このスクリーンショットを分析してください: /root/mywork/chainlit_pj/screenshots/chainlit_ui_20250828_120000_initial.png

以下の観点で確認してください：
- 基本UI要素の表示状態
- 設定パネルの機能
- チャット機能の動作
- 改善提案
```

#### Step 4: MCPエージェントでの記録
```python
from test_scripts.mcp_ui_analyzer import MCPUIAnalyzer

analyzer = MCPUIAnalyzer()
analyzer.record_analysis_result(
    screenshot_path="/path/to/screenshot.png",
    analysis_result="Claude分析結果",
    test_scenario="基本チャット機能テスト"
)
```

## テストシナリオ

### 基本機能テスト
1. **初期画面表示** - UI要素の読み込み確認
2. **チャット機能** - メッセージ送信・応答確認  
3. **設定UI** - 設定パネルの表示・操作確認
4. **会話継続** - previous_response_id機能確認
5. **Tools機能** - Web検索・ファイル検索確認

### 高度なテスト  
1. **エラーハンドリング** - 異常系の動作確認
2. **パフォーマンス** - 応答速度測定
3. **レスポンシブ** - 画面サイズ対応確認

## チェックリスト

生成されるファイル `ui_analysis/ui_checklist.json` で進捗管理：

```json
{
  "基本UI要素": {
    "ヘッダー表示": "✅完了",
    "チャット入力欄": "⚠️問題あり",
    "設定パネル": "未確認"
  }
}
```

## 出力ファイル

### スクリーンショット
- `screenshots/` - 撮影された画面キャプチャ
- 自動的にタイムスタンプ付きで保存

### 分析結果
- `ui_analysis/test_report.json` - テスト実行結果
- `ui_analysis/analysis_record_*.json` - Claude分析結果記録
- `ui_analysis/ui_checklist.json` - 機能チェックリスト

## トラブルシューティング

### よくある問題

**Q: "Chainlitアプリが起動していません"**
```bash
# 解決方法
cd /root/mywork/chainlit_pj
chainlit run app.py --host 0.0.0.0 --port 8000
```

**Q: "依存関係が不足しています"**  
```bash
# 解決方法
pip install selenium requests
```

**Q: "Chrome WebDriverが見つかりません"**
```bash
# 解決方法
apt-get update && apt-get install -y chromium-browser
```

**Q: スクリーンショットが空白**
```bash
# 仮想ディスプレイで実行
xvfb-run -a python test_scripts/ui_checker.py
```

## MCP連携の利点

1. **自動記録**: 分析結果がCipherエージェントに自動保存
2. **履歴検索**: 過去の分析結果を素早く検索
3. **継続改善**: 分析傾向からUI改善点を特定
4. **知識蓄積**: チーム全体でUI品質知識を共有

## カスタマイズ

### 新しいテストシナリオ追加
`mcp_ui_analyzer.py`の`create_test_scenarios()`を編集

### チェック項目追加
`ui_checklist.json`に新しい項目を追加

### スクリーンショット設定変更
`ui_checker.py`のWebDriverオプションを調整

## サポート

問題が発生した場合は、以下をClaude Codeに報告：
- エラーメッセージ
- 実行環境（OS, Python バージョン等）
- 撮影されたスクリーンショット
- ログファイル（該当する場合）
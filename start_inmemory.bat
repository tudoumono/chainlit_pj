@echo off
echo =========================================
echo AI Workspace - 履歴機能付き起動
echo =========================================
echo.

REM 既存のデータベースをバックアップ（存在する場合）
if exist ".chainlit\chainlit.db" (
    echo 既存のデータベースをバックアップ...
    copy ".chainlit\chainlit.db" ".chainlit\chainlit.db.bak" >nul 2>&1
)

echo 起動中...
echo.
echo ログイン情報:
echo   ユーザー名: admin
echo   パスワード: admin123
echo.
echo 📝 履歴機能について:
echo   - 左上に履歴ボタンが表示されます
echo   - セッション中は履歴が保持されます
echo   - アプリ再起動で履歴は消失します（インメモリ版）
echo.
echo =========================================
echo.

chainlit run app.py
pause

async def show_knowledge_base():
    """ナレッジベースの状態を表示"""
    vector_stores = cl.user_session.get("vector_stores", {})
    uploaded_files = cl.user_session.get("uploaded_files", [])
    
    message = "# 📚 ナレッジベース\n\n"
    
    # ベクトルストア情報
    message += "## ベクトルストア\n"
    if vector_stores:
        for store_type, store_id in vector_stores.items():
            if store_id:  # IDが存在する場合のみ表示
                message += f"- **{store_type}**: `{store_id[:8] if len(store_id) > 8 else store_id}...`\n"
    else:
        message += "*ベクトルストアが作成されていません*\n"
    
    message += "\n## アップロードされたファイル\n"
    if uploaded_files:
        # デバッグ情報を詳細に出力
        app_logger.debug(f"uploaded_files データ構造: {uploaded_files}")
        print(f"[DEBUG] uploaded_files数: {len(uploaded_files)}")
        
        for i, file_info in enumerate(uploaded_files):
            try:
                # デバッグ: file_infoの型とキーを確認
                if isinstance(file_info, dict):
                    app_logger.debug(f"file_info[{i}] keys: {list(file_info.keys())}")
                    print(f"[DEBUG] file_info[{i}] keys: {list(file_info.keys())}")
                    
                    # キーの存在を確認してデフォルト値を使用
                    # 複数の可能なキー名を試す
                    filename = (file_info.get('filename') or 
                               file_info.get('name') or 
                               file_info.get('file_name') or 
                               file_info.get('fileName') or 
                               'Unknown')
                    
                    file_id = (file_info.get('file_id') or 
                              file_info.get('id') or 
                              file_info.get('fileId') or 
                              'unknown')
                    
                    # IDの長さを確認してから切り詰める
                    file_id_display = file_id[:8] if len(file_id) > 8 else file_id
                    message += f"- 📄 {filename} (ID: `{file_id_display}...`)\n"
                    
                elif isinstance(file_info, str):
                    # file_infoが文字列の場合（ファイルIDのみの場合）
                    app_logger.debug(f"file_info[{i}] is string: {file_info}")
                    message += f"- 📄 ファイル (ID: `{file_info[:8] if len(file_info) > 8 else file_info}...`)\n"
                else:
                    app_logger.warning(f"file_info[{i}] は予期しない型: {type(file_info)}")
                    print(f"[WARNING] file_info[{i}] は予期しない型: {type(file_info)}")
                    
            except Exception as e:
                app_logger.error(f"file_info[{i}]の処理でエラー: {e}")
                print(f"[ERROR] file_info[{i}]の処理でエラー: {e}")
                message += f"- 📄 エラー: ファイル情報の取得に失敗\n"
    else:
        message += "*ファイルがアップロードされていません*\n"
    
    message += "\n## 使い方\n"
    message += "1. ファイルをドラッグ&ドロップまたはクリップボードアイコンからアップロード\n"
    message += "2. ファイルは自動的に処理され、ナレッジベースに追加されます\n"
    message += "3. AIはアップロードされたファイルの内容を参照して回答します\n\n"
    
    message += "💡 **サポートされるファイル形式**: PDF, TXT, DOCX, CSV, JSON, MD等\n"
    message += "💡 **コマンド**: `/kb clear` でナレッジベースをクリア\n"
    
    await cl.Message(content=message, author="System").send()

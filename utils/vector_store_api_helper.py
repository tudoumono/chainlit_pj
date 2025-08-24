"""
ベクトルストアAPIヘルパー
OpenAI SDKの異なるバージョンに対応
"""

from typing import Optional, Any


def get_vector_store_api(client: Any) -> Optional[Any]:
    """
    利用可能なベクトルストアAPIを取得
    
    Args:
        client: OpenAIクライアント（同期または非同期）
    
    Returns:
        ベクトルストアAPI、または None
    """
    # パターン1: 直接vector_stores (Responses API)
    if hasattr(client, 'vector_stores'):
        print("✅ vector_stores APIを使用（Responses API）")
        return client.vector_stores
    
    # パターン2: beta.vector_stores (Beta API)
    if hasattr(client, 'beta') and hasattr(client.beta, 'vector_stores'):
        print("✅ beta.vector_stores APIを使用（Beta API）")
        return client.beta.vector_stores
    
    # パターン3: betaの下の異なる名前をチェック
    if hasattr(client, 'beta'):
        beta_attrs = dir(client.beta)
        # ベクトル関連の属性を探す
        for attr in beta_attrs:
            if 'vector' in attr.lower() and 'store' in attr.lower():
                print(f"✅ beta.{attr} APIを使用")
                return getattr(client.beta, attr)
    
    # 見つからない場合
    print("❌ ベクトルストアAPIが見つかりません")
    print(f"   利用可能な属性: {dir(client)[:10]}...")  # 最初の10個だけ表示
    if hasattr(client, 'beta'):
        print(f"   Beta属性: {dir(client.beta)[:10]}...")  # 最初の10個だけ表示
    
    return None


def get_vector_store_files_api(client: Any) -> Optional[Any]:
    """
    利用可能なベクトルストアファイルAPIを取得
    
    Args:
        client: OpenAIクライアント（同期または非同期）
    
    Returns:
        ベクトルストアファイルAPI、または None
    """
    # まずベクトルストアAPIを取得
    vs_api = get_vector_store_api(client)
    
    if vs_api and hasattr(vs_api, 'files'):
        return vs_api.files
    
    # file_batchesもチェック（一部のSDKバージョンでは異なる名前）
    if vs_api and hasattr(vs_api, 'file_batches'):
        print("⚠️ file_batchesを使用（filesの代わり）")
        return vs_api.file_batches
    
    return None


async def safe_create_vector_store(client: Any, name: str, metadata: dict = None) -> Optional[str]:
    """
    安全にベクトルストアを作成
    
    Args:
        client: 非同期OpenAIクライアント
        name: ベクトルストア名
        metadata: メタデータ（オプション）
    
    Returns:
        作成されたベクトルストアID、またはNone
    """
    try:
        vs_api = get_vector_store_api(client)
        if not vs_api:
            return None
        
        # メタデータ付きで作成を試みる
        if metadata:
            try:
                vector_store = await vs_api.create(
                    name=name,
                    metadata=metadata
                )
            except TypeError:
                # metadataパラメータがサポートされていない場合
                print("⚠️ メタデータはサポートされていません")
                vector_store = await vs_api.create(name=name)
        else:
            vector_store = await vs_api.create(name=name)
        
        return vector_store.id
        
    except Exception as e:
        print(f"❌ ベクトルストア作成エラー: {e}")
        return None


async def safe_list_vector_stores(client: Any) -> list:
    """
    安全にベクトルストアリストを取得
    
    Args:
        client: 非同期OpenAIクライアント
    
    Returns:
        ベクトルストアのリスト
    """
    try:
        vs_api = get_vector_store_api(client)
        if not vs_api:
            return []
        
        result = await vs_api.list()
        return result.data if hasattr(result, 'data') else []
        
    except Exception as e:
        print(f"❌ ベクトルストア一覧取得エラー: {e}")
        return []


async def safe_retrieve_vector_store(client: Any, vs_id: str) -> Optional[Any]:
    """
    安全にベクトルストアを取得
    
    Args:
        client: 非同期OpenAIクライアント
        vs_id: ベクトルストアID
    
    Returns:
        ベクトルストアオブジェクト、またはNone
    """
    try:
        vs_api = get_vector_store_api(client)
        if not vs_api:
            return None
        
        return await vs_api.retrieve(vs_id)
        
    except Exception as e:
        print(f"❌ ベクトルストア取得エラー: {e}")
        return None


async def safe_delete_vector_store(client: Any, vs_id: str) -> bool:
    """
    安全にベクトルストアを削除
    
    Args:
        client: 非同期OpenAIクライアント
        vs_id: ベクトルストアID
    
    Returns:
        成功/失敗
    """
    try:
        vs_api = get_vector_store_api(client)
        if not vs_api:
            return False
        
        await vs_api.delete(vs_id)
        return True
        
    except Exception as e:
        print(f"❌ ベクトルストア削除エラー: {e}")
        return False


async def safe_update_vector_store(client: Any, vs_id: str, name: str = None, metadata: dict = None) -> bool:
    """
    安全にベクトルストアを更新
    
    Args:
        client: 非同期OpenAIクライアント
        vs_id: ベクトルストアID
        name: 新しい名前（オプション）
        metadata: 新しいメタデータ（オプション）
    
    Returns:
        成功/失敗
    """
    try:
        vs_api = get_vector_store_api(client)
        if not vs_api:
            return False
        
        kwargs = {"vector_store_id": vs_id}
        if name:
            kwargs["name"] = name
        if metadata:
            kwargs["metadata"] = metadata
        
        await vs_api.update(**kwargs)
        return True
        
    except Exception as e:
        print(f"❌ ベクトルストア更新エラー: {e}")
        return False


async def safe_add_file_to_vector_store(client: Any, vs_id: str, file_id: str) -> bool:
    """
    安全にファイルをベクトルストアに追加
    
    Args:
        client: 非同期OpenAIクライアント
        vs_id: ベクトルストアID
        file_id: ファイルID
    
    Returns:
        成功/失敗
    """
    try:
        vs_files_api = get_vector_store_files_api(client)
        if not vs_files_api:
            return False
        
        # 通常のfiles APIを試す
        if hasattr(vs_files_api, 'create'):
            await vs_files_api.create(
                vector_store_id=vs_id,
                file_id=file_id
            )
            return True
        
        # file_batches APIを試す
        elif hasattr(vs_files_api, 'create'):
            await vs_files_api.create(
                vector_store_id=vs_id,
                file_ids=[file_id]
            )
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ ファイル追加エラー: {e}")
        return False

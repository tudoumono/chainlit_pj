## **多機能AIワークスペース 開発リファレンスドキュメント**

**更新日:** 2025年8月24日

### **はじめに**

本ドキュメントは、Chainlit (v2.6.8) と OpenAI Responses API を使用して多機能AIワークスペースを構築するために必要な技術要素を網羅的に解説するものです。これまでの対話で議論されたすべての機能について、その有用性、具体的な実装方法、および公式ドキュメントへのリンクをまとめています。

---

### **Part 1: Chainlit (v2.6.8) 機能リファレンス**

Chainlitは、アプリケーションのUI層とユーザーインタラクションを担当します。

#### **1. 基本的なチャットのライフサイクル**

**概要と有用性:**
アプリケーションの最も基本的な骨格です。チャットセッションの開始時と、ユーザーがメッセージを送信するたびに特定の処理を実行するように定義します。

**具体的な呼び出し方:**
```python
import chainlit as cl

# チャットセッションが開始された時に一度だけ実行される
@cl.on_chat_start
async def start():
    await cl.Message(content="ようこそ！AIワークスペースへ。").send()

# ユーザーがメッセージを送信するたびに実行される
@cl.on_message
async def main(message: cl.Message):
    await cl.Message(content=f"受信しました: {message.content}").send()
```

**情報ソース:**
*   Chat Life Cycle - Chainlit Docs: [https://docs.chainlit.io/concepts/chat-lifecycle](https://docs.chainlit.io/concepts/chat-lifecycle)

#### **2. Step (ステップ)**

**概要と有用性:**
AIの思考プロセスや時間のかかる処理の内部的な段階を、ネストされたステップとしてUIに表示します。処理の透明性を高め、ユーザーの待ち時間の体感を改善します。

**具体的な呼び出し方:**
```python
import chainlit as cl
import asyncio

@cl.on_message
async def main(message: cl.Message):
    async with cl.Step(name="思考プロセス") as step:
        step.output = "ユーザーの要求を分析しています..."
        await asyncio.sleep(1)
        
        async with cl.Step(name="情報検索", parent_id=step.id) as child_step:
            child_step.output = "関連情報を検索中..."
            await asyncio.sleep(1)

        step.output = "最終的な回答を生成しています。"
    await cl.Message(content="回答が生成されました。").send()
```

**情報ソース:**
*   Step - Chainlit Docs: [https://docs.chainlit.io/concepts/step](https://docs.chainlit.io/concepts/step)

#### **3. Ask User (ユーザーへの質問)**

**概要と有用性:**
処理の途中でユーザーからの追加情報を必要とする場合に、入力を促し、応答があるまで処理を一時停止させます。曖昧さの解消や、対話的なワークフローの構築に不可欠です。

**具体的な呼び出し方:**
```python
import chainlit as cl

@cl.on_message
async def main(message: cl.Message):
    res = await cl.AskUserMessage(
        content="処理を続けるには、あなたの名前を入力してください。",
        timeout=60 # 60秒でタイムアウト
    ).send()

    if res:
        await cl.Message(content=f"こんにちは、{res['output']}さん！").send()
```

**情報ソース:**
*   Ask User - Chainlit Docs: [https://docs.chainlit.io/advanced-features/ask-user](https://docs.chainlit.io/advanced-features/ask-user)

#### **4. Data Persistence (Chat History)**

**概要と有用性:**
ユーザーがブラウザを閉じたり再読み込みしたりしても、会話履歴が失われないようにします。UI上での文脈維持とユーザー体験の向上に必須の機能です。

**具体的な呼び出し方:**

**a. 有効化 (`.chainlit/config.toml`):**
```toml
[features]
chat_history = true
```

**b. コード内でのアクセス (`app.py`):**
```python
import chainlit as cl

@cl.on_chat_start
async def start():
    # 履歴のメッセージ数を表示
    num_messages = len(cl.chat_history)
    if num_messages > 0:
        await cl.Message(content=f"ようこそ、おかえりなさい！この会話には既に{num_messages}件のメッセージがあります。").send()
```

**情報ソース:**
*   Chat History - Chainlit Docs: [https://docs.chainlit.io/data-persistence/history](https://docs.chainlit.io/data-persistence/history)

#### **5. Input Widgets (入力ウィジェット)**

**概要と有用性:**
サイドバーに設定項目（モデル選択、パラメータ調整など）を配置し、ユーザーがAIの挙動を直感的に制御できるようにします。

**具体的な呼び出し方:**
```python
import chainlit as cl

@cl.on_chat_start
async def setup_widgets():
    await cl.ChatSettings(
        [
            cl.Select(id="Model", label="モデル", values=["gpt-4o", "gpt-4-turbo"]),
            cl.Switch(id="WebSearch", label="Web検索を有効化", initial=True),
            cl.Slider(id="Temperature", label="創造性", initial=0.7, min=0, max=2, step=0.1),
            cl.TextInput(id="CustomPrompt", label="カスタムプロンプト", initial="あなたは親切なアシスタントです。")
        ]
    ).send()

@cl.on_message
async def main(message: cl.Message):
    settings = await cl.get_chat_settings()
    model = settings["Model"]
    await cl.Message(content=f"モデル「{model}」を使用して応答します。").send()
```

**情報ソース:**
*   API Reference / Input Widgets - Chainlit Docs (例: TextInput): [https://docs.chainlit.io/api-reference/input-widgets/textinput](https://docs.chainlit.io/api-reference/input-widgets/textinput)

#### **6. Elements (リッチな出力)**

**概要と有用性:**
テキストだけでなく、画像、ファイル、インタラクティブなグラフなどをメッセージに添付して表示します。AIの応答をより豊かで分かりやすくするために極めて重要です。

**具体的な呼び出し方:**
```python
import chainlit as cl
import plotly.graph_objects as go

@cl.on_message
async def main(message: cl.Message):
    # 画像
    image = cl.Image(path="./cat.png", name="image1", display="inline")
    # Plotlyグラフ
    fig = go.Figure(data=[go.Bar(y=[2, 3, 1])])
    plot = cl.Plotly(figure=fig, display="inline")
    
    await cl.Message(
        content="画像とインタラクティブなグラフを添付しました。",
        elements=[image, plot]
    ).send()
```

**情報ソース:**
*   Elements - Chainlit Docs: [https://docs.chainlit.io/concepts/elements](https://docs.chainlit.io/concepts/elements)

#### **7. TaskList (タスクリスト)**

**概要と有用性:**
複数ステップからなるプロセスの進捗状況をリアルタイムで表示します。各タスクの状態（実行中、完了、失敗）をユーザーに明示し、安心感を与えます。

**具体的な呼び出し方:**
```python
import chainlit as cl
import asyncio

@cl.on_message
async def main(message: cl.Message):
    task_list = cl.TaskList()
    task1 = cl.Task(title="データ収集", status=cl.TaskStatus.RUNNING)
    await task_list.add_task(task1)
    await task_list.send()
    
    await asyncio.sleep(2)
    task1.status = cl.TaskStatus.DONE
    task1.output = "収集完了"
    await task_list.send()
```

**情報ソース:**
*   TaskList - Chainlit Docs: [https://docs.chainlit.io/api-reference/elements/tasklist](https://docs.chainlit.io/api-reference/elements/tasklist)

---

### **Part 2: OpenAI Responses API 機能リファレンス**

OpenAIのResponses APIは、AIの頭脳として、文脈理解、ツール利用、応答生成を担当します。

#### **1. 会話履歴管理 (スレッド)**

**概要と有用性:**
`Completions API`と異なり、会話履歴の管理をOpenAI側が行います。`thread_id`という一意のIDを管理するだけで、AIは過去のやり取り、アップロードされたファイル、ツールの実行結果など、すべての文脈を記憶します。開発者は毎回全履歴を送信する必要がありません。

**具体的な呼び出し方:**
```python
from openai import OpenAI
client = OpenAI()

# 1. 新規会話の開始時にスレッドを作成
thread = client.beta.threads.create()
thread_id = thread.id
# この thread_id をDBなどに保存する

# 2. 会話の継続
# DBから thread_id を取得
client.beta.threads.messages.create(
    thread_id=thread_id,
    role="user",
    content="前回の続きの質問です。"
)
stream = client.responses.create(
    thread_id=thread_id,
    assistant_id="YOUR_ASSISTANT_ID",
    stream=True
)
```

**情報ソース:**
*   Assistants Overview (Threads) - OpenAI Docs: [https://platform.openai.com/docs/assistants/overview](https://platform.openai.com/docs/assistants/overview)

#### **2. Web Search (ウェブ検索)**

**概要と有用性:**
AIがリアルタイムのウェブ情報を検索し、回答に反映させることを可能にします。最新の出来事や、学習データに含まれていない情報に関する質問に答えるために不可欠です。

**具体的な呼び出し方:**
```python
# responses.create の呼び出し時にツールとして指定
stream = client.responses.create(
    thread_id=thread_id,
    assistant_id="YOUR_ASSISTANT_ID",
    tools=[{"type": "web_search"}],
    stream=True
)
```

**情報ソース:**
*   Web search - OpenAI API Reference: [https://platform.openai.com/docs/api-reference/web-search](https://platform.openai.com/docs/api-reference/web-search)

#### **3. File Search (ファイル検索 / RAG)**

**概要と有用性:**
ユーザーがアップロードしたファイル（PDF, DOCX等）の内容を、AIが回答の根拠として利用できるようにします。Retrieval-Augmented Generation (RAG) を実現する中核機能であり、社内ドキュメントの問い合わせなどに絶大な効果を発揮します。

**具体的な呼び出し方:**
```python
# 1. Vector Storeを作成し、ファイルをアップロード
vector_store = client.beta.vector_stores.create(name="Project Documents")
with open("document.pdf", "rb") as file_stream:
    client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=[file_stream]
    )

# 2. スレッドにVector Storeを紐付ける
thread = client.beta.threads.create(
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
)
# 3. responses.create 呼び出し時にツールとして指定
stream = client.responses.create(
    thread_id=thread.id,
    assistant_id="YOUR_ASSISTANT_ID",
    tools=[{"type": "file_search"}],
    stream=True
)
```

**情報ソース:**
*   File search - OpenAI API Reference: [https://platform.openai.com/docs/api-reference/file-search](https://platform.openai.com/docs/api-reference/file-search)
*   Doing RAG on PDFs using File Search - OpenAI Cookbook: [https://cookbook.openai.com/examples/file_search_responses](https://cookbook.openai.com/examples/file_search_responses)

#### **4. Code Interpreter (コードインタプリタ)**

**概要と有用性:**
AIがサンドボックス環境でPythonコードを生成・実行できるようにする強力なツールです。データ分析、グラフ作成、ファイル形式の変換などを自律的に行えます。

**具体的な呼び出し方:**```python
stream = client.responses.create(
    thread_id=thread.id,
    assistant_id="YOUR_ASSISTANT_ID",
    tools=[{"type": "code_interpreter"}], # これを追加するだけ
    stream=True
)
```

**情報ソース:**
*   Tools / Code Interpreter - OpenAI Docs: [https://platform.openai.com/docs/assistants/tools/code-interpreter](https://platform.openai.com/docs/assistants/tools/code-interpreter)

#### **5. Function Calling (外部関数の呼び出し)**

**概要と有用性:**
AIが事前に定義された独自のPython関数を呼び出せるようにします。これにより、社内DBへのアクセス、外部API連携、ローカルシステム操作など、AIの能力を外部に拡張できます。

**具体的な呼び出し方:**
(※ストリームの処理が複雑なため要約版を記載)
```python
# 1. 呼び出したい関数と、その情報を定義
def get_stock_price(symbol: str):
    # ...株価を取得する処理...
    return 150.0

tools = [{"type": "function", "function": {...}}] # 関数の仕様をJSONで定義

# 2. API呼び出し時にツールとして渡す
stream = client.responses.create(..., tools=tools)

# 3. ストリーム内でAIからの関数呼び出し要求 (tool_call) を処理し、
#    結果を再度OpenAIに送り返して最終的な回答を生成させる。
```

**情報ソース:**
*   Tools / Function calling - OpenAI Docs: [https://platform.openai.com/docs/assistants/tools/function-calling](https://platform.openai.com/docs/assistants/tools/function-calling)

---

### **Part 3: ChainlitとOpenAIの連携**

この2つのシステムを連携させることが、アプリケーションの中核となります。

**概要と有用性:**
ChainlitのChat History（UI層）とOpenAIのスレッド（AIコンテキスト層）は別物です。`cl.user_session` を「接着剤」として使い、ユーザーが見ているUIとAIが記憶している文脈を同期させます。

**具体的な連携実装:**
```python
import chainlit as cl
from openai import OpenAI
import os

client = OpenAI()

@cl.on_chat_start
async def on_chat_start():
    # 既存のチャット履歴があるか確認
    if cl.chat_history:
        # あれば、セッションからthread_idを復元
        thread_id = cl.user_session.get("thread_id")
        await cl.Message(content=f"会話を再開します。").send()
    else:
        # なければ、新規にスレッドを作成し、IDをセッションに保存
        thread = client.beta.threads.create()
        cl.user_session.set("thread_id", thread.id)
        await cl.Message(content="新しい会話を開始します。").send()

@cl.on_message
async def main(message: cl.Message):
    # セッションから常に正しいthread_idを取得
    thread_id = cl.user_session.get("thread_id")
    
    # このthread_idを使ってOpenAIと通信する
    client.beta.threads.messages.create(...)
    stream = client.responses.create(...)

    # ...ストリーミング処理...
```


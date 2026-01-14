import os
from groq import Groq

# APIキーを設定（環境変数などで管理するのが推奨）
api_key = os.environ.get("GROQ_API_KEY")

if api_key is None:
    # キーがない場合の例外処理
    print("Error: GROQ_API_KEY is not set.")
else:
    client = Groq(api_key=api_key)

chat_completion = client.chat.completions.create(
    messages=[
        {"role": "user", "content": "Geminiについて教えて"}
    ],
    model="openai/gpt-oss-120b",  # モデルの指定
)

print(chat_completion.choices[0].message.content)
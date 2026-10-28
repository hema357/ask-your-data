import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
api_key = os.getenv("LLM_API_KEY")

client = Groq(api_key=api_key)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": "Reply with the word OK"}],
)

print(response.choices[0].message.content)
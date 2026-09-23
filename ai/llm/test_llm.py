from ai.llm.client import LocalLLM


llm = LocalLLM()


messages = [
    {
        "role": "system",
        "content": (
            "You are Vishakha's AI Employee Assistant. "
            "Be concise and helpful."
        ),
    },
    {
        "role": "user",
        "content": "Hello, introduce yourself in one sentence.",
    },
]


response = llm.chat(messages)


print("\nAI RESPONSE:")
print(response)
import requests


class LocalLLM:

    def __init__(self):
        self.base_url = "http://127.0.0.1:8080"

    def chat(self, messages):

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 500,
            },
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        return data["choices"][0]["message"]["content"]
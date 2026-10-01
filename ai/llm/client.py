import json
import requests

from ai.llm.cancellation import (
    get_request,
    LLMCancelled,
)

class LocalLLM:

    def __init__(self):

        self.base_url = "http://127.0.0.1:8080"


    def chat(self, messages, chat_id=None):

        cancel_event = get_request(
            chat_id
        )

        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 500,
                "stream": True,
            },
            stream=True,
            timeout=120,
        )


        if not response.ok:

            print("\n========== LLM ERROR ==========")
            print("HTTP STATUS:", response.status_code)
            print("RESPONSE:", response.text)
            print("================================\n")


        response.raise_for_status()


        generated_text = ""


        try:

            for line in response.iter_lines():

                # Stop was requested for this conversation
                if (
                    cancel_event
                    and cancel_event.is_set()
                ):
                    print(
                        "LLM GENERATION CANCELLED FOR CHAT:",
                        chat_id
                    )

                    raise LLMCancelled(
                        f"LLM generation cancelled for chat {chat_id}"
                    )

                if not line:
                    continue


                line = line.decode(
                    "utf-8"
                ).strip()


                if not line.startswith(
                    "data:"
                ):
                    continue


                data = line[
                    len("data:"):
                ].strip()


                if data == "[DONE]":
                    break


                try:

                    chunk = json.loads(
                        data
                    )

                except json.JSONDecodeError:
                    continue


                choices = chunk.get(
                    "choices",
                    []
                )


                if not choices:
                    continue


                delta = choices[0].get(
                    "delta",
                    {}
                )


                content = delta.get(
                    "content"
                )


                if content:

                    generated_text += content


        finally:

            response.close()


        return generated_text
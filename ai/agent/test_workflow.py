import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings"
)

import django
django.setup()

from ai.agent.workflow import AgentWorkflow


def main():
    workflow = AgentWorkflow()

    print("=" * 60)
    print("DARPAN - AGENT WORKFLOW TEST")
    print("=" * 60)
    print("Type 'exit' or 'quit' to stop.")
    print("Type 'reset' to start a new conversation.")

    while True:

        user_message = input("\nUSER:\n").strip()

        if not user_message:
            continue

        # Exit
        if user_message.lower() in ["exit", "quit"]:
            print("\nExiting test workflow...")
            break

        # Reset conversation
        if user_message.lower() == "reset":

            workflow = AgentWorkflow()

            print("\nAI:")
            print({
                "type": "message",
                "message": "Conversation has been reset."
            })

            continue

        try:

            response = workflow.process_message(user_message)

            print("\nAI:")
            print(response)

        except Exception as e:

            print("\nERROR:")
            print(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
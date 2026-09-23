import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from ai.agent.conversation import ConversationState
from ai.agent.workflow import AgentWorkflow


def home(request):

    return render(
        request,
        "assistant/index.html"
    )


# =========================================================
# SESSION WORKFLOW
# =========================================================

def get_workflow(request):

    state_data = request.session.get(
        "assistant_state"
    )

    state = ConversationState()

    if state_data:

        state.from_dict(
            state_data
        )

    workflow = AgentWorkflow(
        state=state
    )

    return workflow


def save_workflow(request, workflow):

    request.session[
        "assistant_state"
    ] = workflow.state.to_dict()

    request.session.modified = True


# =========================================================
# CHAT API
# =========================================================

@csrf_exempt
@require_POST
def chat(request):

    try:

        data = json.loads(
            request.body
        )

        user_message = data.get(
            "message",
            ""
        ).strip()

        message_type = data.get(
            "message_type",
            "text"
        )


        if not user_message:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "Message cannot be empty."
                },
                status=400
            )


        # ---------------------------------------------
        # Get this user's workflow
        # ---------------------------------------------

        workflow = get_workflow(
            request
        )


        # ---------------------------------------------
        # Process request
        # ---------------------------------------------

        if message_type == "option":

            if user_message == "Confirm & Create Ticket":

                result = workflow.confirm_ticket()

            elif user_message == "Cancel":

                result = workflow.cancel()

            else:

                result = workflow.handle_option(
                    user_message
                )

        else:

            result = workflow.process_message(
                user_message
            )


        # ---------------------------------------------
        # Save updated state
        # ---------------------------------------------

        save_workflow(
            request,
            workflow
        )


        # ---------------------------------------------
        # Return response
        # ---------------------------------------------

        return JsonResponse(
            {
                "success": True,
                "type": result.get("type"),
                "message": result.get("message"),
                "response": result,
            }
        )


    except Exception as e:

        print(
            "CHAT ERROR:",
            str(e)
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(e)
            },
            status=500
        )

@require_GET
def chat_state(request):

    workflow = get_workflow(request)

    state = workflow.state

    missing = state.get_missing_fields()

    # No active conversation
    if not state.intent:

        return JsonResponse({
            "success": True,
            "active": False,
        })

    # Current pending question
    if state.current_question:

        question_map = {

            "description": {
                "message": "What issue are you facing?",
                "options": [
                    "Screen not working",
                    "Laptop not switching on",
                    "Keyboard issue",
                    "Battery/charging issue",
                    "Other",
                ],
            },

            "location": {
                "message": "Where are you currently located?",
                "options": [
                    "Ahmedabad Plant",
                    "Noida Plant",
                    "Corporate Office",
                    "Other",
                ],
            },

            "priority": {
                "message": "What priority should this ticket have?",
                "options": [
                    "Low",
                    "Medium",
                    "High",
                    "Critical",
                ],
            },

        }

        question = question_map.get(
            state.current_question
        )

        if question:

            return JsonResponse({
                "success": True,
                "active": True,
                "type": "question",
                "field": state.current_question,
                "message": question["message"],
                "options": question["options"],
            })


    # Conversation is complete and waiting for confirmation
    if state.is_complete():

        return JsonResponse({
            "success": True,
            "active": True,
            "type": "confirmation",
            "message": "Please confirm the ticket details.",
            "ticket": state.get_summary(),
        })


    return JsonResponse({
        "success": True,
        "active": False,
    })

@csrf_exempt
@require_POST
def new_chat(request):

    # Remove the current assistant workflow state
    request.session.pop(
        "assistant_state",
        None
    )

    request.session.modified = True

    return JsonResponse({
        "success": True,
        "message": "New chat started."
    })
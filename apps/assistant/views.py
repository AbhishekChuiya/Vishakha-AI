import json

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from ai.agent.conversation import ConversationState
from ai.agent.workflow import AgentWorkflow
import time
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from ai.llm.cancellation import (
    register_request,
    cancel_request,
    unregister_request,
    LLMCancelled,
)

def login_view(request):

    # Already logged in
    if request.user.is_authenticated:
        return redirect("/")

    error = None

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            return redirect("/")

        error = "Invalid username or password."

    return render(
        request,
        "assistant/login.html",
        {
            "error": error
        }
    )


def signup_view(request):

    # Already logged in
    if request.user.is_authenticated:
        return redirect("/")

    error = None

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        # Basic validation
        if not username:
            error = "Username is required."

        elif not email:
            error = "Email address is required."

        elif password != confirm_password:
            error = "Passwords do not match."

        elif not (
            email.lower().endswith("@vishakha.com")
            or email.lower().endswith("@gmail.com")
        ):
            error = (
                "Please use a Vishakha or Gmail email address."
            )

        elif User.objects.filter(
            username__iexact=username
        ).exists():
            error = "This username is already registered."


        elif User.objects.filter(
            email__iexact=email
        ).exists():
            error = "This email address is already registered."

        else:

            try:
                validate_password(
                    password,
                    user=User(
                        username=username,
                        email=email
                    )
                )

            except ValidationError as validation_error:
                error = " ".join(
                    validation_error.messages
                )

            if error is None:

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                login(
                    request,
                    user
                )

                return redirect("/")

    return render(
        request,
        "assistant/signup.html",
        {
            "error": error
        }
    )

def logout_view(request):

    logout(request)

    return redirect("/login/")

@login_required
def home(request):

    return render(
        request,
        "assistant/index.html"
    )


# =========================================================
# SESSION WORKFLOW
# =========================================================

def get_workflow(request, chat_id=None):

    state = ConversationState()

    # ---------------------------------------------
    # Multi-chat workflow state
    # ---------------------------------------------

    if chat_id:

        assistant_chats = request.session.get(
            "assistant_chats",
            {}
        )

        state_data = assistant_chats.get(
            chat_id
        )


        # # TEMPORARY DEBUG
        # print(
        #     "\n========== GET WORKFLOW DEBUG =========="
        # )

        # print(
        #     "REQUESTED CHAT ID:",
        #     repr(chat_id)
        # )

        # print(
        #     "AVAILABLE CHAT IDS:",
        #     list(assistant_chats.keys())
        # )

        # print(
        #     "STATE DATA FOUND:",
        #     state_data
        # )

        # print(
        #     "========================================\n"
        # )


        if state_data:

            state.from_dict(
                state_data
            )

    # ---------------------------------------------
    # Legacy single-chat fallback
    # ---------------------------------------------

    else:

        state_data = request.session.get(
            "assistant_state"
        )

        if state_data:

            state.from_dict(
                state_data
            )


    workflow = AgentWorkflow(
        state=state,
        requester_email=(
            request.user.email
            if request.user.is_authenticated
            else None
        ),
        actor_email=(
            request.user.email
            if request.user.is_authenticated
            else None
        ),
    )

    return workflow

def save_workflow(
    request,
    workflow,
    chat_id=None
):

    # ---------------------------------------------
    # Multi-chat workflow state
    # ---------------------------------------------

    if chat_id:

        # Always create a fresh dictionary copy.
        # This avoids nested Django session
        # mutation/persistence problems.
        assistant_chats = dict(
            request.session.get(
                "assistant_chats",
                {}
            )
        )

        assistant_chats[
            chat_id
        ] = workflow.state.to_dict()

        # Reassign the complete dictionary
        # back into the Django session.
        request.session[
            "assistant_chats"
        ] = assistant_chats


        # print(
        #     "SAVED CHAT IDS:",
        #     list(assistant_chats.keys())
        # )

    # ---------------------------------------------
    # Legacy single-chat fallback
    # ---------------------------------------------

    else:

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

        # ---------------------------------------------
        # Conversation ID
        # ---------------------------------------------

        chat_id = data.get(
            "chat_id"
        )

        if chat_id:
            chat_id = str(
                chat_id
            ).strip()


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
            request,
            chat_id=chat_id
        )

        # print("\n================ CHAT DEBUG ================")
        # print("CHAT ID:", chat_id)
        # print("MESSAGE:", user_message)
        # print("MESSAGE TYPE:", message_type)
        # print("CURRENT QUESTION:", workflow.state.current_question)
        # print("DEPARTMENT:", workflow.state.department)
        # print("REQUEST TYPE:", workflow.state.request_type)
        # print("CATEGORY:", workflow.state.selected_category)
        # print("SUBCATEGORY:", workflow.state.subcategory)
        # print("LOCATION:", workflow.state.location)
        # print("============================================\n")

        # ---------------------------------------------
        # Register cancellable AI request
        # ---------------------------------------------

        cancel_event = register_request(
            chat_id
        )
        # ---------------------------------------------
        # Process request
        # ---------------------------------------------
        request_start_time = time.perf_counter()

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

            try:
                result = workflow.process_message(
                    user_message,
                    chat_id=chat_id
                )

            except LLMCancelled:
                print(
                    "CHAT REQUEST CANCELLED:",
                    chat_id
                )

                return JsonResponse(
                    {
                        "success": False,
                        "cancelled": True,
                        "message": "Generation stopped."
                    },
                    status=200
                )

            finally:
                unregister_request(
                    chat_id,
                    cancel_event
                )

        request_end_time = time.perf_counter()

        print(
            "WORKFLOW PROCESSING TIME:",
            round(
                request_end_time -
                request_start_time,
                2
            ),
            "seconds"
        )

        # ---------------------------------------------
        # Save updated state
        # ---------------------------------------------

        save_workflow(
            request,
            workflow,
            chat_id=chat_id
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

    # ---------------------------------------------
    # Conversation ID
    # ---------------------------------------------

    chat_id = request.GET.get(
        "chat_id"
    )

    if chat_id:
        chat_id = str(
            chat_id
        ).strip()


    # ---------------------------------------------
    # Load this conversation's workflow
    # ---------------------------------------------

    workflow = get_workflow(
        request,
        chat_id=chat_id
    )

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
                "request_type": {
                "message":
                    "Please select the Request Type.",
                "options": [],
            },

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

            "impact": {
                "message":
                    "What is the impact of this incident?",
                "options": [
                    "Low",
                    "Medium",
                    "High",
                ],
            },

            "start_time": {
                "message":
                    "When did this incident start?",
                "options": [],
                "input_type":
                    "datetime-local",
                "placeholder":
                    "Select incident start date and time",
            },

            "target_date": {
                "message":
                    "When do you need this request completed by?",
                "options": [],
                "input_type":
                    "date",
                "placeholder":
                    "Select target date",
            },

            "business_justification": {
                "message":
                    "Please provide the business justification for this request.",
                "options": [],
                "input_type":
                    "text",
                "placeholder":
                    "Enter business justification",
            },

            "urgency": {
                "message":
                    "Please select the urgency of this request.",
                "options": [
                    "Low",
                    "Medium\t- Work is significantly hindered",
                    "High",
                ],
            },

            "email": {
                "message":
                    "Please enter your email address.",
                "options": [],
                "input_type":
                    "text",
                "placeholder":
                    "Enter email address",
            },

            "phone": {
                "message":
                    "Please enter your phone number.",
                "options": [],
                "input_type":
                    "text",
                "placeholder":
                    "Enter phone number",
            },

        }

        # ---------------------------------------------
        # Request Type options depend on Department
        # ---------------------------------------------

        if (
            state.current_question ==
            "request_type"
        ):

            request_types = {
                "IT Department": [
                    "Incident Request",
                    "Service Request",
                ],
                "Admin": [
                    "Incident Request",
                    "Service Request",
                ],
                "Safety": [
                    "Incident Request",
                    "Service Request",
                ],
                "Security": [
                    "Incident Request",
                ],
                "Branding": [
                    "Change Management",
                    "Request For Information",
                    "Service Request",
                ],
                "HR Department": [
                    "Incident Request",
                    "Service Request",
                ],
                "Finance": [
                    "Service Request",
                ],
                "Insurance": [
                    "Service Request",
                ],
                "Compliance & Risk": [
                    "Service Request",
                ],
                "Projects": [
                    "Change Management",
                ],
                "Quality management": [
                    "Customer Complaint",
                ],
                "Strategy": [
                    "Service Request",
                ],
            }

            question_map[
                "request_type"
            ][
                "options"
            ] = request_types.get(
                state.department,
                []
            )



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
                "department": state.department,
                "input_type": question.get("input_type"),
                "placeholder": question.get("placeholder"),
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

    try:

        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        data = {}


    chat_id = data.get(
        "chat_id"
    )

    if chat_id:

        chat_id = str(
            chat_id
        ).strip()


    # ---------------------------------------------
    # Initialize only this new conversation.
    #
    # IMPORTANT:
    # Do not remove any previous chat states.
    # ---------------------------------------------

    if chat_id:

        assistant_chats = request.session.get(
            "assistant_chats",
            {}
        )

        # Make sure this ID starts with
        # a completely fresh workflow state.
        assistant_chats[
            chat_id
        ] = ConversationState().to_dict()

        request.session[
            "assistant_chats"
        ] = assistant_chats

        # print(
        #     "SAVED CHAT IDS:",
        #     list(assistant_chats.keys())
        # )

    else:

        # Legacy fallback
        request.session.pop(
            "assistant_state",
            None
        )


    request.session.modified = True


    return JsonResponse({
        "success": True,
        "message": "New chat started.",
        "chat_id": chat_id,
    })

@csrf_exempt
@require_POST
def delete_chat(request):

    try:

        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON."
            },
            status=400
        )


    chat_id = data.get(
        "chat_id"
    )


    if not chat_id:

        return JsonResponse(
            {
                "success": False,
                "error": "chat_id is required."
            },
            status=400
        )


    chat_id = str(
        chat_id
    ).strip()


    # ---------------------------------------------
    # Remove only this conversation
    # ---------------------------------------------

    assistant_chats = dict(
        request.session.get(
            "assistant_chats",
            {}
        )
    )


    existed = (
        chat_id in assistant_chats
    )


    assistant_chats.pop(
        chat_id,
        None
    )


    request.session[
        "assistant_chats"
    ] = assistant_chats

    request.session.modified = True


    print(
        "DELETED CHAT ID:",
        chat_id
    )

    print(
        "REMAINING CHAT IDS:",
        list(
            assistant_chats.keys()
        )
    )


    return JsonResponse({
        "success": True,
        "deleted": existed,
        "chat_id": chat_id,
    })

# =========================================================
# STOP ACTIVE AI RESPONSE
# =========================================================

@csrf_exempt
@require_POST
def stop_chat(request):

    try:

        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid JSON."
            },
            status=400
        )


    chat_id = data.get(
        "chat_id"
    )


    if not chat_id:

        return JsonResponse(
            {
                "success": False,
                "error": "chat_id is required."
            },
            status=400
        )


    chat_id = str(
        chat_id
    ).strip()


    print(
        "STOP REQUEST RECEIVED FOR CHAT:",
        chat_id
    )

    cancelled = cancel_request(
        chat_id
    )

    print(
        "ACTIVE AI REQUEST CANCELLED:",
        cancelled
    )

    return JsonResponse(
        {
            "success": True,
            "stopped": cancelled,
            "chat_id": chat_id
        }
    )
import json
import logging

from openai import OpenAI

from app.config import settings
from app.token_tracker import extract_usage_from_response, log_token_usage

logger = logging.getLogger("entitlements-chat.intent_router")


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in backend/.env (OPENAI_API_KEY=...)"
        )
    return OpenAI(api_key=settings.openai_api_key)


INTENTS = [
    "users_in_dept_for_app",   # e.g. 'Show active users in DEPT_5 who are entitled to APP_3'
    "users_in_dept",           # e.g. 'Show users from DEPT_5', 'How many users in Department 1'
    "departments_for_app",     # e.g. 'Which departments have access to APP_1'
    "apps_for_dept",           # e.g. 'Which applications are available to DEPT_5'
    "app_metadata",            # e.g. 'What is the state / criticality of APP_2'
    "generic_sql",             # needs SQL but no specific template
    "knowledge_only"           # docs/schema only
]


def classify_intent(question: str) -> dict:
    """
    Uses OpenAI to classify the question into a small set of intents and
    extract normalized codes (e.g. APP_3, DEPT_5).
    Returns a dict:
      {intent, app_code?, dept_code?}
    """
    system = (
        "You are an intent classifier for the Entitlements Platform chat.\n"
        "Your job is to:\n"
        "- Decide which high-level intent a question belongs to.\n"
        "- Extract application and department codes when relevant.\n\n"
        "Allowed intents:\n"
        "  - users_in_dept_for_app: questions about users in a department for a specific application\n"
        "  - users_in_dept: questions about users in a single department, without specifying an application\n"
        "  - departments_for_app: questions about which departments have access to an application\n"
        "  - apps_for_dept: questions about which applications are available to a department\n"
        "  - app_metadata: questions about an application's state, status, lifecycle, criticality\n"
        "  - generic_sql: any question that needs SQL to query data (e.g., 'what is the name of user X', 'show me user details', 'list all applications')\n"
        "  - knowledge_only: pure documentation / explanation questions (e.g., 'how does it work', 'explain the architecture')\n\n"
        "IMPORTANT: Questions asking for specific data values (names, emails, counts, lists) should be classified as 'generic_sql', NOT 'knowledge_only'.\n\n"
        "Codes:\n"
        "- Application codes look like APP_1, APP_2, etc.\n"
        "- Department codes look like DEPT_1, DEPT_2, etc.\n"
        "- If the user says 'Application 3' or 'App 3', normalize that to APP_3.\n"
        "- If the user says 'Department 5' or 'Dept 5', normalize that to DEPT_5.\n\n"
        "Respond ONLY with a compact JSON object like:\n"
        "  {\"intent\":\"users_in_dept_for_app\",\"app_code\":\"APP_3\",\"dept_code\":\"DEPT_5\"}\n"
        "or:\n"
        "  {\"intent\":\"knowledge_only\"}\n"
    )

    examples = [
        {
            "question": "Show active users in DEPT_5 who are entitled to APP_3.",
            "result": {
                "intent": "users_in_dept_for_app",
                "app_code": "APP_3",
                "dept_code": "DEPT_5",
            },
        },
        {
            "question": "Which departments have access to Application 1?",
            "result": {
                "intent": "departments_for_app",
                "app_code": "APP_1",
            },
        },
        {
            "question": "Show users from DEPT_5",
            "result": {
                "intent": "users_in_dept",
                "dept_code": "DEPT_5"
            }
        },
        {
            "question": "How many users are in Department 1?",
            "result": {
                "intent": "users_in_dept",
                "dept_code": "DEPT_1"
            }
        },
        {
            "question": "What is the criticality and lifecycle state of App 2?",
            "result": {
                "intent": "app_metadata",
                "app_code": "APP_2",
            },
        },
        {
            "question": "Which applications are available to Department 5?",
            "result": {
                "intent": "apps_for_dept",
                "dept_code": "DEPT_5",
            },
        },
        {
            "question": "What apps can DEPT_3 access?",
            "result": {
                "intent": "apps_for_dept",
                "dept_code": "DEPT_3",
            },
        },
        {
            "question": "What is the name of user whose username is user00001?",
            "result": {
                "intent": "generic_sql",
            },
        },
        {
            "question": "Show me the email of user user00001",
            "result": {
                "intent": "generic_sql",
            },
        },
        {
            "question": "What is the policy rule for application with app code APP_1?",
            "result": {
                "intent": "generic_sql",
            },
        },
        {
            "question": "What is the policy rule for application id 301?",
            "result": {
                "intent": "generic_sql",
            },
        },
        {
            "question": "Show me the policy rules for APP_2",
            "result": {
                "intent": "generic_sql",
            },
        },
        {
            "question": "Explain how entitlements are evaluated at login.",
            "result": {
                "intent": "knowledge_only",
            },
        },
    ]

    user = {
        "question": question,
        "examples": examples,
        "intents": INTENTS,
    }

    client = _client()
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
        temperature=0.0,
    )
    
    # Track token usage and cost
    usage = extract_usage_from_response(resp.usage, model=settings.openai_model)
    if usage:
        log_token_usage(usage, context="intent_classification")
    
    content = (resp.choices[0].message.content or "").strip()
    logger.info("classify_intent raw LLM content: %s", content)

    try:
        obj = json.loads(content)
        if not isinstance(obj, dict):
            raise ValueError("intent output not a dict")
    except Exception:
        logger.warning("classify_intent: could not parse JSON, defaulting to generic_sql")
        return {"intent": "generic_sql"}

    intent = obj.get("intent") or "generic_sql"
    if intent not in INTENTS:
        intent = "generic_sql"

    return {
        "intent": intent,
        "app_code": obj.get("app_code"),
        "dept_code": obj.get("dept_code"),
    }



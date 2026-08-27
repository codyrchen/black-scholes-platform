from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from voice_agent import knowledge

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Look up an order by order ID (e.g. ORD-1001).",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The order ID, e.g. ORD-1001",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_customer",
            "description": "Look up a customer account by email address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Customer email address"},
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_faq",
            "description": "Get company policy or FAQ information on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": ["hours", "refund", "billing", "api", "cancel"],
                        "description": "FAQ topic key",
                    }
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Create a support ticket for issues that need human follow-up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Customer email"},
                    "subject": {"type": "string", "description": "Brief subject line"},
                    "description": {"type": "string", "description": "Issue description"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Ticket priority",
                    },
                },
                "required": ["email", "subject", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Transfer the caller to a live human agent when the issue cannot be resolved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Why escalation is needed"},
                },
                "required": ["reason"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "lookup_order":
        order_id = arguments.get("order_id", "").upper()
        order = knowledge.ORDERS.get(order_id)
        if not order:
            return {"found": False, "message": f"No order found with ID {order_id}."}
        return {
            "found": True,
            "order_id": order.order_id,
            "status": order.status,
            "items": order.items,
            "total": order.total,
            "estimated_delivery": order.estimated_delivery,
            "customer_email": order.customer_email,
        }

    if name == "lookup_customer":
        email = arguments.get("email", "").lower()
        customer = knowledge.CUSTOMERS.get(email)
        if not customer:
            return {"found": False, "message": f"No account found for {email}."}
        return {
            "found": True,
            "name": customer.name,
            "email": customer.email,
            "plan": customer.plan,
            "account_status": customer.account_status,
        }

    if name == "get_faq":
        topic = arguments.get("topic", "")
        answer = knowledge.FAQ.get(topic)
        if not answer:
            return {"found": False, "message": f"No FAQ entry for topic '{topic}'."}
        return {"found": True, "topic": topic, "answer": answer}

    if name == "create_support_ticket":
        ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
        ticket = {
            "ticket_id": ticket_id,
            "email": arguments.get("email", ""),
            "subject": arguments.get("subject", ""),
            "description": arguments.get("description", ""),
            "priority": arguments.get("priority", "medium"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "open",
        }
        knowledge.TICKETS[ticket_id] = ticket
        return {
            "success": True,
            "ticket_id": ticket_id,
            "message": f"Support ticket {ticket_id} created. A team member will respond within 24 hours.",
        }

    if name == "escalate_to_human":
        return {
            "escalate": True,
            "reason": arguments.get("reason", ""),
            "message": "Transferring you to a live agent now. Please hold.",
        }

    return {"error": f"Unknown tool: {name}"}

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_email: str
    status: str
    items: list[str]
    total: float
    estimated_delivery: str


@dataclass(frozen=True)
class Customer:
    email: str
    name: str
    plan: str
    account_status: str


# Sample in-memory customer service data (replace with CRM/database in production).
ORDERS: dict[str, Order] = {
    "ORD-1001": Order(
        order_id="ORD-1001",
        customer_email="jane@example.com",
        status="shipped",
        items=["Options Analytics Pro (annual)"],
        total=299.0,
        estimated_delivery="2026-06-18",
    ),
    "ORD-1002": Order(
        order_id="ORD-1002",
        customer_email="john@example.com",
        status="processing",
        items=["API Access (monthly)", "Historical Data Add-on"],
        total=149.0,
        estimated_delivery="2026-06-20",
    ),
    "ORD-1003": Order(
        order_id="ORD-1003",
        customer_email="jane@example.com",
        status="delivered",
        items=["Team License (5 seats)"],
        total=999.0,
        estimated_delivery="2026-06-10",
    ),
}

CUSTOMERS: dict[str, Customer] = {
    "jane@example.com": Customer(
        email="jane@example.com",
        name="Jane Smith",
        plan="Pro",
        account_status="active",
    ),
    "john@example.com": Customer(
        email="john@example.com",
        name="John Doe",
        plan="Starter",
        account_status="active",
    ),
}

FAQ = {
    "hours": "Our support team is available Monday through Friday, 9 AM to 6 PM Eastern Time.",
    "refund": "We offer a 14-day money-back guarantee on all new subscriptions. Refunds are processed within 5–7 business days.",
    "billing": "You can update your payment method in Account Settings under Billing. We accept Visa, Mastercard, and ACH transfers.",
    "api": "API rate limits are 1,000 requests per minute on Pro plans and 100 on Starter plans. Enterprise plans have custom limits.",
    "cancel": "You can cancel anytime from Account Settings. Your access continues until the end of the current billing period.",
}

TICKETS: dict[str, dict] = {}

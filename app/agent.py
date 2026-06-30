# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import LongRunningFunctionTool
from google.genai import types

import os
import google.auth

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"


import random
from google.adk.tools.tool_context import ToolContext

# UCP/A2A の商品カタログ (products.json に準拠)
PRODUCTS = {
    "BISC-001": {"title": "Chocochip Cookies", "price": 4.99},
    "STRAW-001": {"title": "Fresh Strawberries", "price": 4.49},
    "CHIPS-001": {"title": "Classic Potato Chips", "price": 3.79},
    "SW-CHIPS-001": {"title": "Baked Sweet Potato Chips", "price": 4.79},
}


def search_shopping_catalog(query: str) -> str:
    """Search the product catalog for products that match the given query.

    Args:
        query: The search term (e.g. cookies, strawberries, chips).
    """
    query_lower = query.lower()
    matches = [
        (pid, info)
        for pid, info in PRODUCTS.items()
        if query_lower in pid.lower() or query_lower in info["title"].lower()
    ]
    if not matches:
        return f"No products found matching '{query}'."

    res = "Available Products in Stock:\n"
    for pid, info in matches:
        res += f"- [ID: {pid}] {info['title']} - ${info['price']}\n"
    return res


def add_to_checkout(
    tool_context: ToolContext, product_id: str, quantity: int = 1
) -> str:
    """Add a product to the checkout session.

    Args:
        tool_context: The tool context containing session state.
        product_id: The ID or SKU of the product to add (e.g., BISC-001).
        quantity: The quantity of the product to add. Defaults to 1.
    """
    if product_id not in PRODUCTS:
        return f"Error: Product ID '{product_id}' does not exist. Please search for valid products first."

    if "cart" not in tool_context.state:
        tool_context.state["cart"] = {}

    cart = tool_context.state["cart"]
    cart[product_id] = cart.get(product_id, 0) + quantity
    tool_context.state["cart"] = cart

    summary = "Current Cart Summary:\n"
    total = 0.0
    for pid, qty in cart.items():
        pinfo = PRODUCTS[pid]
        subtotal = pinfo["price"] * qty
        total += subtotal
        summary += f"- {pinfo['title']} (x{qty}) - ${subtotal:.2f}\n"
    summary += f"Total Amount: ${total:.2f}\n\n"

    cust_info = tool_context.state.get("customer_info")
    if not cust_info:
        summary += (
            "To complete the checkout, please provide your first name, last name, "
            "street address, locality, region, postal code, and email address."
        )
    else:
        summary += "All details are set. You can now complete your purchase by running 'complete_checkout'."

    return summary


def update_customer_details(
    tool_context: ToolContext,
    first_name: str,
    last_name: str,
    street_address: str,
    address_locality: str,
    address_region: str,
    postal_code: str,
    email: str,
) -> str:
    """Add delivery address and email to the checkout session.

    Args:
        tool_context: The tool context containing session state.
        first_name: First name of the recipient.
        last_name: Last name of the recipient.
        street_address: The street address (e.g. 1600 Amphitheatre Pkwy).
        address_locality: The city or locality.
        address_region: The state or region.
        postal_code: The postal code.
        email: The customer's email address.
    """
    tool_context.state["customer_info"] = {
        "first_name": first_name,
        "last_name": last_name,
        "street_address": street_address,
        "address_locality": address_locality,
        "address_region": address_region,
        "postal_code": postal_code,
        "email": email,
    }

    cart = tool_context.state.get("cart", {})
    if not cart:
        return "Customer information saved successfully. Please add products to your checkout next."

    total = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())

    res = "Customer Details Updated:\n"
    res += f"- Name: {first_name} {last_name}\n"
    res += f"- Shipping: {street_address}, {address_locality}, {address_region} (Zip: {postal_code})\n"
    res += f"- Email: {email}\n\n"
    res += f"Order Total: ${total:.2f}\n"
    res += (
        "Everything is ready! Please run 'complete_checkout' to finish your purchase."
    )
    return res


def complete_checkout(tool_context: ToolContext) -> str:
    """Process the payment and complete the checkout session.

    Args:
        tool_context: The tool context containing session state.
    """
    cart = tool_context.state.get("cart", {})
    cust_info = tool_context.state.get("customer_info")

    if not cart:
        return "Cannot complete payment: Your cart is empty."
    if not cust_info:
        return "Cannot complete payment: Shipping details and email are required. Please provide them first."

    order_id = f"ORD-{random.randint(10000, 99999)}"
    total = sum(PRODUCTS[pid]["price"] * qty for pid, qty in cart.items())

    res = f"🎉 Payment Completed and Order Created successfully!\n"
    res += f"Order ID: {order_id}\n"
    res += f"Total Paid: ${total:.2f}\n"
    res += f"Receipt Sent To: {cust_info['email']}\n"
    res += f"Deliver To: {cust_info['first_name']} {cust_info['last_name']}\n"
    res += f"Address: {cust_info['street_address']}, {cust_info['address_locality']}, {cust_info['address_region']} (Zip: {cust_info['postal_code']})\n\n"
    res += "Thank you for shopping at the UCP Grocery Store!"

    tool_context.state["cart"] = {}
    tool_context.state["customer_info"] = None

    return res


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a helpful shopping assistant for the UCP Grocery Store. "
        "Your goal is to guide the user through their shopping journey:\n"
        "1. Help them search for products using 'search_shopping_catalog'.\n"
        "2. Add their selected items to checkout using 'add_to_checkout'.\n"
        "3. Ask the user for their delivery details (name, address, postal code, email) and save them using 'update_customer_details'.\n"
        "4. Finalize the order using 'complete_checkout' once details are filled."
    ),
    tools=[
        search_shopping_catalog,
        add_to_checkout,
        update_customer_details,
        complete_checkout,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)

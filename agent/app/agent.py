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
from google.genai import types

from app.store import RetailStore
from ucp_sdk.models.schemas.shopping.types.postal_address import PostalAddress
from ucp_sdk.models.schemas.shopping.types.buyer import Buyer
from ucp_sdk.models.schemas.ucp import ResponseCheckout as UcpMetadata
from google.adk.tools.tool_context import ToolContext

# 移植したストアロジックのインスタンス化
store = RetailStore()

def search_shopping_catalog(query: str) -> str:
    """Search the product catalog for products that match the given query.

    Args:
        query: The search term (e.g. cookies, strawberries, chips).
    """
    results = store.search_products(query)
    if not results.results:
        return results.content or f"No products found matching '{query}'."

    res = "Available Products in Stock:\n"
    for product in results.results:
        price_usd = float(product.offers.price) if product.offers else 0.0
        res += f"- [ID: {product.product_id}] {product.name} - ${price_usd:.2f}\n"
    return res

def add_to_checkout(tool_context: ToolContext, product_id: str, quantity: int = 1) -> str:
    """Add a product to the active checkout session in the store database.

    Args:
        tool_context: The tool context containing session state.
        product_id: The ID or SKU of the product to add (e.g., BISC-001).
        quantity: The quantity of the product to add.
    """
    checkout_id = tool_context.state.get("checkout_id")
    # UCPメタデータのダミーモックを用意
    dummy_metadata = UcpMetadata(
        version="2026-01-23",
        capabilities=[]
    )
    
    try:
        checkout = store.add_to_checkout(
            metadata=dummy_metadata,
            product_id=product_id,
            quantity=quantity,
            checkout_id=checkout_id
        )
        tool_context.state["checkout_id"] = checkout.id
        
        # カート合計額の算出 (セント単位からドルに変換)
        grand_total = 0.0
        for total in checkout.totals:
            if total.type == "total":
                grand_total = total.amount / 100.0
                break

        summary = f"Item added successfully. Checkout ID: {checkout.id}\nCurrent Cart Summary:\n"
        for item in checkout.line_items:
            summary += f"- {item.item.title} (x{item.quantity}) - ${item.item.price/100:.2f} each\n"
        summary += f"Total Amount: ${grand_total:.2f}\n"
        
        if not tool_context.state.get("customer_info"):
            summary += "\nTo complete the checkout, please provide your delivery details using 'update_customer_details'."
        return summary
    except Exception as e:
        return f"Error adding item to checkout: {e}"

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
    """Add delivery address and email to the active checkout session.

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
    checkout_id = tool_context.state.get("checkout_id")
    if not checkout_id:
        return "Error: No active checkout session. Please add products to your cart first."

    address = PostalAddress(
        street_address=street_address,
        address_locality=address_locality,
        address_region=address_region,
        postal_code=postal_code,
        country="US"
    )
    
    try:
        # 配送先住所をストアに追加
        checkout = store.add_delivery_address(checkout_id, address)
        # バイヤー情報を設定
        checkout.buyer = Buyer(email=email)
        
        # 顧客情報をセッションステートに保持
        tool_context.state["customer_info"] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email
        }
        
        # 送料と総支払額を算出
        grand_total = 0.0
        shipping_fee = 0.0
        for total in checkout.totals:
            if total.type == "total":
                grand_total = total.amount / 100.0
            elif total.type == "fulfillment":
                shipping_fee = total.amount / 100.0

        # 決済可能状態にするため、start_payment をコール
        store.start_payment(checkout_id)

        res = f"Customer details updated successfully.\n"
        res += f"- Recipient: {first_name} {last_name}\n"
        res += f"- Shipping Address: {street_address}, {address_locality}, {address_region} (Zip: {postal_code})\n"
        res += f"- Shipping Fee (Standard): ${shipping_fee:.2f}\n"
        res += f"- Grand Total: ${grand_total:.2f}\n"
        res += "Everything is ready! Please run 'complete_checkout' to finish your purchase."
        return res
    except Exception as e:
        return f"Error updating customer details: {e}"

def complete_checkout(tool_context: ToolContext) -> str:
    """Process the payment and complete the checkout session.

    Args:
        tool_context: The tool context containing session state.
    """
    checkout_id = tool_context.state.get("checkout_id")
    if not checkout_id:
        return "Error: No active checkout session."
        
    try:
        # 注文を確定
        checkout = store.place_order(checkout_id)
        order_id = checkout.order.id if checkout.order else "UNKNOWN"
        
        grand_total = 0.0
        for total in checkout.totals:
            if total.type == "total":
                grand_total = total.amount / 100.0
                break

        cust_info = tool_context.state.get("customer_info", {"first_name": "Valued", "last_name": "Customer", "email": ""})
        
        res = f"🎉 Order finalized successfully! (Integration Mode)\n"
        res += f"- Order ID: {order_id}\n"
        res += f"- Total Paid: ${grand_total:.2f}\n"
        res += f"- Receipt Sent To: {cust_info['email']}\n"
        res += f"- Deliver To: {cust_info['first_name']} {cust_info['last_name']}\n\n"
        res += "Thank you for shopping at the integrated UCP Grocery Store!"
        
        # ステートの初期化
        tool_context.state["checkout_id"] = None
        tool_context.state["customer_info"] = None
        return res
    except Exception as e:
        return f"Error placing order: {e}"

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are a helpful shopping assistant for the UCP Grocery Store. "
        "Your goal is to guide the user through their shopping journey using the store catalog and states:\n"
        "1. Help them search for products using 'search_shopping_catalog'.\n"
        "2. Add their selected items to checkout using 'add_to_checkout'.\n"
        "3. Ask the user for their delivery details (name, address, postal code, email) and save them using 'update_customer_details'.\n"
        "4. Finalize the order using 'complete_checkout' once details are filled."
    ),
    tools=[search_shopping_catalog, add_to_checkout, update_customer_details, complete_checkout],
)

app = App(
    root_agent=root_agent,
    name="app",
)

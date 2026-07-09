# ruff: noqa
import logging
from typing import Any

from google.adk import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from ucp_sdk.models.schemas.shopping.types.buyer import Buyer
from ucp_sdk.models.schemas.shopping.types.postal_address import PostalAddress

# 移植する business_agent モジュールから正しくインポート
from app.a2a_extensions.ucp_extension import UcpExtension
from app.constants import (
    ADK_EXTENSIONS_STATE_KEY,
    ADK_LATEST_TOOL_RESULT,
    ADK_PAYMENT_STATE,
    ADK_UCP_METADATA_STATE,
    ADK_USER_CHECKOUT_ID,
    UCP_CHECKOUT_KEY,
    UCP_PAYMENT_DATA_KEY,
    UCP_RISK_SIGNALS_KEY,
)
from app.payment_processor import MockPaymentProcessor
from app.store import RetailStore

store = RetailStore()
mpp = MockPaymentProcessor()


def _create_error_response(message: str) -> dict:
    return {"message": message, "status": "error"}


def _get_current_checkout_id(tool_context: ToolContext) -> str | None:
    return tool_context.state.get(ADK_USER_CHECKOUT_ID)


def search_shopping_catalog(tool_context: ToolContext, query: str) -> dict:
    """Search the product catalog for products that match the given query.

    Args:
        tool_context: The tool context for the current request.
        query: Query for performing product search.
    """
    try:
        product_results = store.search_products(query)
        return {"a2a.product_results": product_results.model_dump(mode="json")}
    except Exception:
        logging.exception("There was an error searching the product catalog.")
        return _create_error_response(
            "Sorry, there was an error searching the product catalog, "
            "please try again later."
        )


def add_to_checkout(
    tool_context: ToolContext, product_id: str, quantity: int = 1
) -> dict:
    """Add a product to the checkout session.

    Args:
        tool_context: The tool context for the current request.
        product_id: Product ID or SKU.
        quantity: Quantity; defaults to 1 if not specified.
    """
    checkout_id = tool_context.state.get(ADK_USER_CHECKOUT_ID)
    ucp_metadata_dict = tool_context.state.get(ADK_UCP_METADATA_STATE)

    from ucp_sdk.models.schemas.ucp import ResponseCheckout as UcpMetadata
    if not ucp_metadata_dict:
        ucp_metadata = UcpMetadata(version="2026-01-23", capabilities=[])
        tool_context.state[ADK_UCP_METADATA_STATE] = ucp_metadata.model_dump(mode="json")
    else:
        ucp_metadata = UcpMetadata.model_validate(ucp_metadata_dict)

    try:
        checkout = store.add_to_checkout(
            ucp_metadata, product_id, quantity, checkout_id
        )
        if not checkout_id:
            tool_context.state[ADK_USER_CHECKOUT_ID] = checkout.id

        return {
            UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception(
            "There was an error adding item to checkout, please retry later."
        )
        return _create_error_response(
            "There was an error adding item to checkout, please retry later."
        )


def remove_from_checkout(tool_context: ToolContext, product_id: str) -> dict:
    """Remove a product from the checkout session.

    Args:
        tool_context: The tool context for the current request.
        product_id: Product ID or SKU.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    try:
        return {
            UCP_CHECKOUT_KEY: store.remove_from_checkout(
                checkout_id, product_id
            ).model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception(
            "There was an error removing item from checkout, please retry later."
        )
        return _create_error_response(
            "There was an error removing item from checkout, please retry later."
        )


def update_checkout(tool_context: ToolContext, product_id: str, quantity: int) -> dict:
    """Update the quantity of a product in the checkout session.

    Args:
        tool_context: The tool context for the current request.
        product_id: Product ID or SKU.
        quantity: New quantity for the product.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    try:
        return {
            UCP_CHECKOUT_KEY: store.update_checkout(
                checkout_id, product_id, quantity
             ).model_dump(mode="json"),
            "status": "success",
        }
    except ValueError:
        logging.exception(
            "There was an error updating item in the cart, please retry later."
        )
        return _create_error_response(
            "There was an error updating item in the cart, please retry later."
        )


def get_checkout(tool_context: ToolContext) -> dict:
    """Retrieve a Checkout Session.

    Args:
        tool_context: The tool context for the current request.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    checkout = store.get_checkout(checkout_id)
    if checkout is None:
        return _create_error_response("Checkout not found with the given ID.")

    return {
        UCP_CHECKOUT_KEY: checkout.model_dump(mode="json"),
        "status": "success",
    }


def update_customer_details(
    tool_context: ToolContext,
    first_name: str,
    last_name: str,
    street_address: str,
    address_locality: str,
    address_region: str,
    postal_code: str,
    address_country: str | None = None,
    extended_address: str | None = None,
    email: str | None = None,
) -> dict:
    """Add delivery address to the checkout.

    Args:
        tool_context: The tool context for the current request.
        first_name: First name of the recipient.
        last_name: Last name of the recipient.
        street_address: The street address.
        address_locality: The locality.
        address_region: The region.
        postal_code: The postal code.
        address_country: The country.
        extended_address: The extended address.
        email: The email address.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    if not address_country:
        address_country = "US"

    address = PostalAddress(
        street_address=street_address,
        extended_address=extended_address,
        address_locality=address_locality,
        address_region=address_region,
        address_country=address_country,
        postal_code=postal_code,
        first_name=first_name,
        last_name=last_name,
    )

    checkout = store.add_delivery_address(checkout_id, address)
    if email:
        checkout.buyer = Buyer(email=email)
        store._checkouts[checkout_id] = checkout
        store._save_checkouts()

    return start_payment(tool_context)


def start_payment(tool_context: ToolContext) -> dict:
    """Ask for required information to proceed with the payment.

    Args:
        tool_context: The tool context for the current request.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    result = store.start_payment(checkout_id)
    if isinstance(result, str):
        return {"message": result, "status": "requires_more_info"}
    else:
        tool_context.actions.skip_summarization = True
        return {
            UCP_CHECKOUT_KEY: result.model_dump(mode="json"),
            "status": "success",
        }


async def complete_checkout(tool_context: ToolContext) -> dict:
    """Process the payment data to complete checkout.

    Args:
        tool_context: The tool context for the current request.
    """
    checkout_id = _get_current_checkout_id(tool_context)
    if not checkout_id:
        return _create_error_response("A Checkout has not yet been created.")

    checkout = store.get_checkout(checkout_id)
    if checkout is None:
        return _create_error_response("Checkout not found for the current session.")

    payment_data: dict[str, Any] = tool_context.state.get(ADK_PAYMENT_STATE)
    if payment_data is None:
        # Create mock payment data for CLI testing/fallback to ensure checkout completes
        from ucp_sdk.models.schemas.shopping.types.payment_instrument import PaymentInstrument
        from ucp_sdk.models.schemas.shopping.types.card_payment_instrument import CardPaymentInstrument

        mock_instrument = PaymentInstrument(
            root=CardPaymentInstrument(
                id="mock_card_id",
                handler_id="example_payment_provider",
                type="card",
                brand="visa",
                last_digits="1111",
                expiry_month=12,
                expiry_year=2030,
            )
        )
        payment_data = {
            UCP_PAYMENT_DATA_KEY: mock_instrument,
            UCP_RISK_SIGNALS_KEY: {},
        }

    try:
        from a2a.types import TaskState
        from a2a.utils import get_message_text

        task = mpp.process_payment(
            payment_data[UCP_PAYMENT_DATA_KEY],
            payment_data[UCP_RISK_SIGNALS_KEY],
        )

        if task is None:
            return _create_error_response("Failed to receive a valid response from MPP")

        if task.status is not None and task.status.state == TaskState.completed:
            payment_instrument = payment_data.get(UCP_PAYMENT_DATA_KEY)
            checkout.payment.selected_instrument_id = payment_instrument.root.id
            checkout.payment.instruments = [payment_instrument]

            response = store.place_order(checkout_id)
            tool_context.state[ADK_USER_CHECKOUT_ID] = None
            return {
                UCP_CHECKOUT_KEY: response.model_dump(mode="json"),
                "status": "success",
            }
        else:
            return _create_error_response(get_message_text(task.status.message))
    except Exception:
        logging.exception("There was an error completing the checkout.")
        return _create_error_response(
            "Sorry, there was an error completing the checkout, please try again."
        )


def after_tool_modifier(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: dict,
) -> dict | None:
    extensions = tool_context.state.get(ADK_EXTENSIONS_STATE_KEY, [])
    ucp_response_keys = [UCP_CHECKOUT_KEY, "a2a.product_results"]
    if UcpExtension.URI in extensions and any(
        key in tool_response for key in ucp_response_keys
    ):
        tool_context.state[ADK_LATEST_TOOL_RESULT] = tool_response
    return None


def modify_output_after_agent(
    callback_context: CallbackContext,
) -> types.Content | None:
    latest_result = callback_context.state.get(ADK_LATEST_TOOL_RESULT)
    if latest_result:
        return types.Content(
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        response={"result": latest_result}
                    )
                )
            ],
            role="model",
        )
    return None


root_agent = Agent(
    name="shopper_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description="Agent to help with shopping",
    instruction=(
        "You are a helpful agent who can help user with shopping actions such "
        "as searching the catalog, add to checkout session, complete checkout "
        "and handle order placed event. Given the user ask, plan ahead and "
        "invoke the tools available to complete the user's ask. Always make "
        "sure you have completed all aspects of the user's ask. If the user "
        "says add to my list or remove from the list, add or remove from the "
        "cart, add the product or remove the product from the checkout "
        "session. If the user asks to add any items to the checkout session, "
        "search for the products and then add the matching products to "
        "checkout session. If the user asks to replace products, "
        "use remove_from_checkout and add_to_checkout tools to replace the "
        "products to match the user request. "
        "Crucial Rule: When calling 'search_shopping_catalog', always translate "
        "the search query into English (e.g., translate 'クッキー' to 'cookies', "
        "'イチゴ' to 'strawberries') because the product catalog database is written in English."
    ),
    tools=[
        search_shopping_catalog,
        add_to_checkout,
        remove_from_checkout,
        update_checkout,
        get_checkout,
        start_payment,
        update_customer_details,
        complete_checkout,
    ],
    after_tool_callback=after_tool_modifier,
    after_agent_callback=modify_output_after_agent,
)

app = App(
    root_agent=root_agent,
    name="app",
)

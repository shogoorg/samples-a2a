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

"""Attach A2A (Agent2Agent) endpoints to the FastAPI app.

func:`attach_a2a_routes` registers the dynamic
agent-card endpoint and the JSON-RPC endpoint so the same app serves A2A
alongside the adk_api routes, reachable by A2A clients and Gemini Enterprise A2A
registration.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import TaskStore
from a2a.types import AgentCapabilities, AgentExtension
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder

if TYPE_CHECKING:
    from fastapi import FastAPI
    from google.adk.agents import BaseAgent
    from google.adk.runners import Runner

# URI advertised on the agent card describing the executor extension shipped
# by ADK. Kept as a module-level constant so callers can override or extend
# the capabilities list when needed.
_ADK_AGENT_EXECUTOR_EXTENSION_URI = (
    "https://google.github.io/adk-docs/a2a/a2a-extension/"
)


def _default_capabilities() -> AgentCapabilities:
    """Returns the default A2A capabilities used by scaffolded projects."""
    return AgentCapabilities(
        streaming=True,
        extensions=[
            AgentExtension(
                uri=_ADK_AGENT_EXECUTOR_EXTENSION_URI,
                description=("Ability to use the new agent executor implementation"),
            ),
        ],
    )


async def attach_a2a_routes(
    app: FastAPI,
    *,
    agent: BaseAgent,
    runner: Runner,
    task_store: TaskStore,
    rpc_path: str,
    capabilities: AgentCapabilities | None = None,
    agent_version: str | None = None,
    app_url: str | None = None,
) -> None:
    """Register A2A routes (JSON-RPC + agent-card endpoints) under ``rpc_path``.

    Builds a dynamic agent card from ``agent`` and mounts the routes on ``app``.
    The ``runner`` should share the session/artifact/memory services with the
    standard ADK path. ``capabilities``, ``agent_version``, and ``app_url``
    override their defaults (streaming + ADK extension, ``AGENT_VERSION``,
    ``APP_URL``). Call once per app — typically in a FastAPI ``lifespan``, since
    the card is built asynchronously; repeated calls register duplicate routes.
    """
    resolved_app_url = app_url or os.getenv("APP_URL", "http://0.0.0.0:8000")
    resolved_agent_version = agent_version or os.getenv("AGENT_VERSION", "0.1.0")
    resolved_capabilities = capabilities or _default_capabilities()

    agent_card = await AgentCardBuilder(
        agent=agent,
        capabilities=resolved_capabilities,
        rpc_url=f"{resolved_app_url}{rpc_path}",
        agent_version=resolved_agent_version,
    ).build()

    from google.adk.a2a.executor.config import A2aAgentExecutorConfig
    from google.adk.a2a.converters.part_converter import convert_genai_part_to_a2a_part
    from google.adk.a2a.converters.request_converter import convert_a2a_request_to_agent_run_request
    from a2a.server.agent_execution import RequestContext
    from google.adk.a2a.converters.part_converter import A2APartToGenAIPartConverter
    from google.adk.a2a.converters.request_converter import AgentRunRequest
    from a2a import types as a2a_types
    from google.genai import types as genai_types
    import re
    import json
    import logging

    logger = logging.getLogger("google_adk.a2a.custom")

    def custom_genai_part_to_a2a_part(part: genai_types.Part) -> a2a_types.Part | None:
        if part.function_response and part.function_response.response:
            result = part.function_response.response.get("result")
            if isinstance(result, dict):
                return a2a_types.Part(
                    root=a2a_types.DataPart(
                        data=result,
                        metadata={
                            "type": "function_response"
                        }
                    )
                )
        return convert_genai_part_to_a2a_part(part)

    def custom_request_converter(
        request: RequestContext,
        part_converter: A2APartToGenAIPartConverter,
    ) -> AgentRunRequest:
        base_request = convert_a2a_request_to_agent_run_request(request, part_converter)

        from app.ucp_profile_resolver import ProfileResolver
        from app.constants import (
            ADK_EXTENSIONS_STATE_KEY,
            ADK_LATEST_TOOL_RESULT,
            ADK_PAYMENT_STATE,
            ADK_UCP_METADATA_STATE,
            UCP_AGENT_HEADER,
            UCP_PAYMENT_DATA_KEY,
            UCP_RISK_SIGNALS_KEY,
        )
        from ucp_sdk.models.schemas.shopping.types.payment_instrument import PaymentInstrument

        # 1. Resolve UCP metadata from headers
        ucp_metadata = None
        try:
            headers = request.call_context.state.get("headers", {}) if request.call_context else {}
            ucp_agent_header_key = next(
                (key for key in headers if key.lower() == UCP_AGENT_HEADER.lower()),
                None,
            )
            if ucp_agent_header_key:
                ucp_agent_header_value = headers[ucp_agent_header_key]
                match = re.search(r'profile="([^"]*)"', ucp_agent_header_value)
                if match and match.group(1):
                    client_profile_url = match.group(1)
                    resolver = ProfileResolver()
                    client_profile_metadata = resolver.resolve_profile(client_profile_url)
                    ucp_metadata = resolver.get_ucp_metadata(client_profile_metadata)
        except Exception as e:
            logger.warning("Failed to resolve UCP metadata: %s", e)

        # 2. Extract payment data from request parts
        payment_payload = {}
        query_addons = []
        payment_keys = [UCP_PAYMENT_DATA_KEY, UCP_RISK_SIGNALS_KEY]

        if request.message and request.message.parts:
            for a2a_part in request.message.parts:
                if isinstance(a2a_part.root, a2a_types.DataPart):
                    data_part = dict(a2a_part.root.data)
                    found_any = False
                    for key in payment_keys:
                        if key in data_part:
                            found_any = True
                            value = data_part.pop(key)
                            if key == UCP_PAYMENT_DATA_KEY:
                                if isinstance(value, dict) and "display" in value:
                                    value.update(value.pop("display"))
                                try:
                                    payment_payload[key] = PaymentInstrument.model_validate(value)
                                except Exception as val_err:
                                    logger.warning("Failed to validate payment instrument: %s", val_err)
                                    payment_payload[key] = value
                            else:
                                payment_payload[key] = value
                    if found_any and data_part:
                        query_addons.append(json.dumps(data_part))

        if query_addons and base_request.new_message and base_request.new_message.parts:
            for part in base_request.new_message.parts:
                if part.text:
                    part.text += "\n" + "\n".join(query_addons)
                    break

        # 3. Build state_delta
        base_request.state_delta = {
            ADK_UCP_METADATA_STATE: ucp_metadata.model_dump(mode="json") if ucp_metadata else None,
            ADK_EXTENSIONS_STATE_KEY: request.requested_extensions,
            ADK_PAYMENT_STATE: payment_payload or None,
            ADK_LATEST_TOOL_RESULT: None,
        }

        return base_request

    config = A2aAgentExecutorConfig(
        gen_ai_part_converter=custom_genai_part_to_a2a_part,
        request_converter=custom_request_converter,
    )

    request_handler = DefaultRequestHandler(
        agent_executor=A2aAgentExecutor(runner=runner, config=config),
        task_store=task_store,
    )

    a2a_app = A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
    a2a_app.add_routes_to_app(
        app,
        agent_card_url=f"{rpc_path}{AGENT_CARD_WELL_KNOWN_PATH}",
        rpc_url=rpc_path,
        extended_agent_card_url=f"{rpc_path}{EXTENDED_AGENT_CARD_PATH}",
    )

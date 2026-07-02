# Copyright 2026 UCP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""UCP."""

import asyncio
import functools
import json
import logging
import os

from pathlib import Path
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard
import click
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
import uvicorn

from .agent import root_agent as business_agent
from .agent_executor import ADKAgentExecutor

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def make_sync(func):
    """Wrap an async function to run synchronously.

    Args:
        func: The async function to wrap.





    Returns:
        The wrapped synchronous function.


    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10999)
@make_sync
async def run(host, port):
    """Run the A2A business agent server.

    Args:
        host: The host to bind to.
        port: The port to listen on.

    """
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY must be set")
        exit(1)

    base_path = Path(__file__).parent
    card_path = base_path / "data" / "agent_card.json"
    with card_path.open(encoding="utf-8") as f:
        data = json.load(f)
    agent_card = AgentCard.model_validate(data)

    app_url = os.getenv("APP_URL")
    if app_url:
        agent_card.url = app_url

    task_store = InMemoryTaskStore()

    request_handler = DefaultRequestHandler(
        agent_executor=ADKAgentExecutor(
            agent=business_agent,
            extensions=agent_card.capabilities.extensions or [],
        ),
        task_store=task_store,
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    
    # Get base routes from A2AStarletteApplication
    base_routes = a2a_app.routes()
    
    # We will build a unified route list containing:
    # 1. Base routes (e.g. /, /.well-known/agent-card.json)
    # 2. Prefixed routes (e.g. /a2a/src, /a2a/business-agent/...) to support agents-cli remote routing
    routes = []
    
    for r in base_routes:
        routes.append(r)
        if r.path == "/":
            # For JSON-RPC POST endpoints:
            routes.append(Route("/a2a/business-agent", r.endpoint, methods=r.methods))
            routes.append(Route("/a2a/business-agent/", r.endpoint, methods=r.methods))
            routes.append(Route("/a2a/src", r.endpoint, methods=r.methods))
            routes.append(Route("/a2a/src/", r.endpoint, methods=r.methods))
        else:
            routes.append(Route(f"/a2a/business-agent{r.path}", r.endpoint, methods=r.methods))
            routes.append(Route(f"/a2a/src{r.path}", r.endpoint, methods=r.methods))

    # Add extra static assets and config endpoints
    routes.extend(
        [
            Route(
                "/.well-known/ucp",
                lambda _: FileResponse(base_path / "data" / "ucp.json"),
            ),
            Route(
                "/a2a/business-agent/.well-known/ucp",
                lambda _: FileResponse(base_path / "data" / "ucp.json"),
            ),
            Route(
                "/a2a/src/.well-known/ucp",
                lambda _: FileResponse(base_path / "data" / "ucp.json"),
            ),
            Route(
                "/agent-card.json",
                lambda _: FileResponse(card_path),
            ),
            Route(
                "/a2a/business-agent/agent-card.json",
                lambda _: FileResponse(card_path),
            ),
            Route(
                "/a2a/src/agent-card.json",
                lambda _: FileResponse(card_path),
            ),
            Mount(
                "/images",
                app=StaticFiles(directory=str(base_path / "data" / "images")),
                name="images",
            ),
            Mount(
                "/a2a/business-agent/images",
                app=StaticFiles(directory=str(base_path / "data" / "images")),
                name="images_ba",
            ),
            Mount(
                "/a2a/src/images",
                app=StaticFiles(directory=str(base_path / "data" / "images")),
                name="images_src",
            ),
        ]
    )
    app = Starlette(routes=routes)

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    run()

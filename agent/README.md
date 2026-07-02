# agent

Simple ReAct agent
Agent generated with `agents-cli` version `1.0.0`

## Project Structure

```
agent/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── fast_api_app.py        # FastAPI Backend server
│   └── app_utils/             # App utilities and helpers
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Antigravity CLI](https://antigravity.google/) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Start the interactive development playground:

```bash
agents-cli playground
```

Or test the agent directly from your terminal using commands to run through the entire shopping flow:

```bash
# 1. Search products (calls 'search_shopping_catalog')
agents-cli run "Show me cookies in stock"

# 2. Add product to checkout (calls 'add_to_checkout')
agents-cli run "Add BISC-001 to my checkout"

# 3. Register shipping address and details (calls 'update_customer_details')
agents-cli run "Set my shipping info: name is Shogo Suzuki, address is 1600 Amphitheatre Pkwy, Mountain View, CA, postal code is 94043, email is shogo@example.com"

# 4. Finalize payment and place order (calls 'complete_checkout')
agents-cli run "Complete my checkout now"
```

Example commands in Japanese (to run the entire shopping flow using Japanese prompts):

```bash
# 1. 商品の検索テスト
agents-cli run "在庫があるクッキーを見せてください"

# 2. カート追加テスト
agents-cli run "私のチェックアウトに BISC-001 を追加してください"

# 3. 配送先情報の登録テスト
agents-cli run "私の配送情報を設定してください：名前は Shogo Suzuki、住所は 1600 Amphitheatre Pkwy, Mountain View, CA、郵便番号は 94043、メールアドレスは shogo@example.com です"

# 4. 決済完了テスト
agents-cli run "今すぐ私のチェックアウトを完了してください"
```

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Cloud Run                                                                   || [A2A Inspector](https://github.com/a2aproject/a2a-inspector) | Launch A2A Protocol Inspector                                                        |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

### Dev UI & A2A Endpoints (After Deployment)

Once deployed and allowed for public access (`gcloud run services add-iam-policy-binding`):
* **Playground (Dev UI)**: Accessible at `https://<YOUR_SERVICE_URL>/dev-ui/`
* **A2A JSON-RPC Endpoint**: `https://<YOUR_SERVICE_URL>/a2a/app`
* **Agent Card**: `https://<YOUR_SERVICE_URL>/a2a/app/.well-known/agent-card.json`

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.

## A2A Inspector

This agent supports the [A2A Protocol](https://a2a-protocol.org/). Use the [A2A Inspector](https://github.com/a2aproject/a2a-inspector) to test interoperability.
See the [A2A Inspector docs](https://github.com/a2aproject/a2a-inspector) for details.

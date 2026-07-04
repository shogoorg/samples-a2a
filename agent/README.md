# Cymbal Retail Agent with UCP Extension and A2A

This Project enables running the Cymbal Retail Agent with UCP Extension and A2A using agents-cli.

agents-cli <https://github.com/Universal-Commerce-Protocol/samples/tree/main/rest/python/server> is a CLI and skill for building agents on the Gemini Enterprise Agent Platform.

The Cymbal Retail Agent with UCP Extension and A2A <https://github.com/Universal-Commerce-Protocol/samples/tree/main/a2a> demonstrates how to build an AI-powered shopping assistant using Universal Commerce Protocol (UCP) - an open standard that enables interoperability between commerce platforms, merchants, and payment providers.

## Project Structure

```
agent/
├── app/                       # Core ADK agent code
│   ├── agent.py               # Main agent logic (customized Grocery Store assistant)
│   ├── fast_api_app.py        # FastAPI backend server
│   ├── store.py               # Integrated Retail Store state management
│   ├── payment_processor.py   # Payment processor logic
│   ├── app_utils/             # App utilities and helpers
│   └── data/                  # Store data (products.json, ucp.json)
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Antigravity CLI](https://antigravity.google/) for AI-assisted development — project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) — [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI — Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services — [Install](https://cloud.google.com/sdk/docs/install)

## Quick Start

This agent simulates a full customer shopping checkout flow referencing the **UCP (Universal Commerce Protocol)** and its A2A implementation.

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
agents-cli run "Set my shipping info: name is John Doe, address is 1600 Amphitheatre Pkwy, Mountain View, CA, postal code is 94043, email is john.doe@example.com"

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
agents-cli run "私の配送情報を設定してください：名前は John Doe、住所は 1600 Amphitheatre Pkwy, Mountain View, CA、郵便番号は 94043、メールアドレスは john.doe@example.com です"

# 4. 決済完了テスト
agents-cli run "今すぐ私のチェックアウトを完了してください"
```

### Cloud Run Deployment
If deploying the merchant server on Google Cloud:
- **Server URL**: `https://<YOUR_UCP_SERVER_URL>`
- **Discovery URL**: `https://<YOUR_UCP_SERVER_URL>/.well-known/ucp`

## Commands

| Command | Description |
| :--- | :--- |
| `agents-cli install` | Install agent dependencies using uv |
| `agents-cli playground` | Launch local development playground |
| `agents-cli lint` | Run code quality checks |
| `agents-cli eval` | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests |

## 🛠️ Project Management

| Command | What It Does |
| :--- | :--- |
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | Set up the entire CI/CD pipeline and infrastructure with a single command |
| `agents-cli scaffold upgrade` | Automatically upgrade to the latest version while preserving customizations |

---

## Development

Edit your agent logic in `agent/app/agent.py` and test it with `agents-cli playground` — it automatically reloads on save.

## Deployment

Deploy the ADK Agent to Cloud Run and expose it publicly:

```bash
# 1. Deploy the agent
agents-cli deploy --project=<YOUR_PROJECT_ID> --no-confirm-project

# 2. Expose the service to allow public access
gcloud run services add-iam-policy-binding samples-a2a \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --region=us-east1 \
  --project=<YOUR_PROJECT_ID>
```

## Observability

Built-in telemetry automatically exports data to Cloud Trace, BigQuery, and Cloud Logging.

## A2A Inspector

This agent supports the [A2A Protocol](https://a2a-protocol.org/). Use the [A2A Inspector](https://github.com/a2aproject/a2a-inspector) to test interoperability.
See the [A2A Inspector docs](https://github.com/a2aproject/a2a-inspector) for details.

## Changelog

### 2026-07-04
- Updated CI/CD runner configuration in `agents-cli-manifest.yaml` to `google_cloud_build`.
- Excluded dynamic runtime artifacts (`agent/app/data/checkouts_db.json`, `agent/artifacts/`) from Git via `.gitignore`.

# Telegram and Zoho workspace connections

Staging enables these two providers individually through
`ENABLED_INTEGRATION_PROVIDERS=["telegram","zoho"]`. Billing and the other
integration categories remain disabled. Production retains its default empty
provider list. This configuration enables connection setup; actual provider
acceptance still requires authorized accounts and real message/lead tests.

## Telegram

In **Integrations → Telegram**, select a Telegram agent, choose a distinct
connection name and enter that bot's BotFather token. The server checks the bot
identity, encrypts the token and registers a webhook with a secret header.
Choose **Connect another bot** to add further bots. Select a saved bot to check,
disconnect or update its token. Each bot has one webhook; disconnect a bot from
another application before moving it here. Bots assigned to another workspace
cannot be silently reassigned through this flow.

Tokens and webhook secrets are not returned to the browser. On PostgreSQL,
registration is serialized by bot identity across tenants. Retrying a saved bot
preserves its webhook secret. Provider outages and invalid credentials produce
actionable errors and do not report a successful connection.

## Zoho

In **Integrations → Zoho CRM**, enter a connection name, select the correct Zoho
data center, and enter your OAuth application's client ID and client secret.
Register the exact **Authorized redirect URL** shown in the dialog in your Zoho
OAuth application. Sign in and approve access in the Zoho authorization window.
TalkToBot does not request your Zoho account password.

Use **Connect another account** and a distinct name for each additional account.
The account selector keeps connection checks, credential updates, authorization,
mapping and disconnect actions scoped to the selected connection. Starting a
second named connection does not replace the first connection's credentials.
Credentials are encrypted; secret fields clear after a successful OAuth start.
Expired or rejected authorization can be restarted on the saved connection.

## AWS callback access and delivery

The existing staging ALB exposes only the Zoho OAuth callback and channel
webhook paths publicly. Ordinary website, application and API routes retain
operator/NAT source-IP conditions. `prepare-staging-callback-access.py` verifies
the live HTTPS listener restrictions before inbound access can be widened for
callbacks. Telegram callbacks require the webhook secret, and Zoho callbacks
require valid single-use OAuth state with a current workspace authorization.

CRM routing, delivery, reconciliation and health monitoring plus channel event
processing and health monitoring run on the existing staging nodes. Provider
checks apply to background execution, token refresh and outbound HTTP requests.
Automatic retries retain existing delivery idempotency and read-back checks;
ambiguous provider acknowledgement is not blindly resent.

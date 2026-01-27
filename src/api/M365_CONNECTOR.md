# M365 Connector API Documentation

## 📋 Overview

The M365 Connector provides a RESTful API for integrating Microsoft 365 email functionality into your application. It enables:

- **OAuth2 Authentication** with Microsoft accounts
- **Email Reading** from user mailboxes
- **Webhook Subscriptions** for real-time email notifications
- **Auto-Draft Replies** using AI/LLM for incoming emails
- **Multi-User Support** where each user can connect their own M365 account

## 🏗️ Architecture

```
Your Frontend → API Endpoints → M365 Service → Storage (data.json)
                                      ↓
                                OutlookConnector → Microsoft Graph API
                                      ↓
                                EmailReplyGenerator (LLM)
```

## 🔗 Base URL

```
http://localhost:8000/api/m365
```

---

## 📚 Endpoints

### 1. Health Check

**Endpoint:** `GET /api/m365/health`

**Description:** Check if the M365 connector service is running and view statistics.

**Request:**
```bash
curl http://localhost:8000/api/m365/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "m365-connector",
  "active_users": 2,
  "active_subscriptions": 1
}
```

**Use Case:** Monitor service health and see how many users are connected.

---

## 🔐 Authentication Endpoints

### 2. Initiate Authentication

**Endpoint:** `GET /api/m365/auth/authenticate`

**Description:** Start the OAuth2 authentication flow to connect a user's Microsoft 365 account.

**Request:**
```bash
curl http://localhost:8000/api/m365/auth/authenticate
```

**Response:**
```json
{
  "status": "success",
  "auth_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?...",
  "message": "Please complete authentication in the opened browser tab",
  "state": "abc123def456"
}
```

**Flow:**
1. Call this endpoint to initiate the authentication flow (in frontend it is typically the "Connect Outlook" button)
2. Redirect user to the `auth_url`
3. User signs in with their Microsoft account
4. Microsoft redirects back to your callback URL

**Use Case:** When a user clicks "Connect Outlook" in your app.

---

### 3. Authentication Callback

**Endpoint:** `GET /api/m365/auth/callback`

**Description:** Handles the OAuth2 callback from Microsoft after user authentication.

**Query Parameters:**
- `code` (string, required): Authorization code from Microsoft
- `state` (string, required): State parameter for CSRF protection

**Request:**
```
GET http://localhost:8000/api/m365/auth/callback?code=xxx&state=yyy
```

**Response:**
```json
{
  "status": "success",
  "message": "Authentication successful!",
  "user": {
    "user_id": "abc123def456",
    "name": "John Doe",
    "email": "john@company.com"
  },
  "next_steps": "Create a subscription using POST /api/m365/mail/subscriptions"
}
```

**Use Case:** This is automatically called by Microsoft after user signs in. The user_id is then stored and used for all future requests.

**⚠️ Important:** This callback URL must match the redirect URI configured in Azure AD app registration.

**TODO in frontend:** automatically close the browser tab after successful authentication.

---

### 4. Refresh Access Token

**Endpoint:** `POST /api/m365/auth/refresh-token`

**Description:** Refresh an expired access token for a user. By default, tokens expire after 1 hour.

**Request Body:**
```json
{
  "user_id": "abc123def456"
}
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/m365/auth/refresh-token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "abc123def456"}'
```

**Response:**
```json
{
  "status": "success",
  "message": "Token refreshed successfully",
  "user_id": "abc123def456",
  "expires_in": 3600
}
```

**Use Case:** When you get a 401 Unauthorized error, refresh the token before retrying. Tokens typically expire after 1 hour.

**Note:** Token refresh happens automatically on most operations, so it rarely needs to be called manually.

---

### 5. List Authenticated Users

**Endpoint:** `GET /api/m365/auth/users`

**Description:** Get a list of all users who have connected their M365 accounts.

**Request:**
```bash
curl http://localhost:8000/api/m365/auth/users
```

**Response:**
```json
{
  "status": "success",
  "count": 2,
  "users": [
    {
      "user_id": "abc123def456",
      "name": "John Doe",
      "email": "john@company.com",
      "has_token": true,
      "token_expires_at": "2024-11-07T14:30:00Z"
    },
    {
      "user_id": "xyz789ghi012",
      "name": "Jane Smith",
      "email": "jane@company.com",
      "has_token": true,
      "token_expires_at": "2024-11-07T15:00:00Z"
    }
  ]
}
```

**Use Case:** Admin dashboard/settings page to see all connected M365 accounts.

---

### 6. Clear All Users (Testing)

**Endpoint:** `POST /api/m365/auth/users/clear`

**Description:** Remove all authenticated users and their tokens. **For testing only!**

**Request:**
```bash
curl -X POST http://localhost:8000/api/m365/auth/users/clear
```

**Response:**
```json
{
  "status": "success",
  "message": "Cleared 2 user tokens"
}
```

**Use Case:** Reset local test environment.

**⚠️ Warning:** This deletes all user data. Do not use in production!

---

## 📧 Email Endpoints

### 7. Get Emails

**Endpoint:** `POST /api/m365/mail/emails`

**Description:** Retrieve emails from a user's mailbox.

**Request Body:**
```json
{
  "user_id": "abc123def456",
  "folder": "inbox",
  "limit": 10
}
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/m365/mail/emails \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "abc123def456",
    "folder": "inbox",
    "limit": 10
  }'
```

**Response:**
```json
{
  "status": "success",
  "count": 10,
  "emails": [
    {
      "id": "AAMkAD...",
      "subject": "Meeting tomorrow",
      "from": "colleague@company.com",
      "from_name": "Alice Johnson",
      "received_datetime": "2024-11-07T10:30:00Z",
      "is_read": false,
      "body_preview": "Hi, just confirming our meeting..."
    }
    // ... more emails
  ]
}
```

**Parameters:**
- `user_id` (string, required): The M365 user ID from authentication
- `folder` (string, optional): Folder name - default: "inbox"
- `limit` (integer, optional): Number of emails to retrieve - default: 10

**Use Case:** Display user's emails in app, check for unread messages, etc.

---

## 🔔 Subscription Endpoints (Webhooks)

### 8. Create Subscription

**Endpoint:** `POST /api/m365/mail/subscriptions`

**Description:** Create a webhook subscription to receive real-time notifications when new emails arrive.

**Request Body:**
```json
{
  "user_id": "abc123def456",
  "resource": "me/mailFolders('Inbox')/messages"
}
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/m365/mail/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "abc123def456",
    "resource": "me/mailFolders('\''Inbox'\'')/messages"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Subscription created successfully",
  "subscription": {
    "id": "subscription-xyz-789",
    "user_id": "abc123def456",
    "resource": "me/mailFolders('Inbox')/messages",
    "expires_at": "2024-11-10T12:00:00Z",
    "notification_url": "https://your-domain.com/api/m365/mail/webhook"
  }
}
```

**Parameters:**
- `user_id` (string, required): The M365 user ID
- `resource` (string, optional): Resource to monitor - default: `me/mailFolders('Inbox')/messages`

**Other Resource Options:**
- `me/mailFolders('Inbox')/messages` - Inbox only
- `me/messages` - All mail folders
- `me/mailFolders('Sent Items')/messages` - Sent items

**Use Case:** Enable auto-draft replies when new emails arrive in user's inbox. In frontend, it is typically the "Enable Auto-Draft" toggle button.

**⚠️ Requirements:**
1. Webhook URL must be **publicly accessible** (use ngrok for local testing)
2. Must respond with `200 OK` to Microsoft's validation request
3. Subscriptions expire after ~3 days and need renewal

---

### 9. List Subscriptions

**Endpoint:** `GET /api/m365/mail/subscriptions`

**Description:** Get all active webhook subscriptions.

**Request:**
```bash
curl http://localhost:8000/api/m365/mail/subscriptions
```

**Response:**
```json
{
  "status": "success",
  "count": 2,
  "subscriptions": [
    {
      "id": "subscription-xyz-789",
      "user_id": "abc123def456",
      "resource": "me/mailFolders('Inbox')/messages",
      "notification_url": "https://your-domain.com/api/m365/mail/webhook",
      "expires_at": "2024-11-10T12:00:00Z",
      "created_at": "2024-11-07T12:00:00Z"
    }
    // ... more subscriptions
  ]
}
```

**Use Case:** Check which users have active auto-draft subscriptions, monitor expiration dates.

---

### 10. Delete Subscription

**Endpoint:** `DELETE /api/m365/mail/subscriptions/{subscription_id}`

**Description:** Delete a webhook subscription.

**Request:**
```bash
curl -X DELETE http://localhost:8000/api/m365/mail/subscriptions/subscription-xyz-789
```

**Response:**
```json
{
  "status": "success",
  "message": "Subscription subscription-xyz-789 deleted successfully"
}
```

**Use Case:** When user disconnects their account or disables auto-draft feature.

---

### 11. Webhook Endpoint

**Endpoint:** `GET|POST /api/m365/mail/webhook`

**Description:** Receives notifications from Microsoft Graph when subscribed events occur (e.g., new email arrives).

**⚠️ This endpoint is called by Microsoft, not by your application!**

**Validation Request (from Microsoft):**
```
GET /api/m365/mail/webhook?validationToken=abc123xyz
```

**Response:**
```
200 OK
Content-Type: text/plain

abc123xyz
```

**Notification Request (from Microsoft):**
```json
POST /api/m365/mail/webhook

{
  "value": [
    {
      "subscriptionId": "subscription-xyz-789",
      "clientState": "secret",
      "changeType": "created",
      "resource": "Users/abc123/Messages/AAMkAD..."
    }
  ]
}
```

**Response:**
```json
{
  "status": "accepted",
  "message": "Notification received and processing"
}
```

**What Happens:**
1. New email arrives in user's inbox
2. Microsoft sends webhook notification to this endpoint
3. Server extracts message ID
4. Background task:
   - Fetches full email details
   - Generates AI-powered draft reply
   - Creates draft in user's mailbox
5. Returns `202 Accepted` immediately (within 3 seconds)

**Use Case:** Automatic draft reply generation when emails arrive. The main function for auto-draft replies.

---

## 🔄 Complete User Flow

### Flow 1: Connecting a User's M365 Account

```
┌─────────┐         ┌──────────┐         ┌─────────┐
│  User   │         │ Frontend │         │Microsoft│
└────┬────┘         └────┬─────┘         └────┬────┘
     │                   │                    │
     │ Clicks "Connect   │                    │
     │ Outlook"          │                    │
     ├──────────────────>│                    │
     │                   │                    │
     │                   │ GET /auth/authenticate
     │                   ├────────────────────>│
     │                   │                    │
     │                   │ Returns auth_url   │
     │                   │<────────────────────┤
     │                   │                    │
     │ Redirect to Microsoft login            │
     ├────────────────────────────────────────>│
     │                                         │
     │ Signs in with Microsoft account        │
     │<────────────────────────────────────────┤
     │                                         │
     │ Redirected back with code              │
     ├──────────────────>│                    │
     │                   │                    │
     │                   │ GET /auth/callback?code=...
     │                   ├────────────────────>│
     │                   │                    │
     │                   │ Exchange code for tokens
     │                   │<────────────────────┤
     │                   │                    │
     │                   │ Save tokens to data.json
     │                   │                    │
     │ "Connected!"      │                    │
     │<──────────────────┤                    │
     │                   │                    │
```

### Flow 2: Auto-Draft Email Replies

```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────┐
│ Sender  │    │Microsoft │    │Your API │    │ LLM │
└────┬────┘    └────┬─────┘    └────┬────┘    └──┬──┘
     │              │               │            │
     │ Sends email  │               │            │
     │ to user      │               │            │
     ├─────────────>│               │            │
     │              │               │            │
     │              │ POST /webhook │            │
     │              │ (new email)   │            │
     │              ├──────────────>│            │
     │              │               │            │
     │              │ 202 Accepted  │            │
     │              │<──────────────┤            │
     │              │               │            │
     │              │               │ Fetch email details
     │              │<──────────────┤            │
     │              │               │            │
     │              │ Email content │            │
     │              ├──────────────>│            │
     │              │               │            │
     │              │               │ Generate reply
     │              │               ├───────────>│
     │              │               │            │
     │              │               │ AI reply   │
     │              │               │<───────────┤
     │              │               │            │
     │              │ Create draft  │            │
     │              │<──────────────┤            │
     │              │               │            │
     │              │ Draft created │            │
     │              ├──────────────>│            │
     │              │               │            │
     │              │     User sees draft in     │
     │              │     Outlook Drafts folder  │
     │              │               │            │
```

---

## 🚀 Setup & Configuration

### Prerequisites

1. **Microsoft Azure AD App Registration**
   - Client ID
   - Client Secret
   - Tenant ID (or use "common")
   - Redirect URI configured (must match the redirect URI configured in Azure AD app registration)

2. **Environment Variables** (.env file)
   ```env
   MICROSOFT_CLIENT_ID=your_client_id
   MICROSOFT_CLIENT_SECRET=your_client_secret
   MICROSOFT_TENANT_ID=common
   REDIRECT_URI=http://URL_or_localhost:8000/api/m365/auth/callback
   WEBHOOK_URL=https://PUBLIC_DOMAIN_HERE/api/m365/mail/webhook
   ```

---

## 🔑 Azure AD App Configuration

### 1. Create App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: **Azure Active Directory** → **App registrations** → **New registration**
3. Fill in:
   - **Name**: "M365 Email Connector"
   - **Supported account types**: "Accounts in any organizational directory and personal Microsoft accounts"
   - **Redirect URI**: `http://localhost:8000/api/m365/auth/callback`

### 2. Configure Permissions

1. Go to **API permissions** → **Add a permission**
2. Select **Microsoft Graph** → **Delegated permissions**
3. Add these permissions:
   - `Mail.ReadWrite` - Read and write mail
   - `User.Read` - Read user profile
   - `offline_access` - Maintain access to data
4. Click **Grant admin consent** (if you're admin)

### 3. Generate Client Secret

1. Go to **Certificates & secrets** → **New client secret**
2. Description: "M365 Connector Secret"
3. Expires: 24 months (or custom)
4. Copy the **Value** (this is your `MICROSOFT_CLIENT_SECRET`)

### 4. Copy Credentials

- **Application (client) ID** → `MICROSOFT_CLIENT_ID`
- **Directory (tenant) ID** → `MICROSOFT_TENANT_ID`
- **Client secret value** → `MICROSOFT_CLIENT_SECRET`

---

## 📊 Data Storage

All data is stored in `src/api/data.json`:

```json
{
  "user_tokens": {
    "user_id_123": {
      "access_token": "eyJ0...",
      "refresh_token": "0.AX0A...",
      "expires_at": 1699123456.789,
      "user_profile": {
        "id": "user_id_123",
        "displayName": "John Doe",
        "mail": "john@company.com"
      }
    }
  },
  "subscriptions": {
    "subscription_xyz": {
      "id": "subscription_xyz",
      "user_id": "user_id_123",
      "resource": "me/mailFolders('Inbox')/messages",
      "expires_at": "2024-11-10T12:00:00Z"
    }
  }
}
```
---

**Last Updated:** 2025-10-07
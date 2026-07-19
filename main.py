from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

import models
import schemas
import auth
from database import engine, get_db

# Create the database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Routine Management API")

# ==========================================
# META WHATSAPP WEBHOOKS
# ==========================================
VERIFY_TOKEN = "routine_secure_token_123"


@app.get("/webhook")
def verify_webhook(request: Request):
    """Meta pings this URL to verify we own the server."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge)

    raise HTTPException(status_code=403, detail="Invalid verification token")


@app.post("/webhook")
async def receive_whatsapp_message(request: Request, db: Session = Depends(get_db)):
    """Meta sends button clicks and user replies here."""
    data = await request.json()

    try:
        # 1. Verify this is a WhatsApp business event
        if data.get("object") == "whatsapp_business_account":
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    # 2. Check if there are actual messages (ignoring "read"/"delivered" status updates)
                    if "messages" in value:
                        message = value["messages"][0]
                        phone_number = message.get("from")
                        msg_type = message.get("type")

                        print(f"\n📩 Message received from: {phone_number}")

                        # 3. Handle standard text messages
                        if msg_type == "text":
                            text_body = message["text"]["body"]
                            print(f"💬 They said: {text_body}")

                        # 4. Handle button clicks (interactive messages)
                        elif msg_type == "interactive":
                            button_id = message["interactive"]["button_reply"]["id"]
                            button_title = message["interactive"]["button_reply"]["title"]
                            print(f"👆 They clicked button: {button_title} (ID: {button_id})")

                            # Example Database Logic: If they clicked "Done", we would look up
                            # the task using the button_id and mark it as completed here!

                    # 5. Check for delivery status updates (sent, delivered, read, failed)
                    elif "statuses" in value:
                        status_update = value["statuses"][0]
                        current_status = status_update.get("status")
                        recipient = status_update.get("recipient_id")
                        print(f"\n🚦 Message Status Update: {current_status.upper()} (To: {recipient})")

                        if "errors" in status_update:
                            print(f"❌ DELIVERY ERROR FROM META: {status_update['errors']}")

    except Exception as e:
        print(f"Error parsing webhook data: {e}")

    # We must always return a 200 OK so Meta knows we got the message
    return {"status": "success"}


# ==========================================
# STANDARD API ROUTES
# ==========================================
@app.get("/")
def read_root():
    return {"message": "Welcome to Routine Manager API. Webhook is ready!"}
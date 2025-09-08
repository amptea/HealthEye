import os
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


# Load environment from project root .env if present
def _load_env_once() -> None:
    if not getattr(_load_env_once, "_loaded", False):
        # Try project root and current file directory
        load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
        load_dotenv()
        _load_env_once._loaded = True


def send_email_via_ses(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
    aws_region: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an email using AWS SES.

    Env vars used if parameters are not provided:
    - FROM_EMAIL
    - AWS_REGION (fallback to us-east-1)
    - AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN
    """
    _load_env_once()

    source_email = from_email or os.getenv("FROM_EMAIL")
    if not source_email:
        raise ValueError("Missing from_email. Set parameter or FROM_EMAIL in environment.")

    region = aws_region or os.getenv("AWS_REGION") or "us-east-1"

    ses_client = boto3.client("ses", region_name=region)

    try:
        response = ses_client.send_email(
            Source=source_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text_body or html_body, "Charset": "UTF-8"},
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return {"status": "sent", "message_id": response.get("MessageId")}
    except ClientError as e:
        return {"status": "error", "error": str(e)}



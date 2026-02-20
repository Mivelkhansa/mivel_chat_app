# -------------------------
# Helper functions
# -------------------------
from bleach import clean, linkifier, linkify
from markdown import markdown

import models
from config import ALLOWED_ATTRIBUTES, ALLOWED_PROTOCOLS, ALLOWED_TAGS


def get_username(db, user_id: str) -> str:
    return (
        db.query(models.User.username).filter(models.User.user_id == user_id).scalar()
    )


def sanitize_message(message: str) -> str:
    sanitized_message = clean(
        message,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    sanitized_message = linkify(
        sanitized_message,
        callbacks=linkifier.DEFAULT_CALLBACKS
        + [
            lambda attrs, new=False: {
                **attrs,
                (None, "target"): "_blank",
                (None, "rel"): "noopener noreferrer nofollow",
            }
        ],
        skip_tags=["pre", "code"],
    )
    return sanitized_message


def render_message(message: str) -> str:
    html = markdown(message, extensions=["extra"])
    sanitized_html = sanitize_message(html)
    return sanitized_html

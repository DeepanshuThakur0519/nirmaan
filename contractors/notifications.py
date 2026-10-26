import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger(__name__)


def _url(name, *args):
    """Build a full link such as http://127.0.0.1:8000/dashboard/requests/"""
    return settings.SITE_URL.rstrip("/") + reverse(name, args=args)


def _name(user):
    return user.first_name or user.username


def _send(subject, message, recipient):
    """Send one email. A failure is logged but never breaks the page the user is on."""
    if not recipient:
        return
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient])
    except Exception:
        logger.exception("Could not send email: %s", subject)


def notify_new_quote(quote):
    """Tell a contractor that a client sent a quote request."""
    contractor = quote.contractor
    client = quote.client
    specialty = quote.specialty.name if quote.specialty else "Not specified"
    message = (
        f"Hello {_name(contractor.user)},\n\n"
        f"{_name(client)} has sent you a quote request on Nirmaan.\n\n"
        f"Type of work: {specialty}\n"
        f"Location: {quote.location}\n"
        f"Budget: Rs. {quote.budget:,.0f}\n"
        f"Timeline: {quote.get_timeline_display()}\n\n"
        f"Project details:\n{quote.description}\n\n"
        f"Log in to reply: {_url('contractors:contractor_requests')}\n\n"
        "The Nirmaan team\n"
    )
    _send(f"New quote request from {_name(client)}", message, contractor.user.email)


def notify_quote_reply(quote):
    """Tell a client that a contractor accepted or declined their request."""
    contractor = quote.contractor
    accepted = quote.status == "accepted"
    outcome = "accepted" if accepted else "declined"
    if accepted:
        next_step = f"After the work, you can rate this contractor here: {_url('contractors:review_edit', contractor.pk)}"
    else:
        next_step = f"You can look for other verified contractors here: {_url('contractors:list')}"
    message = (
        f"Hello {_name(quote.client)},\n\n"
        f"{contractor.company_name} has {outcome} your quote request.\n\n"
        f"Their message:\n{quote.contractor_reply}\n\n"
        f"{next_step}\n\n"
        f"All your requests: {_url('contractors:my_requests')}\n\n"
        "The Nirmaan team\n"
    )
    _send(f"{contractor.company_name} has {outcome} your request", message, quote.client.email)


def notify_verified(profile):
    """Tell a contractor that their company is now verified."""
    message = (
        f"Hello {_name(profile.user)},\n\n"
        f"Good news: {profile.company_name} is now verified on Nirmaan. "
        "Clients can find your profile and send you quote requests.\n\n"
        f"Your public page: {_url('contractors:detail', profile.pk)}\n"
        f"Your dashboard: {_url('contractors:dashboard')}\n\n"
        "The Nirmaan team\n"
    )
    _send("Your Nirmaan profile is verified", message, profile.user.email)
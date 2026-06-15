import logging

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.integrations.email import makerspace_mail_connection

logger = logging.getLogger(__name__)

_SUBJECTS = {
    "submitted": "We received your makerspace print request",
    "accepted": "Your makerspace print request was accepted",
    "started": "Your makerspace print request is now printing",
    "rejected": "Your makerspace print request was rejected",
    "completed": "Your makerspace print request is ready to collect",
}


def send_print_email(event, print_request):
    # Public requests come from Check-In shadow users with no account email, so the
    # reachable address is the contact_email captured on the request; fall back to the
    # requester's account email for staff-created/authenticated requests.
    recipient = print_request.contact_email or print_request.requester.email
    if not recipient:
        return

    subject = _SUBJECTS[event]
    context = {"print_request": print_request}
    try:
        text_body = render_to_string(f"email/print_{event}.txt", context)
        html_body = render_to_string(f"email/print_{event}.html", context)
        connection, from_email = makerspace_mail_connection(
            print_request.bucket.makerspace
        )
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=from_email,
            to=[recipient],
            connection=connection,
        )
        message.attach_alternative(html_body, "text/html")
        message.send()
    except Exception:
        logger.warning(
            "print_email_send_failed",
            extra={
                "event": event,
                "print_request_id": print_request.pk,
                "requester_id": print_request.requester_id,
            },
            exc_info=True,
        )

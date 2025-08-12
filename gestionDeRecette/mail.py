
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend

class CustomEmailBackend(EmailBackend):
    """Custom Email backend used in the project."""

    def send_messages(self, messages):
        for message in messages:
            # if settings.DEBUG is enabled we want to send the e-mail to a specific debug e-mail instead of
            # sending it to end users. This way while deployed in local and DEV, e-mails are not send to real people.
            if settings.DEBUG:
                message.subject = "{subject} [{to}]".format(
                    subject=message.subject,
                    to=', '.join(message.to)
                )
                message.to = [settings.DEBUG_EMAIL]
                message.cc = []
                message.bcc = []

        return super(CustomEmailBackend, self).send_messages(messages)

# from django.core.mail import send_mail
# send_mail("subject", "body",  None, ["sepul.nathan@gmail.com"], fail_silently=False,)
def send_email(subject, to, text_content, html_content):
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives

    email = EmailMultiAlternatives(
        subject,
        text_content,
        settings.EMAIL_HOST_USER,
        [to]
    )

    email.attach_alternative(html_content, "text/html")
    email.send()

if __name__ == "__main__":
    import os
    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

    from django.template.loader import render_to_string

    verification_link = "http://localhost:8000/test-link"

    html_content = render_to_string(
        "emails/verify_email.html",
        {
            "verification_link": verification_link
        }
    )

    text_content = f"Тестовое письмо:\n{verification_link}"

    send_email(
        subject="Тест Splitra",
        to="gonkong2111@gmail.com",
        text_content=text_content,
        html_content=html_content
    )
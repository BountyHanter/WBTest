from django.contrib.auth.tokens import default_token_generator


def generate_verification_token(user):
    return default_token_generator.make_token(user)


def check_verification_token(user, token):
    return default_token_generator.check_token(user, token)
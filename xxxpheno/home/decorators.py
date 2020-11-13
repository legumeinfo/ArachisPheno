from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings

def login_if_required(function = None, redirect_field_name = REDIRECT_FIELD_NAME, login_url = None) :
    # Decorator that (if REQUIRE_USER_AUTHENTICATION is True)
    # tests whether the user is logged in, and redirects to the login view if not.
    def test_if_required(u) :
        if (settings.REQUIRE_USER_AUTHENTICATION) :
            return u.is_authenticated
        else :
            return True

    actual_decorator = user_passes_test(
        test_if_required,
        login_url = login_url,
        redirect_field_name = redirect_field_name
    )
    if (function) :
        return actual_decorator(function)
    return actual_decorator


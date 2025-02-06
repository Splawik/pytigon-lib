import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

# Initialize logger
LOGGER = logging.getLogger("pytigon")


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def authentication_error(
        self, request, provider_id, error, exception, extra_context
    ):
        """
        Handle authentication errors from social account providers.

        Args:
            request: The request object.
            provider_id (str): The ID of the social account provider.
            error: The error object.
            exception: The exception object.
            extra_context (dict): Additional context data.

        Returns:
            None
        """
        try:
            error_dict = {
                "title": "SocialAccount authentication error!",
                "provider_id": provider_id,
                "error": str(error),
                "exception": str(exception),
                "extra_context": extra_context,
            }
            LOGGER.error(error_dict)
        except Exception as e:
            LOGGER.error(f"Failed to log authentication error: {str(e)}")

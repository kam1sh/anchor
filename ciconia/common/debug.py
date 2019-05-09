import logging
import pprint

log = logging.getLogger(__name__)


class Logger(logging.getLoggerClass()):
    """
    Basic logger with a few improvments in formatting and django integration.
    """

    def debug(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        """
        args = list(args)
        for i, item in enumerate(args):
            if isinstance(item, dict, list):
                args[i] = pprint.pformat(item)
        return super().debug(msg, *args, **kwargs)

    def dump_headers(self, request):
        """Logs all request headers with DEBUG level."""
        headers = {
            {k: x for k, x in request.META.items() if str(k).startswith("HTTP_")}
        }
        self.debug("%s", headers)


logging.setLoggerClass(Logger)

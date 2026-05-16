"""IMAP4 client using Twisted for asynchronous mailbox operations.

Provides connection management, message fetching, and sending via IMAP.
"""

import io
import logging
from email.mime.text import MIMEText

from twisted.internet import defer, protocol, reactor, ssl
from twisted.mail import imap4

logger = logging.getLogger(__name__)


def GetMailboxConnection(server, user, password, mailbox="inbox", mailbox2="outbox"):
    """Establish an SSL connection to an IMAP server and select a mailbox.

    Args:
        server: IMAP server hostname.
        user: Login username.
        password: Login password.
        mailbox: Primary mailbox to select (default 'inbox').
        mailbox2: Secondary mailbox name (default 'outbox').

    Returns:
        A Twisted Deferred that fires with the connected IMAP4Client instance
        or errbacks on failure.
    """
    f = protocol.ClientFactory()
    f.user = user.encode("utf-8")
    f.password = password.encode("utf-8")
    f.mailbox = mailbox
    f.mailbox2 = mailbox2

    class ConnectInbox(imap4.IMAP4Client):
        @defer.inlineCallbacks
        def serverGreeting(self, caps):
            """Handle server greeting: login and select the configured mailbox."""
            try:
                yield self.login(self.factory.user, self.factory.password)
                yield self.select(self.factory.mailbox)
                self.factory.deferred.callback(self)
            except Exception as e:
                logger.error("Login or mailbox selection failed: %s", e)
                self.factory.deferred.errback(e)

    f.protocol = ConnectInbox
    reactor.connectSSL(server, 993, f, ssl.ClientContextFactory())

    f.deferred = defer.Deferred()
    return f.deferred


@defer.inlineCallbacks
def get_unseen_messages(conn, callback):
    """Fetch all unseen (unread) messages from the currently selected mailbox.

    Args:
        conn: An authenticated IMAP4Client instance.
        callback: A callable invoked for each message body.

    Yields:
        Deferred from list_messages.
    """
    try:
        result = yield conn.search(imap4.Query(unseen=True), uid=True)
        yield list_messages(result, conn, callback)
    except Exception as e:
        logger.error("Error fetching unseen messages: %s", e)
        raise


@defer.inlineCallbacks
def send_test_message(conn, msg):
    """Append a message to the secondary mailbox (e.g. 'Sent').

    Args:
        conn: An authenticated IMAP4Client instance.
        msg: An email.message.Message object to append.
    """
    try:
        logger.info("Sending message: %s", msg["Subject"])
        x = io.BytesIO(msg.as_string().encode("utf-8"))
        yield conn.append(conn.factory.mailbox2, x)
        yield final(None, conn)
    except Exception as e:
        logger.error("Error sending message: %s", e)
        raise


def list_messages(result, conn, callback):
    """Request bodies for a set of message UIDs and pass them to a callback.

    Args:
        result: Iterable of message UIDs.
        conn: An authenticated IMAP4Client instance.
        callback: Callable receiving each message body.

    Returns:
        Deferred from fetchBody or final.
    """
    if result:
        messages = ",".join(map(str, result))
        return conn.fetchBody(messages, uid=True).addCallback(
            fetch_msg, conn, messages, callback
        )
    else:
        logger.info("No new messages found.")
        return final(None, conn)


def fetch_msg(result, conn, messages, callback):
    """Process fetched message bodies and mark them as seen.

    Args:
        result: Dict mapping UIDs to message parts from fetchBody.
        conn: An authenticated IMAP4Client instance.
        messages: Comma-separated UID string for flagging.
        callback: Callable receiving each message body.

    Returns:
        Deferred from addFlags/final.
    """
    if result:
        logger.info("New messages found.")
        for key in sorted(result):
            for part in result[key]:
                callback(result[key][part])
        return conn.addFlags(messages, "SEEN", uid=True).addCallback(final, conn)
    else:
        logger.info("Empty mailbox.")
        return final(None, conn)


def final(result, conn):
    """Log out and close the IMAP connection.

    Args:
        result: Ignored result from the previous deferred callback.
        conn: An authenticated IMAP4Client instance.

    Returns:
        Deferred from conn.logout().
    """
    return conn.logout()


class IMAPClient:
    """High-level IMAP client wrapping connection and operation helpers.

    Usage::

        client = IMAPClient('imap.example.com', 'user', 'pass')
        client.save_to_sent(msg)
        client.check_mails(my_callback)
        reactor.run()
    """

    def __init__(self, server, username, password, inbox="inbox", outbox="outbox"):
        """Initialize the IMAP client with server credentials.

        Args:
            server: IMAP server hostname.
            username: Login username.
            password: Login password.
            inbox: Inbox folder name.
            outbox: Sent/outbox folder name.
        """
        self.server = server
        self.username = username
        self.password = password
        self.inbox = inbox
        self.outbox = outbox

    def save_to_sent(self, msg):
        """Save an email message to the outbox/sent folder.

        Args:
            msg: An email.message.Message object.

        Returns:
            Deferred that fires when the message has been appended.
        """
        return GetMailboxConnection(
            self.server, self.username, self.password, mailbox2=self.outbox
        ).addCallback(send_test_message, msg)

    def check_mails(self, callback):
        """Check the inbox for new (unread) messages.

        Args:
            callback: Callable invoked with each new message body.

        Returns:
            Deferred that fires when all new messages have been processed.
        """
        return GetMailboxConnection(
            self.server, self.username, self.password, self.inbox
        ).addCallback(get_unseen_messages, callback)


if __name__ == "__main__":
    server = "imap.gmail.com"
    username = "abc@gmail.com"
    password = "abc"
    client = IMAPClient(server, username, password, "inbox", "[Gmail]/Wys\u0142ane")

    msg = MIMEText("Hello world!")
    msg["Subject"] = "Subject"
    msg["From"] = "abc"
    msg["To"] = "def"
    client.save_to_sent(msg)

    def callback(x):
        """Save received message to a file for testing."""
        with open("x.dat", "w") as f:
            f.write(x)

    client.check_mails(callback)

    reactor.run()

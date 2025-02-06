from getpass import getpass
from os import environ
from twisted.mail import imap4
from twisted.internet import reactor, protocol, defer
import email
from twisted.internet import ssl
from email.mime.text import MIMEText
import io
import logging

logger = logging.getLogger(__name__)


def GetMailboxConnection(server, user, password, mailbox="inbox", mailbox2="outbox"):
    """Establish a connection to the IMAP server and select the specified mailbox."""
    f = protocol.ClientFactory()
    f.user = user.encode("utf-8")
    f.password = password.encode("utf-8")
    f.mailbox = mailbox
    f.mailbox2 = mailbox2

    class ConnectInbox(imap4.IMAP4Client):
        @defer.inlineCallbacks
        def serverGreeting(self, caps):
            """Handle server greeting, login, and mailbox selection."""
            try:
                yield self.login(self.factory.user, self.factory.password)
                yield self.select(self.factory.mailbox)
                self.factory.deferred.callback(self)
            except Exception as e:
                logger.error(f"Error during login or mailbox selection: {e}")
                self.factory.deferred.errback(e)

    f.protocol = ConnectInbox
    reactor.connectSSL(server, 993, f, ssl.ClientContextFactory())

    f.deferred = defer.Deferred()
    return f.deferred


@defer.inlineCallbacks
def get_unseen_messages(conn, callback):
    """Fetch unseen messages from the mailbox."""
    try:
        result = yield conn.search(imap4.Query(unseen=True), uid=True)
        yield list_messages(result, conn, callback)
    except Exception as e:
        logger.error(f"Error fetching unseen messages: {e}")
        raise


@defer.inlineCallbacks
def send_test_message(conn, msg):
    """Send a test message to the specified mailbox."""
    try:
        logger.info(f"Sending message: {msg['Subject']}")
        x = io.BytesIO(msg.as_string().encode("utf-8"))
        yield conn.append(conn.factory.mailbox2, x)
        yield final(None, conn)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise


def list_messages(result, conn, callback):
    """List and process messages fetched from the mailbox."""
    if result:
        messages = ",".join(map(str, result))
        return conn.fetchBody(messages, uid=True).addCallback(
            fetch_msg, conn, messages, callback
        )
    else:
        logger.info("No new messages found.")
        return final(None, conn)


def fetch_msg(result, conn, messages, callback):
    """Fetch and process the body of the messages."""
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
    """Finalize the connection by logging out."""
    return conn.logout()


class IMAPClient:
    """IMAP client to handle mailbox operations."""

    def __init__(self, server, username, password, inbox="inbox", outbox="outbox"):
        self.server = server
        self.username = username
        self.password = password
        self.inbox = inbox
        self.outbox = outbox

    def save_to_sent(self, msg):
        """Save a message to the sent folder."""
        return GetMailboxConnection(
            self.server, self.username, self.password, mailbox2=self.outbox
        ).addCallback(send_test_message, msg)

    def check_mails(self, callback):
        """Check for new mails in the inbox."""
        return GetMailboxConnection(
            self.server, self.username, self.password, self.inbox
        ).addCallback(get_unseen_messages, callback)


if __name__ == "__main__":
    server = "imap.gmail.com"
    username = "abc@gmail.com"
    password = "abc"
    client = IMAPClient(server, username, password, "inbox", "[Gmail]/Wysłane")

    msg = MIMEText("Hello world!")
    msg["Subject"] = "Subject"
    msg["From"] = "abc"
    msg["To"] = "def"
    client.save_to_sent(msg)

    def callback(x):
        """Callback function to handle new messages."""
        with open("x.dat", "w") as f:
            f.write(x)

    client.check_mails(callback)

    reactor.run()

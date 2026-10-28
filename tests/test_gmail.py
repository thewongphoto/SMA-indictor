import base64
from email import policy
from email.parser import BytesParser
import io
import json
from unittest import TestCase
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from sma_analyzer.gmail import GmailSender, GmailError, GMAIL_SEND_URL
from sma_analyzer.android_gmail import AndroidGmailAuthorizer
from sma_analyzer.notifications import Alert, deliver_alerts, NotificationSettings
from sma_analyzer.storage import LineStore
from pathlib import Path
from tempfile import TemporaryDirectory


class GmailTests(TestCase):
    def setUp(self):
        self.alert = Alert('email','buy','DEMO-SGX','Trending',11,12,40,
                           'Buy Signal for DEMO-SGX','SIMULATED DATA · example body')
        self.transport = Mock(side_effect=lambda *a, **k: io.BytesIO(b'{"id":"gmail-id"}'))
        self.clock = Mock(return_value=100)
        self.sender = GmailSender('kelwong98@gmail.com',self.transport,self.clock)

    def test_unconnected_expired_and_disconnected_never_call_network(self):
        with self.assertRaisesRegex(GmailError,'Connect Gmail'): self.sender.send(self.alert,'reader@example.com')
        self.sender.accept_access_token('test-token')
        self.clock.return_value = 100+45*60
        with self.assertRaisesRegex(GmailError,'Connect Gmail'): self.sender.send(self.alert,'reader@example.com')
        self.sender.accept_access_token('test-token')
        self.sender.disconnect()
        self.assertFalse(self.sender.connected)
        self.transport.assert_not_called()

    def test_desktop_authorization_has_clear_setup_error(self):
        authorizer = AndroidGmailAuthorizer()
        success, failure = Mock(), Mock()
        with self.assertRaisesRegex(RuntimeError,'Android build'):
            authorizer.authorize('kelwong98@gmail.com',success,failure)
        success.assert_not_called()
        failure.assert_not_called()
        authorizer.close()

    def test_request_uses_tls_send_only_endpoint_and_correct_mime(self):
        self.sender.accept_access_token('test-token')
        self.assertEqual(self.sender.send(self.alert,'reader@example.com'),'gmail-id')
        args, kwargs = self.transport.call_args
        request, = args
        self.assertEqual(request.full_url,GMAIL_SEND_URL)
        self.assertEqual(request.get_method(),'POST')
        self.assertEqual(request.get_header('Authorization'),'Bearer test-token')
        self.assertEqual(kwargs['timeout'],15)
        self.assertTrue(kwargs['context'].check_hostname)
        raw = json.loads(request.data)['raw']
        message = BytesParser(policy=policy.default).parsebytes(base64.urlsafe_b64decode(raw))
        self.assertEqual(message['From'],'kelwong98@gmail.com')
        self.assertEqual(message['To'],'reader@example.com')
        self.assertEqual(message['Subject'],self.alert.subject)
        self.assertEqual(message.get_content().strip(),self.alert.body)

    def test_sender_is_configurable_and_invalid_headers_block_network(self):
        other = GmailSender('dedicated@example.com',self.transport)
        other.accept_access_token('test-token')
        for recipient in ('','broken','a@example.com\nBcc:other@example.com'):
            with self.assertRaises((GmailError,ValueError)): other.send(self.alert,recipient)
        self.transport.assert_not_called()
        with self.assertRaises(ValueError): GmailSender('')
        with self.assertRaises(GmailError): other.accept_access_token('')

    def test_http_errors_are_safe_and_401_clears_token(self):
        for status in (401,403,429,500):
            self.sender.accept_access_token('test-token')
            self.transport.side_effect = HTTPError(GMAIL_SEND_URL,status,'secret server reply',{},None)
            with self.assertRaises(GmailError) as failure: self.sender.send(self.alert,'reader@example.com')
            self.assertNotIn('test-token',str(failure.exception))
            self.assertNotIn('secret server reply',str(failure.exception))
            if status==401: self.assertFalse(self.sender.connected)

    def test_no_automatic_retry_after_uncertain_delivery(self):
        self.sender.accept_access_token('test-token')
        self.transport.side_effect = URLError('secret')
        with self.assertRaisesRegex(GmailError,'Sent before retrying'): self.sender.send(self.alert,'reader@example.com')
        self.assertEqual(self.transport.call_count,1)

    def test_bad_confirmation_is_not_success(self):
        self.sender.accept_access_token('test-token')
        self.transport.side_effect = lambda *a, **k: io.BytesIO(b'{}')
        with self.assertRaisesRegex(GmailError,'no message confirmation'): self.sender.send(self.alert,'reader@example.com')

    def test_dispatch_email_success_dedup_and_failure_retry(self):
        with TemporaryDirectory() as directory:
            store = LineStore(Path(directory)/'data.sqlite3')
            store.save_notification_settings(NotificationSettings(email='reader@example.com'))
            self.sender.accept_access_token('test-token')
            self.assertIn('Accepted by Gmail',deliver_alerts(store,[self.alert],mailer=self.sender)[0])
            self.assertIn('Already delivered',deliver_alerts(store,[self.alert],mailer=self.sender)[0])
            self.assertEqual(self.transport.call_count,1)
            second = Alert('email','monitor','DEMO-SGX','Trending',11,12,41,'Monitor','SIMULATED')
            self.transport.side_effect = URLError('offline')
            self.assertIn('Delivery failed',deliver_alerts(store,[second],mailer=self.sender)[0])
            self.assertFalse(store.was_delivered(second.key))
            self.transport.side_effect = lambda *a, **k: io.BytesIO(b'{"id":"second"}')
            self.assertIn('Accepted by Gmail',deliver_alerts(store,[second],mailer=self.sender)[0])

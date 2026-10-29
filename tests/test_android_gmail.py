"""Python-to-native lifecycle checks; consent itself still needs a Google device."""
import sys
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from sma_analyzer.android_gmail import AndroidGmailAuthorizer


class AndroidGmailBridgeTests(TestCase):
    def setUp(self):
        self.activity = Mock()
        self.bridge = Mock()
        self.events = Mock()
        jnius = ModuleType('jnius')
        jnius.autoclass = lambda name: (SimpleNamespace(mActivity=self.activity)
                                      if name.endswith('PythonActivity') else self.bridge)
        jnius.PythonJavaClass = type('PythonJavaClass', (), {})
        jnius.java_method = lambda signature: lambda method: method
        android = ModuleType('android')
        android.activity = self.events
        self.modules = patch.dict(sys.modules, {'jnius': jnius, 'android': android})
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.authorizer = AndroidGmailAuthorizer()
        self.addCleanup(self.authorizer.close)

    def test_cancelled_result_intent_reaches_native_error_parser(self):
        token, error = Mock(), Mock()
        self.authorizer.authorize('sender@example.com', token, error)
        callback = self.events.bind.call_args.kwargs['on_activity_result']
        data = object()
        callback(5017, 0, data)
        self.bridge.onActivityResult.assert_called_once_with(self.activity, 5017, 0, data)
        listener = self.bridge.authorize.call_args.args[2]
        listener.onFailure('Google authorization failed (code 10). Check package/SHA-1.')
        error.assert_called_once_with('Google authorization failed (code 10). Check package/SHA-1.')
        token.assert_not_called()

    def test_token_callback_retained_and_binding_is_reused(self):
        first, second = Mock(), Mock()
        self.authorizer.authorize('sender@example.com', first, Mock())
        listener = self.authorizer._listener
        listener.onToken('test-token')
        first.assert_called_once_with('test-token')
        self.authorizer.authorize('sender@example.com', second, Mock())
        self.events.bind.assert_called_once()
        self.authorizer._listener.onToken('next-test-token')
        second.assert_called_once_with('next-test-token')

    def test_close_unbinds_exact_activity_callback(self):
        self.authorizer.authorize('sender@example.com', Mock(), Mock())
        callback = self.events.bind.call_args.kwargs['on_activity_result']
        self.authorizer.close()
        self.events.unbind.assert_called_once_with(on_activity_result=callback)
        self.assertIsNone(self.authorizer._listener)

"""Lazy Android Google Identity authorization bridge; no desktop Google dependency."""


class AndroidGmailAuthorizer:
    def __init__(self):
        self._bridge = None
        self._listener = None  # Keep Pyjnius callback alive through consent/activity result.
        self._activity = None
        self._on_result = None

    def _prepare(self):
        if self._bridge is not None:
            return
        try:
            from jnius import autoclass
            from android import activity
            self._activity = autoclass("org.kivy.android.PythonActivity").mActivity
            self._bridge = autoclass("org.thewongphoto.smaanalyzer.GmailAuthBridge")
            self._on_result = lambda request, result, data: self._bridge.onActivityResult(
                self._activity, request, result, data)
            activity.bind(on_activity_result=self._on_result)
        except Exception:
            self._bridge = None
            raise RuntimeError("Connect Gmail on the Android build with Google Play services. See the APK guide.") from None

    def _callbacks(self, on_token, on_error, on_disconnected):
        from jnius import PythonJavaClass, java_method

        class Listener(PythonJavaClass):
            __javainterfaces__ = ["org/thewongphoto/smaanalyzer/GmailAuthBridge$Listener"]
            __javacontext__ = "app"

            @java_method("(Ljava/lang/String;)V")
            def onToken(self, token):
                on_token(str(token))

            @java_method("(Ljava/lang/String;)V")
            def onFailure(self, message):
                on_error(str(message))

            @java_method("()V")
            def onDisconnected(self):
                on_disconnected()

        self._listener = Listener()
        return self._listener

    def authorize(self, sender, on_token, on_error):
        self._prepare()
        try:
            listener = self._callbacks(on_token, on_error, lambda: None)
            self._bridge.authorize(self._activity, sender, listener)
        except Exception:
            raise RuntimeError("Could not start Google authorization. Check the Android build and Google Play services.") from None

    def revoke(self, sender, on_done, on_error):
        self._prepare()
        try:
            listener = self._callbacks(lambda _: None, on_error, on_done)
            self._bridge.revoke(self._activity, sender, listener)
        except Exception:
            raise RuntimeError("Could not revoke Google access. Disconnect this app in your Google account settings.") from None

    def close(self):
        if self._on_result is not None:
            from android import activity
            activity.unbind(on_activity_result=self._on_result)
            self._on_result = None
        self._listener = None

package org.thewongphoto.smaanalyzer;

import android.accounts.Account;
import android.app.Activity;
import android.content.Intent;
import com.google.android.gms.auth.api.identity.AuthorizationRequest;
import com.google.android.gms.auth.api.identity.AuthorizationResult;
import com.google.android.gms.auth.api.identity.Identity;
import com.google.android.gms.auth.api.identity.RevokeAccessRequest;
import com.google.android.gms.common.api.Scope;
import java.util.Collections;
import java.util.List;

/** Google Identity send-only authorization. No password, client secret or token file. */
public final class GmailAuthBridge {
    public interface Listener {
        void onToken(String token);
        void onFailure(String message);
        void onDisconnected();
    }
    private static final int REQUEST = 5017;
    private static final List<Scope> SCOPES = Collections.singletonList(
        new Scope("https://www.googleapis.com/auth/gmail.send"));
    private static Listener pending;

    private GmailAuthBridge() {}

    public static void authorize(Activity activity, String sender, Listener listener) {
        activity.runOnUiThread(() -> {
            if (pending != null) {
                listener.onFailure("Google authorization is already in progress.");
                return;
            }
            pending = listener;
            try {
                AuthorizationRequest request = AuthorizationRequest.builder()
                    .setAccount(new Account(sender, "com.google"))
                    .setRequestedScopes(SCOPES).build();
                Identity.getAuthorizationClient(activity).authorize(request)
                    .addOnSuccessListener(activity, result -> {
                        if (result.hasResolution()) {
                            try {
                                activity.startIntentSenderForResult(
                                    result.getPendingIntent().getIntentSender(), REQUEST,
                                    null, 0, 0, 0);
                            } catch (Exception exception) {
                                fail("Could not open Google consent. Check Google Play services.");
                            }
                        } else {
                            token(result);
                        }
                    })
                    .addOnFailureListener(activity, error -> fail(
                        "Google authorization failed. Check the sender account, package/SHA-1 and OAuth setup."));
            } catch (Exception exception) {
                fail("Could not start Google authorization. Check Google Play services and OAuth setup.");
            }
        });
    }

    public static void onActivityResult(Activity activity, int request, int result, Intent data) {
        if (request != REQUEST || pending == null) return;
        if (result != Activity.RESULT_OK || data == null) {
            fail("Google authorization was cancelled. No email was sent.");
            return;
        }
        try {
            token(Identity.getAuthorizationClient(activity).getAuthorizationResultFromIntent(data));
        } catch (Exception exception) {
            fail("Google did not grant Gmail sending access. Try connecting again.");
        }
    }

    private static void token(AuthorizationResult result) {
        String accessToken = result.getAccessToken();
        if (accessToken == null || accessToken.isEmpty()) {
            fail("Google did not grant Gmail sending access.");
            return;
        }
        Listener listener = pending;
        pending = null;
        if (listener != null) listener.onToken(accessToken);
    }

    private static void fail(String message) {
        Listener listener = pending;
        pending = null;
        if (listener != null) listener.onFailure(message);
    }

    public static void revoke(Activity activity, String sender, Listener listener) {
        activity.runOnUiThread(() -> {
            if (pending != null) {
                listener.onFailure("Finish Google authorization before disconnecting.");
                return;
            }
            try {
                RevokeAccessRequest request = RevokeAccessRequest.builder()
                    .setAccount(new Account(sender, "com.google"))
                    .setScopes(SCOPES).build();
                Identity.getAuthorizationClient(activity).revokeAccess(request)
                    .addOnSuccessListener(activity, unused -> listener.onDisconnected())
                    .addOnFailureListener(activity, error -> listener.onFailure(
                        "Local connection cleared. Revoke app access in your Google account if needed."));
            } catch (Exception exception) {
                listener.onFailure("Local connection cleared. Revoke app access in your Google account settings.");
            }
        });
    }
}

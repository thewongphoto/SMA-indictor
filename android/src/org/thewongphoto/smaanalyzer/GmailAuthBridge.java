package org.thewongphoto.smaanalyzer;

import android.accounts.Account;
import android.app.Activity;
import android.content.Intent;
import com.google.android.gms.auth.api.identity.AuthorizationRequest;
import com.google.android.gms.auth.api.identity.AuthorizationResult;
import com.google.android.gms.auth.api.identity.Identity;
import com.google.android.gms.auth.api.identity.RevokeAccessRequest;
import com.google.android.gms.common.api.Scope;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.common.GoogleApiAvailability;
import com.google.android.gms.common.ConnectionResult;
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
                int availability = GoogleApiAvailability.getInstance().isGooglePlayServicesAvailable(activity);
                if (availability != ConnectionResult.SUCCESS) {
                    fail("Google Play services is unavailable (code " + availability + "). Update/enable it, then reconnect Gmail.");
                    return;
                }
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
                    .addOnFailureListener(activity, error -> authorizationFailure(error));
            } catch (Exception exception) {
                fail("Could not start Google authorization. Check Google Play services and OAuth setup.");
            }
        });
    }

    public static void onActivityResult(Activity activity, int request, int result, Intent data) {
        if (request != REQUEST) return;
        activity.runOnUiThread(() -> {
            if (pending == null) return;
            // Google can return a structured API failure with RESULT_CANCELED.
            // Parse that Intent first; the activity result code alone is not a
            // reliable indication that the person cancelled the consent screen.
            if (data == null) {
                fail(result == Activity.RESULT_CANCELED
                    ? "Google closed authorization without a result (Android result 0). If you did not press Back/Cancel, check that the sender is signed in on this phone, is an OAuth test user, and that the Android OAuth client's package/SHA-1 matches this installed APK. No email was sent."
                    : "Google returned no authorization data (Android result " + result + "). Reconnect Gmail. No email was sent.");
                return;
            }
            try {
                token(Identity.getAuthorizationClient(activity).getAuthorizationResultFromIntent(data));
            } catch (Exception exception) {
                authorizationFailure(exception);
            }
        });
    }

    private static void authorizationFailure(Exception error) {
        // Never expose exception messages, Intent extras, account details or tokens.
        if (error instanceof ApiException) {
            int code = ((ApiException) error).getStatusCode();
            String advice;
            switch (code) {
                case 7:
                    advice = "Check the phone's internet connection and try again.";
                    break;
                case 10:
                case 12500:
                    advice = "Check the Android OAuth client package and SHA-1 against this installed APK, Gmail API, consent scope and test-user account.";
                    break;
                case 16:
                case 12501:
                    advice = "Google did not complete consent. If you did not cancel, check the sender account on this phone, OAuth test users and the installed APK's SHA-1.";
                    break;
                case 17:
                    advice = "Google sign-in or authorization is unavailable. Update Google Play services and check the signed-in sender account.";
                    break;
                default:
                    advice = "Check Google Play services, the sender account and Android OAuth setup, then reconnect.";
            }
            fail("Google authorization failed (code " + code + "). " + advice + " No email was sent.");
        } else {
            fail("Google authorization could not be completed. Check Google Play services and reconnect. No email was sent.");
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

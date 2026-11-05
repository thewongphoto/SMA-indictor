package org.thewongphoto.smaanalyzer;

import android.app.NotificationManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import androidx.work.Constraints;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;
import org.json.JSONArray;
import org.json.JSONObject;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.concurrent.TimeUnit;

/** OS adapter only: times/markets come from the shared Python configuration. */
public final class SmaAlertBridge {
    private static final String PREFS = "sma_daily_checks";
    private static final String PREFIX = "sma-daily-";
    private SmaAlertBridge() {}

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static JSONObject config(Context context) throws Exception {
        return new JSONObject(prefs(context).getString("configuration", "{}"));
    }

    static boolean enabled(Context context, String region) throws Exception {
        JSONArray regions = config(context).optJSONArray("regions");
        if (regions == null) return false;
        for (int i = 0; i < regions.length(); i++) {
            if (region.equals(regions.getString(i))) return true;
        }
        return false;
    }

    public static boolean notificationsAllowed(Context context) {
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(
                "android.permission.POST_NOTIFICATIONS") != 0) return false;
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (!manager.areNotificationsEnabled()) return false;
        android.app.NotificationChannel channel = manager.getNotificationChannel("sma_research_alerts");
        return channel == null || channel.getImportance() > 0;
    }

    public static long nextRun(String specification, long now) throws Exception {
        JSONObject spec = new JSONObject(specification);
        ZonedDateTime local = Instant.ofEpochMilli(now).atZone(ZoneId.of(spec.getString("timezone")));
        JSONArray weekdays = spec.getJSONArray("weekdays");
        for (int days = 0; days <= 7; days++) {
            ZonedDateTime candidate = local.plusDays(days).withHour(spec.getInt("hour"))
                    .withMinute(spec.getInt("minute")).withSecond(0).withNano(0);
            boolean eligible = false;
            for (int i = 0; i < weekdays.length(); i++) {
                if (weekdays.getInt(i) == candidate.getDayOfWeek().getValue() - 1) eligible = true;
            }
            if (eligible && candidate.toInstant().toEpochMilli() > now) return candidate.toInstant().toEpochMilli();
        }
        throw new IllegalArgumentException("No eligible daily slot");
    }

    static void schedule(Context context, String region) throws Exception {
        if (!enabled(context, region)) return;
        JSONObject spec = config(context).getJSONObject("schedules").getJSONObject(region);
        long now = System.currentTimeMillis();
        long target = nextRun(spec.toString(), now);
        OneTimeWorkRequest request = new OneTimeWorkRequest.Builder(SmaAlertWorker.class)
                .setInputData(new androidx.work.Data.Builder().putString("region", region).build())
                .setInitialDelay(Math.max(0, target - now), TimeUnit.MILLISECONDS)
                .setConstraints(new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .addTag(PREFIX + region).build();
        // Each absolute slot has a unique key. Enqueuing tomorrow must not
        // depend on today's worker finishing, nor replace/cancel that worker.
        WorkManager.getInstance(context).enqueueUniqueWork(PREFIX + region + "-" + target,
                ExistingWorkPolicy.KEEP, request);
    }

    public static String configure(Context supplied, String value) throws Exception {
        Context context = supplied.getApplicationContext();
        JSONObject previous = config(context);
        JSONObject current = new JSONObject(value);
        prefs(context).edit().putString("configuration", value).apply();
        JSONObject prior = previous.optJSONObject("schedules");
        boolean changed = prior == null || !prior.toString().equals(current.getJSONObject("schedules").toString());
        for (String region : new String[]{"US", "SG"}) {
            if (!enabled(context, region) || changed)
                WorkManager.getInstance(context).cancelAllWorkByTag(PREFIX + region);
            if (enabled(context, region)) schedule(context, region);
        }
        if (!notificationsAllowed(context)) return "Android notifications are blocked. Enable permission and the SMA alert channel in Android Settings.";
        return current.getJSONArray("regions").length() == 0
                ? "Enable a saved SMA and at least one signal type to schedule checks."
                : "Daily checks scheduled for enabled SMAs. Android may delay a check while sleeping or offline.";
    }

    static synchronized void error(Context context, String detail) {
        prefs(context).edit().putString("last_error", detail).putLong("last_error_at",System.currentTimeMillis()).apply();
    }

    public static synchronized String takeLastError(Context context) throws Exception {
        SharedPreferences preferences=prefs(context);
        String message=preferences.getString("last_error","");
        if (message.isEmpty()) return "";
        String result=new JSONObject().put("detail",message).put("at",preferences.getLong("last_error_at",System.currentTimeMillis())).toString();
        preferences.edit().remove("last_error").remove("last_error_at").apply();
        return result;
    }
}

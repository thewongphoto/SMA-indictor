package org.thewongphoto.smaanalyzer;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import androidx.work.ForegroundInfo;
import androidx.work.Worker;
import androidx.work.WorkerParameters;
import org.json.JSONObject;
import java.io.File;
import java.util.UUID;

/** WorkManager owns wake/foreground lifetime; Python owns data and signal rules. */
public final class SmaAlertWorker extends Worker {
    private static final Object PYTHON_SERVICE_LOCK = new Object();
    private volatile boolean serviceStarted;

    public SmaAlertWorker(Context context, WorkerParameters parameters) { super(context, parameters); }

    private ForegroundInfo foreground() {
        Context context = getApplicationContext();
        String channel = "sma_daily_data_checks";
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        manager.createNotificationChannel(new NotificationChannel(channel, "Daily SMA data checks", 2));
        int icon = context.getResources().getIdentifier("ic_stat_sma", "drawable", context.getPackageName());
        if (icon == 0) icon = android.R.drawable.stat_notify_sync;
        Notification.Builder builder = new Notification.Builder(context, channel)
                .setSmallIcon(icon).setContentTitle("Checking saved SMAs")
                .setContentText("Downloading completed daily prices for enabled alerts.").setOngoing(true);
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        if (launch != null) builder.setContentIntent(PendingIntent.getActivity(context, 0, launch,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
        int id = "US".equals(getInputData().getString("region")) ? 9821 : 9822;
        return Build.VERSION.SDK_INT >= 29
                ? new ForegroundInfo(id, builder.build(), ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
                : new ForegroundInfo(id, builder.build());
    }

    @Override public Result doWork() {
        Context context = getApplicationContext();
        String region = getInputData().getString("region");
        File report = null;
        synchronized (PYTHON_SERVICE_LOCK) {
            try {
                if (isStopped() || region == null || !SmaAlertBridge.enabled(context, region)) return Result.success();
                if (!SmaAlertBridge.notificationsAllowed(context)) {
                    SmaAlertBridge.error(context, "Android notification permission or channel is disabled.");
                    return Result.success();
                }
                setForegroundAsync(foreground()).get();
                String directory = SmaAlertBridge.config(context).getString("directory");
                String runId = UUID.randomUUID().toString();
                report = new File(new File(directory, "notification-jobs"), runId + ".json");
                JSONObject arguments = new JSONObject().put("region", region)
                        .put("directory", directory).put("run_id", runId);
                // A regular p4a service runs while WorkManager holds foreground
                // status. It uses its own process, never the paused Kivy loop.
                // Let the foreground transition reach ActivityManager before
                // starting the regular Python service on slower devices.
                long startDeadline=android.os.SystemClock.elapsedRealtime()+2000L;
                while (true) {
                    try {
                        ServiceSmaalerts.start(context, arguments.toString());
                        break;
                    } catch (IllegalStateException transition) {
                        if (isStopped() || android.os.SystemClock.elapsedRealtime()>=startDeadline) throw transition;
                        Thread.sleep(100);
                    }
                }
                serviceStarted = true;
                long deadline = android.os.SystemClock.elapsedRealtime() + 240000L;
                while (!report.isFile() && !isStopped() && android.os.SystemClock.elapsedRealtime() < deadline) {
                    Thread.sleep(400);
                }
                if (!report.isFile() && !isStopped()) SmaAlertBridge.error(context,
                        "Daily check timed out. Open the app's data request log.");
            } catch (Exception error) {
                SmaAlertBridge.error(context, "Daily check could not complete. Open Settings and the data request log.");
            } finally {
                if (serviceStarted) {
                    ServiceSmaalerts.stop(context);
                    serviceStarted = false;
                }
                if (report != null) report.delete();
                try {
                    if (region != null) SmaAlertBridge.schedule(context, region);
                } catch (Exception ignored) {
                    SmaAlertBridge.error(context, "Scheduling needs to be restored by opening the app.");
                }
            }
        }
        // Errors are logged; never retry a market slot repeatedly. A durable
        // Python journal also protects against OS restarts after partial work.
        return Result.success();
    }

    @Override public void onStopped() {
        if (serviceStarted) ServiceSmaalerts.stop(getApplicationContext());
        serviceStarted = false;
    }
}

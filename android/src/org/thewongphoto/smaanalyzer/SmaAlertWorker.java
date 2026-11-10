package org.thewongphoto.smaanalyzer;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.IBinder;
import androidx.work.Worker;
import androidx.work.WorkerParameters;
import org.json.JSONObject;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

/** A bounded, regular WorkManager job; its bound service needs no FGS startup. */
public final class SmaAlertWorker extends Worker {
    private static final Object PYTHON_SERVICE_LOCK = new Object();
    private final Object bindingLock = new Object();
    private ServiceConnection binding;
    private volatile boolean disconnected;
    private final CountDownLatch serviceExited = new CountDownLatch(1);
    private volatile File cancellation;

    public SmaAlertWorker(Context context, WorkerParameters parameters) { super(context, parameters); }

    private void releaseBinding() {
        synchronized (bindingLock) {
            if (binding == null) return;
            try { getApplicationContext().unbindService(binding); }
            catch (IllegalArgumentException ignored) { /* Already released by Android. */ }
            binding = null;
        }
    }

    @Override public Result doWork() {
        Context context = getApplicationContext();
        String job = getInputData().getString("job");
        if (job == null) job = getInputData().getString("region"); // Upgrade an already queued EOD job.
        final String identifier = job;
        boolean test = getInputData().getBoolean("test", false);
        File report = null;
        boolean bindingRequested = false;
        String stage = "configuration";
        synchronized (PYTHON_SERVICE_LOCK) {
            try {
                SmaAlertBridge.record(context, job, "started", "Native worker started; checking configuration.");
                if (isStopped()) return Result.success();
                if (job == null || !test && !SmaAlertBridge.enabled(context, job)) {
                    SmaAlertBridge.record(context, job, "disabled", "Job disabled; no Python service, API request or notification.");
                    return Result.success();
                }
                stage = "notification-permission";
                if (!SmaAlertBridge.notificationsAllowed(context)) {
                    SmaAlertBridge.record(context, job, "blocked", "Android notification permission or SMA alert channel is disabled.");
                    return Result.success();
                }
                String directory = SmaAlertBridge.config(context).getString("directory");
                String runId = UUID.randomUUID().toString();
                report = new File(new File(directory, "notification-jobs"), runId + ".json");
                if (!report.getParentFile().isDirectory() && !report.getParentFile().mkdirs())
                    throw new IllegalStateException("Notification job directory unavailable.");
                cancellation = new File(report.getParentFile(), runId + ".cancel");
                JSONObject arguments = new JSONObject().put("job", job).put("test", test)
                        .put("directory", directory).put("run_id", runId);
                long due = getInputData().getLong("due_at", 0);
                if (due > 0) arguments.put("due_at", due / 1000L);
                Intent intent = ServiceSmaalerts.getDefaultIntent(context, "", "", "", arguments.toString());
                intent.setClass(context, SmaBackgroundService.class);
                ServiceConnection connection = new ServiceConnection() {
                    @Override public void onServiceConnected(ComponentName name, IBinder binder) {
                        try { binder.linkToDeath(() -> serviceExited.countDown(), 0); }
                        catch (android.os.RemoteException error) { disconnected = true; serviceExited.countDown(); }
                        SmaAlertBridge.record(context, identifier, "connected", "Bound Python service connected; awaiting its result.");
                    }
                    @Override public void onServiceDisconnected(ComponentName name) { disconnected = true; serviceExited.countDown(); }
                    @Override public void onBindingDied(ComponentName name) { disconnected = true; serviceExited.countDown(); }
                    @Override public void onNullBinding(ComponentName name) { disconnected = true; serviceExited.countDown(); }
                };
                stage = "bind-python-service";
                synchronized (bindingLock) {
                    if (isStopped()) return Result.success();
                    if (!context.bindService(intent, connection, Context.BIND_AUTO_CREATE))
                        throw new IllegalStateException("Private Python service was not found.");
                    binding = connection;
                    bindingRequested = true;
                }
                SmaAlertBridge.record(context, job, "bound", "Python binding accepted; no foreground-service startup required.");
                stage = "python-result";
                long deadline = android.os.SystemClock.elapsedRealtime() + 240000L;
                while (!report.isFile() && !isStopped() && !disconnected && android.os.SystemClock.elapsedRealtime() < deadline)
                    Thread.sleep(200);
                if (isStopped()) {
                    SmaAlertBridge.record(context, job, "stopped", "Android stopped the worker; Python binding released.");
                } else if (!report.isFile()) {
                    SmaAlertBridge.record(context, job, "failed", disconnected
                            ? "Bound Python process disconnected before returning its result."
                            : "Bound Python job timed out after four minutes; inspect notification-service rows.");
                } else {
                    JSONObject result = new JSONObject(new String(Files.readAllBytes(report.toPath()), StandardCharsets.UTF_8));
                    String status = result.optString("status", "failed");
                    String detail = "Python job result: " + status + "; " + result.optInt("checked", 0) +
                            " SMAs checked; " + result.optInt("posted", 0) + " alerts posted.";
                    if ("failed".equals(status)) detail += " Stage: " + result.optString("stage", "signal-check") +
                            "; error class: " + result.optString("error_type", "see notification-check log");
                    SmaAlertBridge.record(context, job, status, detail);
                }
            } catch (Exception error) {
                SmaAlertBridge.failure(context, job, stage, error);
            } finally {
                releaseBinding();
                // p4a terminates its dedicated process on unbind. Do not bind
                // the next market/test job into a process that is still exiting.
                if (bindingRequested) {
                    try { serviceExited.await(5, TimeUnit.SECONDS); }
                    catch (InterruptedException interrupted) { Thread.currentThread().interrupt(); }
                }
                if (report != null) report.delete();
                if (!test && job != null) {
                    try { SmaAlertBridge.schedule(context, job); }
                    catch (Exception error) { SmaAlertBridge.failure(context, job, "schedule-next-slot", error); }
                }
            }
        }
        // Python's durable slot claim and real-session delivery keys suppress
        // replays after process restarts. Never repeatedly fetch a failed slot.
        return Result.success();
    }

    @Override public void onStopped() {
        File marker = cancellation;
        if (marker != null) {
            try { marker.createNewFile(); }
            catch (java.io.IOException error) { SmaAlertBridge.failure(getApplicationContext(), "worker", "cancel-python-job", error); }
        }
        releaseBinding();
    }
}

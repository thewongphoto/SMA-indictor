package org.thewongphoto.smaanalyzer;

import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;
import org.json.JSONObject;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.UUID;

/** Short bound Python job: WorkManager owns its wake lock and execution budget.
 * A bound service is allowed while the app is in the background. It does not
 * depend on an Activity, startService(), or a foreground-service transition.
 * Its dedicated process is essential: p4a kills that process on destruction.
 */
public final class SmaBackgroundService extends ServiceSmaalerts {
    private final IBinder binder = new Binder();
    private boolean started;
    private String arguments;

    @Override public IBinder onBind(Intent intent) {
        if (!started) {
            started = true;
            arguments = intent.getStringExtra("pythonServiceArgument");
            intent.putExtra("serviceStartAsForeground", "false");
            try { super.onStartCommand(intent, 0, 1); }
            catch (Throwable error) { reportFailure(arguments, "bind-bootstrap", error); }
        }
        return binder;
    }

    @Override public void run() {
        try { super.run(); }
        catch (Throwable error) {
            reportFailure(arguments, "native-python-startup", error);
            stopSelf();
        }
    }

    static void reportFailure(String payload, String stage, Throwable error) {
        // This process must not write the main process's SharedPreferences:
        // Android does not keep those caches coherent across processes.
        try {
            JSONObject input = new JSONObject(payload);
            String id = input.getString("run_id");
            if (!UUID.fromString(id).toString().equals(id)) throw new IllegalArgumentException();
            File output = new File(new File(input.getString("directory"), "notification-jobs"), id + ".json");
            output.getParentFile().mkdirs();
            JSONObject result = new JSONObject().put("status", "failed").put("checked", 0).put("posted", 0)
                    .put("stage", stage).put("error_type", error.getClass().getSimpleName());
            File temporary = new File(output.getParentFile(), id + ".native.tmp");
            Files.write(temporary.toPath(), result.toString().getBytes(StandardCharsets.UTF_8));
            if (!temporary.renameTo(output)) throw new IllegalStateException();
        } catch (Exception ignored) {
            android.util.Log.e("SmaAlertWorker", "Native Python startup failed; report could not be written.");
        }
    }
}

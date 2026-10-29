package org.thewongphoto.smaanalyzer;

import android.app.Activity;
import android.graphics.Insets;
import android.graphics.Rect;
import android.os.Build;
import android.view.DisplayCutout;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewTreeObserver;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.widget.FrameLayout;
import java.util.Arrays;

/** Report only bars/IME that overlap SDL's rendering surface (avoids double insets). */
public final class AndroidWindowBridge {
    public interface Listener {
        void onInsets(int left, int top, int right, int bottom, int keyboard,
                      int width, int height);
    }
    private static Activity activity;
    private static Listener listener;
    private static View observer;
    private static ViewTreeObserver.OnGlobalLayoutListener layoutListener;
    private static int[] last;

    private AndroidWindowBridge() {}

    public static void install(Activity owner, Listener callback) {
        owner.runOnUiThread(() -> {
            removeObserver();
            activity = owner;
            listener = callback;
            owner.getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
            ViewGroup content = owner.findViewById(android.R.id.content);
            // An independent observer preserves SDL's own insets listener.
            observer = new View(owner);
            content.addView(observer, new FrameLayout.LayoutParams(0, 0));
            observer.setOnApplyWindowInsetsListener((view, insets) -> {
                publish();
                return insets;
            });
            layoutListener = AndroidWindowBridge::publish;
            content.getViewTreeObserver().addOnGlobalLayoutListener(layoutListener);
            observer.requestApplyInsets();
            publish();
        });
    }

    private static View findSurface(View view) {
        if (view instanceof SurfaceView) return view;
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                View found = findSurface(group.getChildAt(i));
                if (found != null) return found;
            }
        }
        return null;
    }

    private static void publish() {
        if (activity == null || listener == null) return;
        View decor = activity.getWindow().getDecorView();
        View surface = findSurface(activity.findViewById(android.R.id.content));
        if (surface == null || surface.getWidth() == 0 || surface.getHeight() == 0) return;
        WindowInsets insets = decor.getRootWindowInsets();
        if (insets == null) return;
        int left, top, right, bottom, ime;
        if (Build.VERSION.SDK_INT >= 30) {
            Insets bars = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
            left = bars.left; top = bars.top; right = bars.right; bottom = bars.bottom;
            ime = insets.isVisible(WindowInsets.Type.ime())
                ? insets.getInsets(WindowInsets.Type.ime()).bottom : 0;
        } else {
            left = insets.getSystemWindowInsetLeft(); top = insets.getSystemWindowInsetTop();
            right = insets.getSystemWindowInsetRight(); bottom = insets.getSystemWindowInsetBottom();
            Rect visible = new Rect();
            decor.getWindowVisibleDisplayFrame(visible);
            int[] origin = new int[2];
            decor.getLocationOnScreen(origin);
            ime = Math.max(0, origin[1] + decor.getHeight() - visible.bottom);
            if (ime < decor.getHeight() * .15) ime = 0;
            if (bottom > decor.getHeight() * .15) bottom = 0;
            if (Build.VERSION.SDK_INT >= 28) {
                DisplayCutout cutout = insets.getDisplayCutout();
                if (cutout != null) {
                    left = Math.max(left, cutout.getSafeInsetLeft());
                    top = Math.max(top, cutout.getSafeInsetTop());
                    right = Math.max(right, cutout.getSafeInsetRight());
                    bottom = Math.max(bottom, cutout.getSafeInsetBottom());
                }
            }
        }
        int[] window = new int[2], render = new int[2];
        decor.getLocationOnScreen(window);
        surface.getLocationOnScreen(render);
        int renderRight = render[0] + surface.getWidth();
        int renderBottom = render[1] + surface.getHeight();
        int[] values = {
            Math.max(0, window[0] + left - render[0]),
            Math.max(0, window[1] + top - render[1]),
            Math.max(0, renderRight - (window[0] + decor.getWidth() - right)),
            Math.max(0, renderBottom - (window[1] + decor.getHeight() - bottom)),
            ime == 0 ? 0 : Math.max(0, renderBottom - (window[1] + decor.getHeight() - ime)),
            surface.getWidth(), surface.getHeight()
        };
        if (!Arrays.equals(last, values)) {
            last = values;
            listener.onInsets(values[0], values[1], values[2], values[3],
                              values[4], values[5], values[6]);
        }
    }

    private static void removeObserver() {
        if (observer != null && observer.getParent() instanceof ViewGroup) {
            ViewGroup content = (ViewGroup) observer.getParent();
            if (layoutListener != null && content.getViewTreeObserver().isAlive())
                content.getViewTreeObserver().removeOnGlobalLayoutListener(layoutListener);
            content.removeView(observer);
        }
        observer = null; layoutListener = null; listener = null; activity = null; last = null;
    }

    public static void uninstall() {
        if (activity != null) activity.runOnUiThread(AndroidWindowBridge::removeObserver);
    }
}

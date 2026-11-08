// Compile this file with ARC. The upstream Kivy main.m remains non-ARC.
#import <UIKit/UIKit.h>
#import <UserNotifications/UserNotifications.h>
#import <BackgroundTasks/BackgroundTasks.h>
#include <Python.h>

static NSString *SMAJSON(id value) {
    NSData *data = [NSJSONSerialization dataWithJSONObject:value options:0 error:nil];
    return [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
}
static NSDictionary *SMAObject(NSString *value) {
    id object = [NSJSONSerialization JSONObjectWithData:[value dataUsingEncoding:NSUTF8StringEncoding]
                                               options:0 error:nil];
    return [object isKindOfClass:[NSDictionary class]] ? object : @{};
}

@interface SMABackgroundRun : NSObject
@property(nonatomic, strong) BGTask *task;
@property(nonatomic) BOOL completed;
@end
@implementation SMABackgroundRun
@end

@interface SMAIOSBridge : NSObject <UNUserNotificationCenterDelegate>
@property(atomic) BOOL ready;
@property(atomic) NSInteger permissionResult;
@property(nonatomic) CGRect keyboardFrame;
@property(nonatomic, strong) NSMutableDictionary *deliveries;
@property(nonatomic, strong) NSMutableDictionary<NSString *, SMABackgroundRun *> *runs;
+ (instancetype)sharedBridge;
- (NSString *)configurationJSON;
- (BOOL)taskActive:(NSString *)token;
- (void)finishTask:(NSString *)token success:(BOOL)success;
- (void)handleTask:(BGTask *)task region:(NSString *)region;
- (void)ensureSchedule:(NSString *)region;
@end

@implementation SMAIOSBridge
+ (instancetype)sharedBridge {
    static SMAIOSBridge *instance;
    static dispatch_once_t once;
    dispatch_once(&once, ^{
        instance = [SMAIOSBridge new];
        instance.deliveries = [NSMutableDictionary new];
        instance.runs = [NSMutableDictionary new];
        instance.keyboardFrame = CGRectNull;
    });
    return instance;
}

+ (void)load {
    // Registration must precede the end of application launch, including a
    // cold background launch. Waiting for Python's App.build() is too late.
    @autoreleasepool {
        for (NSString *region in @[@"US", @"SG"]) {
            NSString *identifier = [NSString stringWithFormat:@"%@.refresh.%@", NSBundle.mainBundle.bundleIdentifier, region];
            [BGTaskScheduler.sharedScheduler registerForTaskWithIdentifier:identifier usingQueue:nil
                launchHandler:^(BGTask *task) { [[self sharedBridge] handleTask:task region:region]; }];
        }
    }
}

- (void)start {
    self.ready = YES;
    UNUserNotificationCenter.currentNotificationCenter.delegate = self;
    NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
    [center removeObserver:self];
    [center addObserver:self selector:@selector(keyboardChanged:) name:UIKeyboardWillChangeFrameNotification object:nil];
    [center addObserver:self selector:@selector(keyboardHidden:) name:UIKeyboardWillHideNotification object:nil];
}
- (void)stop { self.ready = NO; [NSNotificationCenter.defaultCenter removeObserver:self]; }
- (BOOL)isBackground { return UIApplication.sharedApplication.applicationState == UIApplicationStateBackground; }
- (void)pumpEvents {
    [NSRunLoop.currentRunLoop runMode:NSDefaultRunLoopMode beforeDate:[NSDate dateWithTimeIntervalSinceNow:.002]];
}
- (void)keyboardChanged:(NSNotification *)note {
    self.keyboardFrame = [note.userInfo[UIKeyboardFrameEndUserInfoKey] CGRectValue];
}
- (void)keyboardHidden:(NSNotification *)note { self.keyboardFrame = CGRectNull; }

- (NSString *)windowMetricsJSON {
    UIWindow *window = nil;
    for (UIScene *scene in UIApplication.sharedApplication.connectedScenes) {
        if (![scene isKindOfClass:UIWindowScene.class]) continue;
        for (UIWindow *candidate in ((UIWindowScene *)scene).windows)
            if (candidate.isKeyWindow) window = candidate;
    }
    UIView *view = window.rootViewController.view;
    if (!view) return SMAJSON(@{@"width":@1, @"height":@1});
    CGRect bounds = view.bounds;
    UIEdgeInsets safe = view.safeAreaInsets;
    CGFloat keyboard = 0;
    if (!CGRectIsNull(self.keyboardFrame)) {
        CGRect frame = [window convertRect:self.keyboardFrame fromWindow:nil];
        frame = [view convertRect:frame fromView:window];
        CGRect intersection = CGRectIntersection(bounds, frame);
        if (!CGRectIsNull(intersection) && CGRectGetMaxY(intersection) >= CGRectGetMaxY(bounds)-1
            && intersection.size.width >= bounds.size.width*.9) keyboard = intersection.size.height;
    }
    // Points and drawable pixels may differ; Python scales all seven values
    // together, then takes max(home indicator, keyboard), avoiding double padding.
    return SMAJSON(@{@"left":@(safe.left), @"right":@(safe.right), @"top":@(safe.top),
        @"bottom":@(safe.bottom), @"keyboard":@(keyboard),
        @"width":@(MAX(1,bounds.size.width)), @"height":@(MAX(1,bounds.size.height))});
}

- (void)requestPermission {
    self.permissionResult = -1;
    [UNUserNotificationCenter.currentNotificationCenter requestAuthorizationWithOptions:
        UNAuthorizationOptionAlert|UNAuthorizationOptionSound
        completionHandler:^(BOOL granted, NSError *error) { self.permissionResult = granted && !error ? 1 : 0; }];
}
- (void)setDelivery:(NSString *)token status:(NSString *)status detail:(NSString *)detail {
    @synchronized(self) {
        self.deliveries[token] = @{@"status":status, @"detail":detail};
    }
}
- (NSString *)postAlertJSON:(NSString *)value {
    NSDictionary *payload = SMAObject(value);
    NSString *token = NSUUID.UUID.UUIDString;
    [self setDelivery:token status:@"pending" detail:@""];
    [UNUserNotificationCenter.currentNotificationCenter getNotificationSettingsWithCompletionHandler:^(UNNotificationSettings *settings) {
        if (settings.authorizationStatus != UNAuthorizationStatusAuthorized
            && settings.authorizationStatus != UNAuthorizationStatusProvisional) {
            [self setDelivery:token status:@"failed" detail:@"Allow notifications for this app in iPhone Settings, then retry."];
            return;
        }
        NSString *background = payload[@"background_token"];
        if (background.length && ![self taskActive:background]) {
            [self setDelivery:token status:@"failed" detail:@"iOS ended the background check; no late notification was posted."];
            return;
        }
        if (![payload[@"id"] isKindOfClass:NSString.class] || ![payload[@"title"] isKindOfClass:NSString.class]
            || ![payload[@"body"] isKindOfClass:NSString.class]) {
            [self setDelivery:token status:@"failed" detail:@"Notification content is invalid."];
            return;
        }
        UNMutableNotificationContent *content = [UNMutableNotificationContent new];
        content.title = payload[@"title"];
        content.body = payload[@"body"];
        content.userInfo = @{@"banner":payload[@"banner"] ?: @YES, @"list":payload[@"list"] ?: @YES,
                             @"sound":payload[@"sound"] ?: @YES};
        if ([payload[@"sound"] boolValue]) content.sound = UNNotificationSound.defaultSound;
        UNNotificationRequest *request = [UNNotificationRequest requestWithIdentifier:payload[@"id"] content:content trigger:nil];
        [UNUserNotificationCenter.currentNotificationCenter addNotificationRequest:request withCompletionHandler:^(NSError *error) {
            [self setDelivery:token status:error ? @"failed" : @"ok"
                detail:error ? @"iOS rejected this notification. Check notification permission and try again." : @""];
        }];
    }];
    return token;
}
- (NSString *)deliveryResult:(NSString *)token {
    @synchronized(self) {
        NSDictionary *result = self.deliveries[token] ?: @{@"status":@"failed", @"detail":@"Notification request is unavailable."};
        if (![result[@"status"] isEqualToString:@"pending"]) [self.deliveries removeObjectForKey:token];
        return SMAJSON(result);
    }
}
- (void)userNotificationCenter:(UNUserNotificationCenter *)center willPresentNotification:(UNNotification *)notification
        withCompletionHandler:(void (^)(UNNotificationPresentationOptions))completion {
    NSDictionary *options = notification.request.content.userInfo;
    UNNotificationPresentationOptions presentation = 0;
    if ([options[@"banner"] boolValue]) presentation |= UNNotificationPresentationOptionBanner;
    if ([options[@"list"] boolValue]) presentation |= UNNotificationPresentationOptionList;
    if ([options[@"sound"] boolValue]) presentation |= UNNotificationPresentationOptionSound;
    completion(presentation);
}

- (NSString *)configurationJSON {
    return [NSUserDefaults.standardUserDefaults stringForKey:@"sma_daily_config"] ?: @"{}";
}
- (NSString *)identifier:(NSString *)region {
    return [NSString stringWithFormat:@"%@.refresh.%@", NSBundle.mainBundle.bundleIdentifier, region];
}
- (NSDate *)nextDate:(NSString *)region {
    NSDictionary *spec = SMAObject(self.configurationJSON)[@"schedules"][region];
    if (!spec) return nil;
    NSCalendar *calendar = [[NSCalendar alloc] initWithCalendarIdentifier:NSCalendarIdentifierGregorian];
    calendar.timeZone = [NSTimeZone timeZoneWithName:spec[@"timezone"]];
    NSDate *now = NSDate.date;
    for (NSInteger offset = 0; offset < 8; offset++) {
        NSDate *date = [calendar dateByAddingUnit:NSCalendarUnitDay value:offset toDate:now options:0];
        NSDateComponents *parts = [calendar components:NSCalendarUnitYear|NSCalendarUnitMonth|NSCalendarUnitDay|NSCalendarUnitWeekday fromDate:date];
        NSInteger weekday = (parts.weekday+5)%7;  // Sunday=1 -> Python Monday=0
        if (![spec[@"weekdays"] containsObject:@(weekday)]) continue;
        parts.hour = [spec[@"hour"] integerValue]; parts.minute = [spec[@"minute"] integerValue]; parts.second = 0;
        parts.weekday = NSDateComponentUndefined;
        NSDate *target = [calendar dateFromComponents:parts];
        if ([target compare:now] == NSOrderedDescending) return target;
    }
    return nil;
}
- (void)ensureSchedule:(NSString *)region {
    NSString *identifier = [self identifier:region];
    [BGTaskScheduler.sharedScheduler getPendingTaskRequestsWithCompletionHandler:^(NSArray<BGTaskRequest *> *requests) {
        if (![SMAObject(self.configurationJSON)[@"regions"] containsObject:region]) return;
        // Keep an overdue pending request: resubmitting on every foreground
        // launch would postpone it to tomorrow before iOS could execute it.
        for (BGTaskRequest *request in requests) if ([request.identifier isEqualToString:identifier]) return;
        BGAppRefreshTaskRequest *request = [[BGAppRefreshTaskRequest alloc] initWithIdentifier:identifier];
        request.earliestBeginDate = [self nextDate:region];
        NSError *error = nil;
        [BGTaskScheduler.sharedScheduler submitTaskRequest:request error:&error];
        if (error) [NSUserDefaults.standardUserDefaults setObject:@"iOS could not queue background refresh. Check Background App Refresh; timing remains controlled by iOS."
            forKey:@"sma_schedule_error"];
    }];
}
- (NSString *)configureJSON:(NSString *)value {
    NSDictionary *config = SMAObject(value);
    if (![config[@"directory"] isKindOfClass:NSString.class] || ![config[@"regions"] isKindOfClass:NSArray.class])
        return SMAJSON(@{@"status":@"failed", @"detail":@"iPhone daily-check configuration is invalid."});
    [NSUserDefaults.standardUserDefaults setObject:value forKey:@"sma_daily_config"];
    for (NSString *region in @[@"US",@"SG"])
        if ([config[@"regions"] containsObject:region]) [self ensureSchedule:region];
        else [BGTaskScheduler.sharedScheduler cancelTaskRequestWithIdentifier:[self identifier:region]];
    NSString *error = [NSUserDefaults.standardUserDefaults stringForKey:@"sma_schedule_error"];
    [NSUserDefaults.standardUserDefaults removeObjectForKey:@"sma_schedule_error"];
    BOOL available = UIApplication.sharedApplication.backgroundRefreshStatus == UIBackgroundRefreshStatusAvailable;
    NSString *detail = ![config[@"regions"] count] ? @"No enabled saved SMAs: background checks are off." :
        !available ? @"Background App Refresh is unavailable. Enable it in iPhone Settings; Low Power Mode can pause it." :
        @"iPhone background checks requested: US Tue–Sat 6:30am; SGX Mon–Fri 6:30pm, Singapore time. iOS chooses execution time and may skip checks.";
    return SMAJSON(@{@"status":error || !available ? @"unavailable" : @"requested", @"detail":error ?: detail});
}
- (BOOL)taskActive:(NSString *)token {
    @synchronized(self) { return self.runs[token] != nil && !self.runs[token].completed; }
}
- (void)finishTask:(NSString *)token success:(BOOL)success {
    @synchronized(self) {
        SMABackgroundRun *run = self.runs[token];
        if (!run || run.completed) return;
        run.completed = YES;
        [run.task setTaskCompletedWithSuccess:success];
        [self.runs removeObjectForKey:token];
    }
}
- (void)handleTask:(BGTask *)task region:(NSString *)region {
    NSString *token = NSUUID.UUID.UUIDString;
    SMABackgroundRun *run = [SMABackgroundRun new]; run.task = task;
    @synchronized(self) { self.runs[token] = run; }
    task.expirationHandler = ^{ [self finishTask:token success:NO]; };
    [self ensureSchedule:region];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_UTILITY,0), ^{
        // Cold launches initialize the shared interpreter once through Kivy.
        for (int i=0; i<100 && !self.ready && [self taskActive:token]; i++) [NSThread sleepForTimeInterval:.05];
        BOOL success = NO;
        if (self.ready && Py_IsInitialized() && [self taskActive:token]) {
            PyGILState_STATE gil = PyGILState_Ensure();
            PyObject *module = PyImport_ImportModule("sma_analyzer.ios_runtime");
            PyObject *function = module ? PyObject_GetAttrString(module,"run_background") : NULL;
            PyObject *result = function ? PyObject_CallFunction(function,"ss",region.UTF8String,token.UTF8String) : NULL;
            success = result && PyObject_IsTrue(result)==1;
            if (PyErr_Occurred()) PyErr_Print();
            Py_XDECREF(result); Py_XDECREF(function); Py_XDECREF(module);
            PyGILState_Release(gil);
        }
        [self finishTask:token success:success];
    });
}
@end

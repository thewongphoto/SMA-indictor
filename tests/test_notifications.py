from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock

from sma_analyzer.notifications import NotificationSettings, NotificationPresentation, evaluate_eod, deliver_alerts, validate_email, AndroidNotifier
from sma_analyzer.storage import LineStore, SavedLine


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'alerts.sqlite3'
        self.store = LineStore(self.path)
        self.line = SavedLine(1, 'DEMO-SGX', 'Sideways', 2, 12, True, True, True)
        self.settings = NotificationSettings('reader@example.com', True, True, True, True)
        self.store.save_notification_settings(self.settings)

    def test_buy_and_monitor_exact_content_and_channel_gates(self):
        alerts = evaluate_eod([10, 12, 10, 12], self.line, self.settings)
        self.assertEqual([a.kind for a in alerts], ['buy', 'buy'])
        self.assertEqual(alerts[0].body.splitlines()[0], 'Buy Signal: DEMO-SGX has crossed above SMA (2 days), target 12 /year')
        self.assertEqual(alerts[1].subject, 'Buy Signal for DEMO-SGX')
        monitor = evaluate_eod([10, 12, 10], self.line, self.settings)
        self.assertEqual([a.kind for a in monitor], ['monitor', 'monitor'])
        self.assertEqual(monitor[1].subject, 'Impending buy signal (End of trading) for DEMO-SGX')
        self.assertIn('Monitor: DEMO-SGX has closed below SMA (2 days), target 12 /year', monitor[1].body)
        self.assertIn('SIMULATED DATA', monitor[1].body)
        self.assertEqual(evaluate_eod([10,12,10,12], replace(self.line,push_enabled=False), self.settings)[0].channel, 'email')
        self.assertEqual(evaluate_eod([10,12,10,12], self.line,
                                     NotificationSettings(phone_buy=False,phone_monitor=False)), ())

    def test_equality_gaps_warmup_and_latest_session_only(self):
        # SMA 2: below -> equal -> equal -> above counts once, at session 6.
        values = [12,10,10,10,10,12]
        self.assertEqual(evaluate_eod(values,self.line,self.settings,5), ())
        self.assertTrue(all(a.kind == 'buy' for a in evaluate_eod(values,self.line,self.settings,6)))
        self.assertEqual(evaluate_eod([12,10,None,12,14],self.line,self.settings), ())
        self.assertEqual(evaluate_eod([12],self.line,self.settings), ())
        self.assertEqual(evaluate_eod([10,12,10,float('nan')],self.line,self.settings), ())
        self.assertEqual(evaluate_eod([10,12,10,12,14],self.line,self.settings), ())
        with self.assertRaisesRegex(ValueError,'session'):
            evaluate_eod(values,self.line,self.settings,0)

    def test_monitor_is_daily_and_hidden_line_still_alerts(self):
        line = replace(self.line, visible=False)
        a = evaluate_eod([14,12,10,8],line,self.settings,3)[0]
        b = evaluate_eod([14,12,10,8],line,self.settings,4)[0]
        self.assertEqual((a.kind,b.kind), ('monitor','monitor'))
        self.assertNotEqual(a.key,b.key)
        self.assertNotEqual(a.key,replace(a,scenario='Trending').key)

    def test_delivery_dedup_persists_failures_retry_and_unconnected_email(self):
        alerts = evaluate_eod([10,12,10,12],self.line,self.settings)
        phone = Mock()
        report = deliver_alerts(self.store, alerts, phone)
        phone.send.assert_called_once_with(alerts[0])
        self.assertIn('Email not sent',report[1])
        deliver_alerts(LineStore(self.path),alerts,phone)
        self.assertEqual(phone.send.call_count,1)
        self.assertFalse(self.store.was_delivered(alerts[1].key))
        next_alert = replace(alerts[0],session=5)
        phone.send.side_effect = RuntimeError('permission denied')
        self.assertIn('failed',deliver_alerts(self.store,[next_alert],phone)[0])
        self.assertFalse(self.store.was_delivered(next_alert.key))
        phone.send.side_effect = None
        self.assertIn('Posted to Android',deliver_alerts(self.store,[next_alert],phone)[0])

    def test_preview_has_no_delivery_side_effects(self):
        for _ in range(2):
            alerts = evaluate_eod([10,12,10,12],self.line,self.settings)
            self.assertEqual(len(alerts),2)
            self.assertTrue(all(not self.store.was_delivered(a.key) for a in alerts))

    def test_settings_address_validation_and_email_gate(self):
        self.store.save('DEMO-SGX','Sideways',2,12)
        line, = self.store.list_lines('DEMO-SGX','Sideways')
        self.store.save_notification_settings(NotificationSettings())
        with self.assertRaisesRegex(ValueError,'Settings'):
            self.store.set_notifications(line.id,'email',True)
        for bad in ['invalid','a@','a@b','a\nb@example.com','Name <a@example.com>']:
            with self.assertRaises(ValueError): validate_email(bad)
        self.store.save_notification_settings(self.settings)
        self.store.set_notifications(line.id,'email',True)
        self.store.set_notifications(line.id,'phone',True)
        saved, = LineStore(self.path).list_lines('DEMO-SGX','Sideways')
        self.assertTrue(saved.email_enabled and saved.push_enabled)
        with self.assertRaisesRegex(ValueError,'Turn off'):
            self.store.save_notification_settings(NotificationSettings())
        self.assertEqual(LineStore(self.path).notification_settings(),self.settings)

    def test_last_ten_only_saved_then_unsaved_and_restore(self):
        self.assertEqual(self.store.recent_unsaved(),[])
        # These represent 12 distinct formerly saved parameters, newest first.
        for period in range(2,14):
            self.store.save('DEMO-SGX','Sideways',period,12)
            line, = self.store.list_lines('DEMO-SGX','Sideways')
            self.store.set_notifications(line.id,'phone',True)
            self.store.delete(line.id)
            self.store.delete(line.id) # no phantom history for nonexistent entries
        recent = LineStore(self.path).recent_unsaved()
        self.assertEqual([r.period for r in recent],list(range(13,3,-1)))
        self.store.restore(recent[0].id)
        line, = self.store.list_lines('DEMO-SGX','Sideways')
        self.assertTrue(line.push_enabled)
        self.assertEqual(line.period,13)
        self.assertEqual(len(self.store.recent_unsaved()),9)
        with self.assertRaises(ValueError): self.store.restore(recent[0].id)
        self.store.save('DEMO-SGX','Sideways',12,12)
        self.assertNotIn(12,[r.period for r in self.store.recent_unsaved()])

    def test_existing_sqlite_schema_is_migrated_without_data_loss(self):
        old = Path(self.directory.name)/'old.sqlite3'
        with sqlite3.connect(old) as connection:
            connection.execute('CREATE TABLE saved_lines (id INTEGER PRIMARY KEY, counter TEXT, scenario TEXT, period INTEGER, target_frequency INTEGER, visible INTEGER, data_version INTEGER, UNIQUE(counter,scenario,period,target_frequency,data_version))')
            connection.execute("INSERT INTO saved_lines VALUES(7,'DEMO-SGX','Sideways',18,1,0,1)")
        migrated = LineStore(old)
        line, = migrated.list_lines('DEMO-SGX','Sideways')
        self.assertEqual((line.id,line.period,line.target_frequency,line.visible),(7,18,1,False))
        self.assertTrue(line.push_enabled)
        self.assertFalse(line.email_enabled)
        self.assertEqual(LineStore(old).list_lines('DEMO-SGX','Sideways'),[line])

    def test_android_desktop_failure_is_helpful(self):
        with self.assertRaisesRegex(RuntimeError,'Android development build'):
            AndroidNotifier().send(evaluate_eod([10,12,10,12],self.line,self.settings)[0])

    def test_cross_platform_banner_sound_and_center_policy_does_not_replay_existing_signals(self):
        alert=evaluate_eod([10,12,10,12],self.line,self.settings)[0]
        self.assertTrue(alert.presentation.banner and alert.presentation.sound and alert.presentation.notification_center)
        old_quiet=replace(alert,presentation=NotificationPresentation(banner=False,sound=False))
        self.assertEqual(alert.key,old_quiet.key)

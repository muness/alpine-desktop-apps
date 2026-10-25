#!/usr/bin/env python3
"""Native GTK4 front end for the Waydroid userspace setup helper."""
import os
import re
from pathlib import Path
import subprocess
import threading
import sys

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gtk, Gio, GLib
except (ImportError, ValueError):
    sys.exit('Install gtk4.0 and py3-gobject3, then launch Waydroid Setup again.')

HERE = Path(__file__).resolve().parent
BACKEND = str(HERE/'backend.py')

class SetupApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='io.github.muness.WaydroidSetup', flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.busy = False
        self.last_operation = 'No setup attempted.'
        self.connect('activate', self.activate)

    def activate(self, *_):
        if self.get_active_window():
            self.get_active_window().present(); return
        self.window = Gtk.ApplicationWindow(application=self, title='Waydroid Setup')
        self.window.set_default_size(680, 800)
        self.window.connect('close-request', lambda *_: self.busy)
        header = Gtk.HeaderBar()
        self.window.set_titlebar(header)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for edge in ('top', 'bottom', 'start', 'end'):
            getattr(box, 'set_margin_' + edge)(20)
        outer = Gtk.ScrolledWindow()
        outer.set_child(box)
        self.window.set_child(outer)
        title = Gtk.Label(label='Android on your DC-1', xalign=0)
        title.add_css_class('title-1'); box.append(title)
        intro = Gtk.Label(label='Install the Android environment, open it, or collect a report for help.\nThe Waydroid-capable kernel must already be installed and booted.', xalign=0, wrap=True)
        box.append(intro)
        note = Gtk.Label(label='Setup downloads 1–1.5 GB and needs 6 GiB free. Interpreter mode avoids the current Android crash but makes apps slower. Existing Android data is left alone.', xalign=0, wrap=True)
        box.append(note)
        self.choice = Gtk.DropDown.new_from_strings(['Vanilla — no Google apps (tested)', 'GApps — Google Play (untested)'])
        self.choice.set_size_request(-1, 44)
        box.append(self.choice)
        google_note = Gtk.Label(label='GApps includes Google services and can require device registration. Vanilla can use F-Droid or Aurora Store.', xalign=0, wrap=True)
        box.append(google_note)
        help_link = Gtk.LinkButton.new_with_label('https://docs.waydro.id/faq/google-play-certification', 'Google Play registration instructions')
        help_link.set_halign(Gtk.Align.START); box.append(help_link)
        self.status = Gtk.Label(label='Ready to check your system.', xalign=0, wrap=True)
        self.status.set_selectable(True); box.append(self.status)
        self.progress = Gtk.ProgressBar(show_text=True)
        self.progress.set_text('Ready')
        box.append(self.progress)
        self.progress_detail = Gtk.Label(xalign=0, wrap=True, selectable=True)
        box.append(self.progress_detail)
        self.determinate = False
        GLib.timeout_add(200, self.pulse_progress)
        actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(actions)
        self.buttons = []
        for label, callback in [('Check / report', self.check), ('Set up Android', self.setup), ('Open Android', self.launch), ('Remove Android…', self.confirm_remove)]:
            button = Gtk.Button(label=label)
            button.set_size_request(-1, 44)
            button.connect('clicked', callback)
            if label == 'Set up Android': button.add_css_class('suggested-action')
            self.buttons.append(button); actions.append(button)
        self.text = Gtk.TextView(editable=False, monospace=True, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.text.set_top_margin(10); self.text.set_bottom_margin(10)
        self.text.set_left_margin(10); self.text.set_right_margin(10)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=140)
        scroll.set_child(self.text); box.append(scroll)
        self.copy = Gtk.Button(label='Copy report for Discord or GitHub')
        self.copy.set_size_request(-1, 44)
        self.copy.connect('clicked', self.copy_report); box.append(self.copy)
        self.window.present()
        self.check()

    def set_busy(self, value):
        self.busy = value
        for button in self.buttons: button.set_sensitive(not value)
        self.copy.set_sensitive(not value)
        self.choice.set_sensitive(not value)
        if value:
            self.determinate = False
            self.progress.set_fraction(0)
            self.progress.set_text('Working…')
            self.progress_detail.set_text('')

    def pulse_progress(self):
        if self.busy and not self.determinate:
            self.progress.pulse()
        return True

    def append(self, text):
        match = re.match(r'Downloading ([^:]+): (\d+)% (.*)', text)
        if match:
            self.determinate = True
            self.progress.set_fraction(min(100, int(match[2])) / 100)
            self.progress.set_text(f'{match[1]} download — {match[2]}%')
            self.progress_detail.set_text(match[3])
            self.status.set_text('Downloading Android images. Time remaining is an estimate for this file.')
            # Keep the diagnostic log readable rather than adding every refresh.
            return False
        if self.busy and text and '\n' not in text:
            self.determinate = False
            self.progress.set_fraction(0)
            self.progress.set_text(text)
            self.progress_detail.set_text('')
        buffer = self.text.get_buffer()
        buffer.insert(buffer.get_end_iter(), text + '\n')
        return False

    def task(self, argv, action):
        if self.busy: return
        self.set_busy(True)
        self.text.get_buffer().set_text('')
        self.status.set_text('Authenticate in the system prompt to begin.' if action in ('setup', 'remove') else 'Checking your system…')
        def work():
            lines = []
            try:
                process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                for line in process.stdout:
                    line = line.rstrip(); lines.append(line)
                    GLib.idle_add(self.append, line)
                code = process.wait()
                if action in ('setup', 'remove') and code in (126, 127):
                    message = 'Administrator authentication was cancelled or unavailable. No operation started.'
                elif code:
                    message = 'Operation stopped. Read the last step below, then copy the report if you need help.'
                else:
                    message = 'Setup complete. Open Android to start your session.' if action == 'setup' else ('Android removed. See the report for what was retained.' if action == 'remove' else 'Report ready. Review it before sharing.')
                if action in ('setup', 'remove'):
                    # Backend output consists only of authored status lines.
                    self.last_operation = '\n'.join(lines[-12:]) or message
                    diagnostic = subprocess.run(['/usr/bin/python3', BACKEND, 'report'], capture_output=True, text=True, timeout=30)
                    GLib.idle_add(self.append, '\n' + diagnostic.stdout)
            except (OSError, subprocess.TimeoutExpired):
                message = 'Could not run the helper. Reinstall Waydroid Setup and retry.'
            GLib.idle_add(self.finish, message)
        threading.Thread(target=work, daemon=True).start()

    def finish(self, message):
        self.status.set_text(message); self.set_busy(False)
        self.progress.set_fraction(0)
        self.progress.set_text('Stopped' if 'stopped' in message.lower() or 'cancelled' in message.lower() or 'could not' in message.lower() else 'Finished')
        return False

    def check(self, *_):
        self.task(['/usr/bin/python3', BACKEND, 'report'], 'report')

    def setup(self, *_):
        variant = 'gapps' if self.choice.get_selected() == 1 else 'vanilla'
        self.task(['/usr/bin/pkexec', '/usr/bin/python3', BACKEND, 'setup', '--variant', variant], 'setup')

    def confirm_remove(self, *_):
        dialog = Gtk.Dialog(title='Remove Android?', transient_for=self.window, modal=True)
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        remove_button = dialog.add_button('Remove Android', Gtk.ResponseType.ACCEPT)
        remove_button.add_css_class('destructive-action')
        content = dialog.get_content_area()
        for edge in ('top', 'bottom', 'start', 'end'):
            getattr(content, 'set_margin_' + edge)(20)
        content.set_spacing(16)
        content.append(Gtk.Label(label='This stops Android and removes its packages.\nThe Linux kernel and recovery files stay installed.', wrap=True, xalign=0))
        erase = Gtk.CheckButton(label='Also delete Android apps, data and downloaded images')
        content.append(erase)
        content.append(Gtk.Label(label='Leave unchecked to keep your data. Deletion cannot be undone.\nOnly this desktop user’s Android data is selected.', wrap=True, xalign=0))
        def response(widget, response_id):
            wipe = erase.get_active(); widget.destroy()
            if response_id == Gtk.ResponseType.ACCEPT:
                command = ['/usr/bin/pkexec', '/usr/bin/python3', BACKEND, 'remove']
                if wipe: command.append('--erase-data')
                self.task(command, 'remove')
        dialog.connect('response', response)
        dialog.present()

    def launch(self, *_):
        if not os.environ.get('WAYLAND_DISPLAY'):
            self.status.set_text('Open this app from your Wayland desktop session.'); return
        try:
            subprocess.Popen(['waydroid', 'show-full-ui'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            self.status.set_text('Android launch requested. First startup can take two minutes. Use Check / report if no window appears.')
        except OSError:
            self.status.set_text('Waydroid is not installed. Run Set up Android first.')

    def copy_report(self, *_):
        buffer = self.text.get_buffer()
        content = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        self.window.get_clipboard().set(content + '\n\nLast setup attempt:\n' + self.last_operation)
        self.status.set_text('Report copied. Add what you expected and what happened before posting.')

if __name__ == '__main__':
    sys.exit(SetupApp().run(sys.argv))

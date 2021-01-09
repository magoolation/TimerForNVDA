# -*- coding: UTF-8 -*-
# A part of the EnhancedFind addon for NVDA
# Copyright (C) 2020 Marlon Sousa
# This file is covered by the GNU General Public License.
# See the file COPYING.txt for more details.

from . import conf
import core
from enum import Enum, unique
import gui
from logHandler import log
import locale
from gui import guiHelper
from .timer import getStatus, reportWithSound, reportWithSpeech, reportTimeCompletion, timer
from .types import TimeUnit, getOperationModes, getTimeUnits, TimerEvent
import string
import ui
import wx


class TimerDialog(wx.Dialog):
    """A dialog used to manager timer and stop watch.
    """

    def __init__(self, parent):
        # Translators: Title of a dialog to find text.
        super(TimerDialog, self).__init__(
            parent, wx.ID_ANY, _("Timer for NVDA"))

        # current operation mode
        self._operationMode = timer._mode

        self._buildGui()
        self._bindEvents()

    def _buildGui(self):
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainHelper = guiHelper.BoxSizerHelper(self, orientation=wx.VERTICAL)
        timerHelper = guiHelper.BoxSizerHelper(
            self, orientation=wx.HORIZONTAL)
        feedbackHelper = guiHelper.BoxSizerHelper(
            self, orientation=wx.HORIZONTAL)
        self._timerValueCtrl = timerHelper.addLabeledControl(
            "", wx.TextCtrl)
        self._timeUnitCTRL = timerHelper.addItem(wx.RadioBox(self, label=_(
            "Time unit"), choices=getTimeUnits(), majorDimension=1, style=wx.RA_SPECIFY_ROWS))
        mainHelper.addItem(timerHelper)
        self._operationModeCTRL = mainHelper.addLabeledControl(
            _("Type of watch"), wx.Choice, id=wx.ID_ANY, choices=getOperationModes())
        timerActions = guiHelper.ButtonHelper(wx.HORIZONTAL)
        self._startButton = timerActions.addButton(self, label=_("start"))
        self._pauseButton = timerActions.addButton(self, label=_("Pause"))
        self._stopButton = timerActions.addButton(self, label=_("stop"))
        mainHelper.addItem(timerActions)
        self._reportWithSoundCheckbox = feedbackHelper.addItem(
            wx.CheckBox(self, id=wx.ID_ANY, label=_("Report progress with sound")))
        self._reportWithSpeechCheckbox = feedbackHelper.addItem(
            wx.CheckBox(self, id=wx.ID_ANY, label=_("Report progress with speech")))
        mainHelper.addItem(feedbackHelper)
        dialogActions = guiHelper.ButtonHelper(wx.HORIZONTAL)
        self._closeButton = dialogActions.addButton(
            self, label=_("Close"), id=wx.ID_CANCEL)
        mainHelper.addItem(dialogActions)
        self._statusBar = wx.StatusBar(self, id=wx.ID_ANY)
        self._statusBar.SetStatusText(
            getStatus())
        mainHelper.addItem(self._statusBar, flag=wx.EXPAND)
        self._setInitialValues()
        self._configureReporter(self._reportWithSoundCheckbox, reportWithSound)
        self._configureReporter(
            self._reportWithSpeechCheckbox, reportWithSpeech)
        self._refreshUI()
        mainSizer.Add(mainHelper.sizer, border=10, flag=wx.ALL)
        mainSizer.Fit(self)
        self.SetSizer(mainSizer)
        self.CentreOnScreen()

    def _bindEvents(self):
        self._startButton.Bind(wx.EVT_BUTTON, self.OnStart)
        self._stopButton.Bind(wx.EVT_BUTTON, self.OnStop)
        self._pauseButton.Bind(wx.EVT_BUTTON, self.OnPause)
        self._timerValueCtrl.Bind(wx.EVT_CHAR, self.OnKeyPress)
        self._timeUnitCTRL.Bind(wx.EVT_RADIOBOX, self.OnTimeUnitChanged)
        self._reportWithSoundCheckbox.Bind(
            wx.EVT_CHECKBOX, self.OnReportWithSoundChanged)
        self._reportWithSpeechCheckbox.Bind(
            wx.EVT_CHECKBOX, self.OnReportWithSpeechChanged)
        self._closeButton.Bind(wx.EVT_BUTTON, self.OnClose)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        timer.registerReporter(self.OnTimer)

    def OnClose(self, event):
        timer.unregisterReporter(self.OnTimer)
        self.Destroy()

    def _setInitialValues(self):
        self._timeUnitCTRL.SetSelection(self._getIndex(
            getTimeUnits(), TimeUnit[conf.getConfig("timeUnit")].value))
        self._operationModeCTRL.SetSelection(self._getIndex(
            getOperationModes(), timer._mode.value))
        self._getTimerValueCtrlLabel().SetLabel(self._getTimerConfigLabel())
        self._reportWithSoundCheckbox.SetValue(
            conf.getConfig("reportWithSound"))
        self._reportWithSpeechCheckbox.SetValue(
            conf.getConfig("reportWithSpeech"))

    def _getIndex(self, items, item):
        for i, _ in enumerate(items):
            if items[i] == item:
                return i
        return -1

    def _refreshUI(self):
        self._startButton.Enable(not timer.isRunning(
        ) and self._timerValueCtrl.GetValue() != "" and float(self._timerValueCtrl.GetValue()) != 0)
        self._stopButton.Enable(timer.isRunning())
        self._pauseButton.Enable(timer.isRunning())
        self._operationModeCTRL.Enable(not timer.isRunning())
        self._timeUnitCTRL.Enable(not timer.isRunning())
        self._timerValueCtrl.SetEditable(not timer.isRunning())
        if not self._startButton.IsEnabled():
            self._stopButton.SetFocus()
        elif not self._stopButton.IsEnabled() and wx.Window.FindFocus() != self._timerValueCtrl:
            self._startButton.SetFocus()

    def _configureReporter(self, ctrl, reporter):
        if ctrl.IsChecked():
            timer.registerReporter(reporter)
        else:
            timer.unregisterReporter(reporter)

    def _getTimerValueCtrlLabel(self):
        # the TimerValueCtrl control is created by using NVDA guiHelper.BoxSizerHelper.addLabeledControl function
        # The problem with this is that BoxSizerHelper does not offer a way of retrieving either a reference for the label or even the id associated with the control
        # as a result, we can't change label content easily.
        # what we will do is we will get the TimerValueCtrl previous sibling control that happens to be its label, so we can change its content if needed
        return self._timerValueCtrl.GetPrevSibling()

    def _configureTimer(self):
        timer.setTimeUnitFromValue(self._timeUnitCTRL.GetStringSelection())

    def _persistConfiguration(self):
        conf.setConfig("timeUnit", timer._timeUnit.name)

    def OnKeyPress(self, evt):
        key = evt.GetKeyCode()
        character = chr(key)
        if key == 8 or key > 256 or character == locale.localeconv()["decimal_point"] or character in string.digits:
            wx.CallAfter(self._refreshUI)
            evt.Skip()

    def OnTimeUnitChanged(self, evt):
        self._getTimerValueCtrlLabel().SetLabel(self._getTimerConfigLabel())

    def OnReportWithSoundChanged(self, evt):
        self._configureReporter(self._reportWithSoundCheckbox, reportWithSound)
        conf.setConfig("reportWithSound",
                       self._reportWithSoundCheckbox.IsChecked())

    def OnReportWithSpeechChanged(self, evt):
        self._configureReporter(
            self._reportWithSpeechCheckbox, reportWithSpeech)
        conf.setConfig("reportWithSpeech",
                       self._reportWithSpeechCheckbox.IsChecked())

    def OnStart(self, evt):
        self._configureTimer()
        self._persistConfiguration()

        timer.startTimer(int(self._timerValueCtrl.GetValue()))

    def OnStop(self, evt):
        timer.stop()

    def OnPause(self, evt):
        timer.toggleOperation()

    def OnTimer(self, evt):
        if evt["type"] in [TimerEvent.STARTED, TimerEvent.STOPPED]:
            self._refreshUI()
            return
        if evt["type"] == TimerEvent.PAUSED:
            self._pauseButton.SetLabel(_("Resume"))
        elif evt["type"] == TimerEvent.RESUMED:
            self._pauseButton.SetLabel(_("Pause"))
        elif evt["type"] == TimerEvent.COUNTER:
            self._statusBar.SetStatusText(
                getStatus())

    def _getTimerConfigLabel(self):
        return f"amount of {self._timeUnitCTRL.GetStringSelection()} for {self._operationMode.value}"

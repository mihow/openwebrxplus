from owrx.source.direct import DirectSource, DirectSourceDeviceDescription
from owrx.command import Option
from typing import List
from owrx.form.input import Input, TextInput, CheckboxInput
from owrx.form.input.validator import Range

import logging

logger = logging.getLogger(__name__)


class FileSource(DirectSource):
    """
    SDR source that plays back IQ files for testing and demo purposes.

    Supports complex float32 (.cf32) files, with optional looping for
    continuous playback. Uses 'pv' for rate-limited playback to simulate
    real-time SDR data rates.
    """

    def getCommandMapper(self):
        return (
            super()
            .getCommandMapper()
            .setMappings(
                {
                    "file_path": Option(""),
                    "samp_rate": Option(""),
                }
            )
        )

    def getCommand(self):
        file_path = self.sdrProps["file_path"]
        sample_rate = self.sdrProps["samp_rate"]
        loop = self.sdrProps["loop"] if "loop" in self.sdrProps else True

        # cf32 format: 8 bytes per sample (4 bytes I + 4 bytes Q)
        byte_rate = sample_rate * 8

        if loop:
            # Loop the file continuously
            read_cmd = f"while true; do cat '{file_path}'; done"
        else:
            read_cmd = f"cat '{file_path}'"

        # Use pv (pipe viewer) for rate-limited playback
        # -q: quiet (no progress), -L: limit rate in bytes/sec
        playback_cmd = f"{read_cmd} | pv -q -L {byte_rate}"

        return [playback_cmd] + self.getNmuxCommand()

    def onPropertyChange(self, changes):
        # Restart source if file_path or loop changes
        if "file_path" in changes or "loop" in changes:
            self.logger.debug("restarting file source due to property changes: {0}".format(changes))
            self.stop()
            self.sleepOnRestart()
            self.start()

    def sleepOnRestart(self):
        # Brief pause before restart
        import time
        time.sleep(0.5)

    def getEventNames(self):
        return super().getEventNames() + ["file_path", "loop"]


class FileSourceDeviceDescription(DirectSourceDeviceDescription):
    def getName(self):
        return "IQ File Playback"

    def getInputs(self) -> List[Input]:
        return super().getInputs() + [
            TextInput(
                "file_path",
                "IQ File Path",
                infotext="Path to a complex float32 (.cf32) IQ recording file",
            ),
            CheckboxInput(
                "loop",
                "Loop playback",
                infotext="Continuously loop the IQ file for demo mode",
            ),
        ]

    def getDeviceMandatoryKeys(self):
        return super().getDeviceMandatoryKeys() + ["file_path"]

    def getDeviceOptionalKeys(self):
        return super().getDeviceOptionalKeys() + ["loop"]

    def getProfileOptionalKeys(self):
        return super().getProfileOptionalKeys() + ["loop"]

    def getSampleRateRanges(self) -> List[Range]:
        # File playback supports any sample rate
        return [Range(1000, 20000000)]

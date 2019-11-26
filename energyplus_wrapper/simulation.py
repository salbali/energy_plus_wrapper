#!/usr/bin/env python
# coding=utf-8

from typing import Callable

import attr
import plumbum
from path import Path
from plumbum import ProcessExecutionError

from .utils import process_eplus_html_report, process_eplus_time_series


def parse_generated_files_as_df(simulation):
    try:
        simulation.reports = dict(
            process_eplus_html_report(simulation.working_dir / "eplus-table.htm")
        )
    except FileNotFoundError:
        pass
    simulation.time_series = dict(process_eplus_time_series(simulation.working_dir))


@attr.s
class Simulation:
    """Object that contains all that is needed to run an EnergyPlus simulation.

    Attributes:
        name (str): simulation name
        eplus_bin (Path): EnergyPlus executable
        idf_file (Path): idf input file
        epw_file (Path): weather file
        idd_file (Path): idd file (should be in the EnergyPlus root)
        working_dir (Path): working folder, where the simulation will generate the files
        post_process (Callable): callable applied after a successful simulation.
            Take the simulation itself as argument.
        status (str): status of the simulation : either ["pending", "running",
            "interrupted", "failed"]
        reports (dict): if finished, contains the EPlus reports.
        time_series (dict): if finished, contains the EPlus time series results.
    """

    name = attr.ib(type=str)
    eplus_bin = attr.ib(type=str, converter=Path)
    idf_file = attr.ib(type=str, converter=Path)
    epw_file = attr.ib(type=str, converter=Path)
    idd_file = attr.ib(type=str, converter=Path)

    working_dir = attr.ib(type=str, converter=Path)

    post_process = attr.ib(
        type=Callable,
        default=parse_generated_files_as_df,
        converter=lambda x: x if x is not None else parse_generated_files_as_df,
    )

    status = attr.ib(type=str, default="pending")
    _log = attr.ib(type=str, default="", init=False, repr=False)
    reports = attr.ib(type=dict, default=None, repr=False)
    time_series = attr.ib(type=dict, default=None, repr=False)

    @property
    def log(self):
        """The log of finished simulation.

        Returns:
            str -- the log as a string
        """
        return self._log

    @property
    def eplus_base_exec(self):
        """give access to the EnergyPlus executable via plumbum
        """
        return plumbum.local[self.eplus_bin]

    @property
    def eplus_cmd(self):
        """return a pre-configured eplus executable that only need the weather
        file and the idf to be ran.
        """
        return self.eplus_base_exec["-s", "d", "-r", "-x", "-i", self.idd_file, "-w"]

    def run(self):
        """Run the EPlus simulation

        Returns:
            dict -- the energy plus report (from the html table-report
                generated by EPlus).
        """
        self.status = "running"
        try:
            self.status = "running"
            self._log = self.eplus_cmd[self.epw_file, self.idf_file]()
            self.status = "finished"
        except ProcessExecutionError:
            self.status = "failed"
            raise
        except KeyboardInterrupt:
            self.status = "interrupted"
            raise
        self.post_process(self)
        return self.reports

    def backup(self, backup_dir: Path):
        """Save all the files generated by energy-plus

        Files are saved in {backup_dir}/{sim.status}_{sim.name}

        Arguments:
            backup_dir {Path} -- where to save the files

        Returns:
            Path -- the exact folder where the data are saved.
        """
        (backup_dir / f"{self.status}_{self.name}").rmtree_p()
        backup_dir = Path(backup_dir).mkdir_p()
        saved_data = backup_dir / f"{self.status}_{self.name}"
        self.working_dir.copytree(saved_data)
        return saved_data

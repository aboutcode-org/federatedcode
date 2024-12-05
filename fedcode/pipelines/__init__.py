#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

import logging
from datetime import datetime
from datetime import timezone
from timeit import default_timer as timer

from aboutcode.pipeline import BasePipeline
from aboutcode.pipeline import humanize_time

module_logger = logging.getLogger(__name__)


class classproperty(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class FederatedCodePipeline(BasePipeline):
    pipeline_id = None  # Unique Pipeline ID

    def on_failure(self):
        """
        Tasks to run in the event that pipeline execution fails.

        Implement cleanup or other tasks that need to be performed
        on pipeline failure, such as:
            - Removing cloned repositories.
            - Deleting downloaded archives.
        """
        pass

    def execute(self):
        """Execute each steps in the order defined on this pipeline class."""
        self.log(f"Pipeline [{self.pipeline_name}] starting")

        steps = self.pipeline_class.get_steps(groups=self.selected_groups)
        steps_count = len(steps)
        pipeline_start_time = timer()

        for current_index, step in enumerate(steps, start=1):
            step_name = step.__name__

            if self.selected_steps and step_name not in self.selected_steps:
                self.log(f"Step [{step_name}] skipped")
                continue

            self.set_current_step(f"{current_index}/{steps_count} {step_name}")
            self.log(f"Step [{step_name}] starting")
            step_start_time = timer()

            try:
                step(self)
            except Exception as exception:
                self.log("Pipeline failed")
                on_failure_start_time = timer()
                self.log(f"Running [on_failure] tasks")
                self.on_failure()
                on_failure_run_time = timer() - on_failure_start_time
                self.log(f"Completed [on_failure] tasks in {humanize_time(on_failure_run_time)}")

                return 1, self.output_from_exception(exception)

            step_run_time = timer() - step_start_time
            self.log(f"Step [{step_name}] completed in {humanize_time(step_run_time)}")

        self.set_current_step("")  # Reset the `current_step` field on completion
        pipeline_run_time = timer() - pipeline_start_time
        self.log(f"Pipeline completed in {humanize_time(pipeline_run_time)}")

        return 0, ""

    def log(self, message, level=logging.INFO):
        """Log the given `message` to the current module logger and execution_log."""
        now_local = datetime.now(timezone.utc).astimezone()
        timestamp = now_local.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        message = f"{timestamp} {message}"
        module_logger.log(level, message)
        self.append_to_log(message)

    @classproperty
    def pipeline_id(cls):
        """Return unique pipeline_id set in cls.pipeline_id"""

        if cls.pipeline_id is None or cls.pipeline_id == "":
            raise NotImplementedError("pipeline_id is not defined or is empty")
        return cls.pipeline_id

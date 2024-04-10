# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities to create, delete, and SSH with TPUs."""


from airflow.decorators import task
from airflow.operators.bash import BashOperator


@task
def initialize(
    config_file: str,
) -> BashOperator:
  return BashOperator(
      task_id="initialize_ray",
      bash_command=f"ray up {config_file}",
  )


@task
def run(
    work_dir: str,
    script_file: str,
) -> BashOperator:
  return BashOperator(
      task_id="run_script",
      bash_command=(
          "export RAY_ADDRESS=http://127.0.0.1:8265 &&"
          f" ray job submit --working-dir {work_dir} python {script_file}"
      ),
  )

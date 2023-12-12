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

"""Config file for Google Cloud Project (GCP)."""

import dataclasses
from apis import metric_config
from typing import Optional


@dataclasses.dataclass
class GCPConfig:
  """This is a class to set up configs of GCP.

  Attributes:
    project_name: The name of a project for Composer env to run a test job.
    zone: The zone to run a test job.
    dataset_name: The option of dataset for metrics.
    cluster_project: The project of a cluster, i.e. a cluster running xpk workloads.
    cluster_name: The name of a cluster that has provisioned resources.
  """

  project_name: str
  zone: str
  dataset_name: metric_config.DatasetOption
  cluster_project: Optional[str] = None
  cluster_name: Optional[str] = None

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

"""A DAG to run all GKE examples."""

import datetime
from airflow import models
from dags.mlperf.configs import ray_test_config as config


with models.DAG(
    dag_id="ray_test",
    schedule=None,
    tags=["example", "ray"],
    start_date=datetime.datetime(2024, 4, 10),
    catchup=False,
) as dag:
  ray_test = config.get_ray_test_config().run()

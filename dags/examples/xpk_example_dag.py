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
from dags.common.vm_resource import TpuVersion, Project, Zone, XpkClusters, DockerImage
from dags.examples.configs import xpk_example_config as config
from dags.common import test_owner
from xlml.utils import name_format
from airflow.utils.task_group import TaskGroup

# TODO(ranran): add following examples:
# 1) jax_resnet_tpu_qr (diff dag)
# 2) jax_vit_tpu_qr_benchmark (diff dag)
# 3) jax_vit_tpu_xpk_benchmark (same dag)
with models.DAG(
    dag_id="gke_example_dag",
    schedule=None,
    tags=["example", "gke", "xlml", "benchmark"],
    start_date=datetime.datetime(2023, 11, 29),
    catchup=False,
) as dag:
  flax_resnet_tpu_singleslice_v4_8 = config.get_flax_resnet_xpk_config(
      test_name="resnet-single-slice",
      cluster=XpkClusters.TPU_V4_8_MAS_CLUSTER,
      docker_image=DockerImage.XPK_JAX_TEST.value,
      time_out_in_min=60,
  ).run()

  flax_resnet_tpu_multislice_v4_128 = config.get_flax_resnet_xpk_config(
      test_name="resnet-multi-slice",
      cluster=XpkClusters.TPU_V4_128_CLUSTER,
      docker_image=DockerImage.XPK_JAX_TEST.value,
      time_out_in_min=60,
      num_slices=2,
  ).run()

  # Example to run multiple tests that share one GCS location for artifacts
  # The value of 'test_group_id':
  #  1) a task group name for those chained tests
  #  2) an ID to generate gcs folder path in format:
  #    "{gcs_bucket.BASE_OUTPUT_DIR}/{gcs_subfolder}/{group_id}-{current_datetime}/"
  test_group_id = "chained_tests"
  gcs_subfolder = f"{test_owner.Team.MULTIPOD.value}/maxtext"
  with TaskGroup(group_id=test_group_id, prefix_group_id=False) as group:
    # With prefix_group_id=False, ensure each task
    # under your chained tests in the same DAG has a unique task id.
    # For gcs folder generation, the default task id is
    # `generate_gcs_folder_location`.
    shared_gcs_location = name_format.generate_gcs_folder_location.override(
        task_id=f"{test_group_id}_generate_gcs_folder_location"
    )(
        gcs_subfolder,
        test_group_id,
    )
    chained_resnet_tpu_singleslice_v4_8 = config.get_flax_resnet_xpk_config(
        test_name="chained-resnet-single-slice",
        cluster=XpkClusters.TPU_V4_8_MAS_CLUSTER,
        docker_image=DockerImage.XPK_JAX_TEST.value,
        time_out_in_min=60,
    ).run(gcs_location=shared_gcs_location)

    chained_resnet_tpu_multislice_v4_128 = config.get_flax_resnet_xpk_config(
        test_name="chained-resnet-multi-slice",
        cluster=XpkClusters.TPU_V4_128_CLUSTER,
        docker_image=DockerImage.XPK_JAX_TEST.value,
        time_out_in_min=60,
        num_slices=2,
    ).run(gcs_location=shared_gcs_location)

    (
        shared_gcs_location
        >> chained_resnet_tpu_singleslice_v4_8
        >> chained_resnet_tpu_multislice_v4_128
    )

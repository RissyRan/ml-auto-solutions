# Copyright 2024 Google LLC
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

"""A DAG to run end-to-end JAX Stable Stack tests for GCP GPUs."""


import datetime
from airflow import models
from dags import composer_env, test_owner, gcs_bucket
from dags.vm_resource import Project, TpuVersion, CpuVersion, Zone, DockerImage, GpuVersion, XpkClusters
from airflow.utils.task_group import TaskGroup
from dags.sparsity_diffusion_devx.configs import gke_config as config
from xlml.utils import name_format
from dags.multipod.configs.common import SetupMode

# Run once a day at 3 am UTC (7 pm PST)
SCHEDULED_TIME = "0 3 * * *" if composer_env.is_prod_env() else None


with models.DAG(
    dag_id="jax_stable_stack_gpu_e2e",
    schedule=SCHEDULED_TIME,
    tags=[
        "sparsity_diffusion_devx",
        "multipod_team",
        "maxtext",
        "gpu",
        "jax-stable-stack",
    ],
    start_date=datetime.datetime(2024, 6, 7),
    catchup=False,
) as dag:
  current_datetime = config.get_current_datetime()
  train_base = (
      "XLA_PYTHON_CLIENT_MEM_FRACTION=0.65 TF_FORCE_GPU_ALLOW_GROWTH=true "
      "python3 MaxText/train.py MaxText/configs/base.yml "
      "base_output_directory=gs://runner-maxtext-logs dataset_path=gs://maxtext-dataset "
      "steps=2 enable_checkpointing=false attention=dot_product"
  )
  test_models_gpu = {
      "train-c4-data": (
          f"{train_base} run_name=runner-{current_datetime}-0",
          1,
      ),
  }

  quarantine_task_group = TaskGroup(
      group_id="Quarantine", dag=dag, prefix_group_id=False
  )

  docker_images = [
      (SetupMode.STABLE, DockerImage.MAXTEXT_GPU_JAX_STABLE_STACK),
      (SetupMode.NIGHTLY, DockerImage.MAXTEXT_GPU_JAX_STABLE_STACK_NIGHTLY),
  ]

  for model, (test_script, nnodes) in test_models_gpu.items():
    for mode, image in docker_images:
      stable_a3_gpu = config.get_gpu_gke_test_config(
          time_out_in_min=300,
          test_name=f"maxtext-stable-stack-{mode.value}-{model}",
          run_model_cmds=(test_script,),
          num_slices=nnodes,
          cluster=XpkClusters.GPU_A3_CLUSTER,
          docker_image=image.value,
          test_owner=test_owner.PARAM_B,
      ).run_with_quarantine(quarantine_task_group)
      stable_a3plus_gpu = config.get_gpu_gke_test_config(
          time_out_in_min=300,
          test_name=f"maxtext-stable-stack-{mode.value}-{model}",
          run_model_cmds=(test_script,),
          num_slices=nnodes,
          cluster=XpkClusters.GPU_A3PLUS_CLUSTER,
          docker_image=image.value,
          test_owner=test_owner.PARAM_B,
      ).run_with_quarantine(quarantine_task_group)
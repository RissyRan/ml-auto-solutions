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

"Bash helper commands for AOTC artifacts"

import re
import os
from google.cloud import storage
import yaml


def set_variables_cmds():
  set_variables = (
      "export PROJECT=supercomputer-testing",
      "export CLUSTER=a3plus-benchmark",
      "export CLUSTER_REGION=australia-southeast1",
      "NOW=$(date +%s)",
      "export BUCKET_NAME=regression-testing-xlml",
  )
  return set_variables


def configure_project_and_cluster():
  set_project_command = (
      "gcloud config set project $PROJECT",
      "sudo chown -R airflow:airflow /home/airflow/composer_kube_config",
      "gcloud container clusters get-credentials "
      "$CLUSTER --region $CLUSTER_REGION",
  )
  return set_project_command


# This is required to get auth to access
def git_cookie_authdaemon():
  auth_cmds = (
      "git clone https://gerrit.googlesource.com/gcompute-tools",
      "echo 'trying to run git-cookie-authdaemon'",
      # Check if the daemon is already running
      "if pgrep -f git-cookie-authdaemon; then "
      "  echo 'git-cookie-authdaemon is already running'; "
      "else "
      "  ./gcompute-tools/git-cookie-authdaemon || echo 'Error running git-cookie-authdaemon'; "  # Run if not running
      "fi",
  )
  return auth_cmds


def clone_gob():
  gob_clone_cmds = (
      "echo 'trying to clone GoB repo from outside'",
      "git clone https://ai-hypercomputer-benchmarks.googlesource.com/"
      "reproducible-benchmark-recipes",
      "cd reproducible-benchmark-recipes/projects",
      "cd gpu-recipes",
      "pwd",
  )
  return gob_clone_cmds


def install_helm_cmds():
  install_helm_cmd = (
      "curl -fsSL -o get_helm.sh "
      "https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3",
      "chmod 700 get_helm.sh",
      "./get_helm.sh",
  )
  return install_helm_cmd


# By default the composer environment overwrites the
# namespaces to airflow namespaces.
# In order to prevent that it is necessary explicitly
# change the namespace to default.
def namespace_cmds():
  namespace = (
      "kubectl config view | grep namespace",
      "kubectl config set-context --current --namespace=default",
      "kubectl config set-context helm --namespace=default",
  )
  return namespace


def helm_apply_cmds():
  helm_cmds = (
      " helm install -f values.yaml "
      "--namespace default "
      "--set namespace=default"
      " --set-file nemo_config"
      "=$CONFIG_FILE"
      " --set workload.image"
      "=us-central1-docker.pkg.dev/"
      "supercomputer-testing/gunjanjalori/nemo_test/nemo_workload:24.07"
      " --set workload.gcsBucketForDataCataPath=$BUCKET_NAME"
      " $JOB_NAME $REPO_ROOT/src/helm-charts/a3mega/nemo-training",
  )
  return helm_cmds


def wait_for_jobs_cmds():
  wait_for_job = (
      "echo 'will wait for jobs to finish'",
      "kubectl wait --for=condition=complete "
      "job/$JOB_NAME --namespace=default --timeout=100m",
  )
  return wait_for_job


def copy_bucket_cmds():
  copy_bucket_contents = (
      "export COMPLETE_JOB_NAME=$(gcloud storage ls "
      "gs://$BUCKET_NAME/nemo-experiments/ | grep $JOB_NAME)",
      'echo "COMPLETE_JOB_NAME ${COMPLETE_JOB_NAME}"',
      "cd $REPO_ROOT/src/utils/training_metrics",
      "gcloud storage cp ${COMPLETE_JOB_NAME}"
      "dllogger/rank-0/dllogger.json .",
  )
  return copy_bucket_contents


def get_metrics_cmds(
    batch_size, num_accelerators, precision, model_id, accelertator_type
):
  # TODO(gunjanj007): get these parameters from the recipe
  cmds = (
      "METRICS_FILE=metrics.txt",
      "python3 process_training_results.py --file"
      f" dllogger.json --batch_size {batch_size} "
      f"--num_accelerators {num_accelerators} "
      f"--precision {precision}  "
      f"--model_type {model_id} "
      f"--accelerator_type {accelertator_type} | "
      "gsutil cp - $METRICS_FILE",
      'echo "METRICS_FILE=${METRICS_FILE}"',
  )
  return cmds


def get_aotc_repo():
  gob_clone_cmds = (
      "echo 'trying to clone GoB aotc repo'",
      "git clone https://cmcs-perf-tooling-internal.googlesource.com/"
      "benchmark-automation",
      "ls",
      "export PYTHONPATH=$PWD",
      'echo "PYTHONPATH=$PYTHONPATH"',
  )
  return gob_clone_cmds


def cleanup_cmds():
  cleanup = (
      "kubectl get pods "
      "--no-headers=true | awk '{print $1}' "
      "| grep $JOB_NAME | xargs kubectl delete pods",
      "helm uninstall $JOB_NAME",
  )
  return cleanup


def get_metrics(metrics_path):
  file_content = ""
  with open(metrics_path + "/metrics.txt", "r", encoding="utf-8") as file:
    file_content = file.read()

  # Parse the metrics (adjust based on your file format)
  lines = file_content.splitlines()
  average_step_time = float(lines[0].split(": ")[1])
  tflops_per_accelerator = float(lines[1].split(": ")[1])
  mfu = float(lines[2].split(": ")[1])

  print(f"Average Step Time: {average_step_time}")
  print(f"TFLOPS/Accelerator: {tflops_per_accelerator}")
  print(f"MFU: {mfu}")

  return average_step_time, mfu


def extract_python_path(last_line):
  python_path = last_line.split("=")[1]
  python_path_to_bq_writer = python_path + "/benchmark-automation/aotc/src"
  return python_path, python_path_to_bq_writer


def extract_run_details(tmpdir, yaml_file, config_path):
  gpus = None
  batch_size = None
  optimizer = None

  try:
    yaml_file_path = os.path.join(tmpdir, yaml_file)
    with open(yaml_file_path, "r", encoding="utf-8") as file:
      config = yaml.safe_load(file)
      gpus = config.get("workload", {}).get("gpus")
  except (FileNotFoundError, yaml.YAMLError) as e:
    print(f"Error: {e}")
    return None

  try:
    config_path = os.path.join(tmpdir, config_path)
    with open(config_path, "r", encoding="utf-8") as file:
      config = yaml.safe_load(file)
      batch_size = config.get("model", {}).get("global_batch_size")
      precision = config.get("trainer", {}).get("precision")
      optimizer = config.get("model", {}).get("optim", {}).get("name")
      seq_length = config.get("model", {}).get("data", {}).get("seq_length")
      max_steps = config.get("trainer", {}).get("max_steps")
  except (FileNotFoundError, yaml.YAMLError) as e:
    print(f"Error: {e}")
    return None

  return gpus, batch_size, optimizer, precision, seq_length, max_steps

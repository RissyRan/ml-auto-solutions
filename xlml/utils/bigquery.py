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

"""Utilities for tests to integrate with BigQuery."""


import dataclasses
import datetime
import enum
import math
from typing import Iterable, Optional
from absl import logging
from xlml.apis import metric_config
import google.auth
from google.cloud import bigquery


BQ_JOB_TABLE_NAME = "job_history"
BQ_METRIC_TABLE_NAME = "metric_history"
BQ_METADATA_TABLE_NAME = "metadata_history"


@dataclasses.dataclass
class JobHistoryRow:
  uuid: str
  timestamp: datetime.datetime
  owner: str
  job_name: str
  job_status: str


@dataclasses.dataclass
class MetricHistoryRow:
  job_uuid: str
  metric_key: str
  metric_value: float


@dataclasses.dataclass
class MetadataHistoryRow:
  job_uuid: str
  metadata_key: str
  metadata_value: str


@dataclasses.dataclass
class TestRun:
  job_history: JobHistoryRow
  metric_history: Iterable[MetricHistoryRow]
  metadata_history: Iterable[MetadataHistoryRow]


class JobStatus(enum.Enum):
  SUCCESS = 0
  FAILED = 1
  MISSED = 2


class BigQueryMetricClient:
  """BigQuery metric client for benchmark tests.

  Attributes:
    project: The project name for database.
    database: The database name for BigQuery.
  """

  def __init__(
      self,
      project: Optional[str] = None,
      database: Optional[str] = None,
  ):
    self.project = google.auth.default()[1] if project is None else project
    self.database = (
        metric_config.DatasetOption.XLML_DATASET.value if database is None else database
    )
    self.client = bigquery.Client(
        project=project,
        default_query_job_config=bigquery.job.QueryJobConfig(
            default_dataset=".".join((self.project, self.database)),
        ),
    )

  @property
  def job_history_table_id(self):
    return ".".join((self.project, self.database, BQ_JOB_TABLE_NAME))

  @property
  def metric_history_table_id(self):
    return ".".join((self.project, self.database, BQ_METRIC_TABLE_NAME))

  @property
  def metadata_history_table_id(self):
    return ".".join((self.project, self.database, BQ_METADATA_TABLE_NAME))

  def is_valid_metric(self, value: float):
    """Check if float metric is valid for BigQuery table."""
    invalid_values = [math.inf, -math.inf, math.nan]
    return not (value in invalid_values or math.isnan(value))

  def delete(self, row_ids: Iterable[str]) -> None:
    """Delete records from tables.

    There is a known issue that you cannot delete or update over table
    in the streaming buffer period, which can last up to 90 min. The
    error message is like `BigQuery Error : UPDATE or DELETE statement
    over table would affect rows in the streaming buffer, which is not supported`

    More context at https://cloud.google.com/knowledge/kb/update-or-delete-over-streaming-tables-fails-for-bigquery-000004334

    Args:
     row_ids: A list of ids to remove.
    """
    table_index_dict = {
        self.job_history_table_id: "uuid",
        self.metric_history_table_id: "job_uuid",
        self.metadata_history_table_id: "job_uuid",
    }

    for table, index in table_index_dict.items():
      for row_id in row_ids:
        query_statement = f"DELETE FROM `{table}` WHERE {index}='{row_id}'"
        query_job = self.client.query(query_statement)

        try:
          query_job.result()
          logging.info(
              f"No matching records or successfully deleted records in {table} with id {row_id}."
          )
        except Exception as e:
          raise RuntimeError(
              (
                  f"Failed to delete records in {table} with id {row_id} and error: `{e}`"
                  " Please note you cannot delete or update table in the streaming"
                  " buffer period, which can last up to 90 min after data insertion."
              )
          )

  def insert(self, test_runs: Iterable[TestRun]) -> None:
    """Insert Benchmark test runs into the table.

    Args:
      test_runs: Test runs in a benchmark test job.
    """
    for run in test_runs:
      # job hisotry rows
      job_history_rows = [dataclasses.astuple(run.job_history)]

      # metric hisotry rows
      metric_history_rows = []
      for each in run.metric_history:
        if self.is_valid_metric(each.metric_value):
          metric_history_rows.append(dataclasses.astuple(each))
        else:
          logging.error(f"Discarding metric as {each.metric_value} is invalid.")

      # metadata hisotry rows
      metadata_history_rows = []
      for each in run.metadata_history:
        metadata_history_rows.append(dataclasses.astuple(each))

      for table_id, rows in [
          (self.job_history_table_id, job_history_rows),
          (self.metric_history_table_id, metric_history_rows),
          (self.metadata_history_table_id, metadata_history_rows),
      ]:
        if not rows:
          continue
        logging.info(f"Inserting {len(rows)} rows into BigQuery table {table_id}.")
        table = self.client.get_table(table_id)
        errors = self.client.insert_rows(table, rows)

        if errors:
          raise RuntimeError(f"Failed to add rows to Bigquery: {errors}.")
        else:
          logging.info("Successfully added rows to Bigquery.")

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

# Format Python codes using Pyink

set -e

FOLDERS_TO_CHECK=("apis" "configs" "dags" "implementations")

for folder in "${FOLDERS_TO_UPLOAD[@]}"
do
  pyink "$folder" --pyink-indentation=2 --pyink-use-majority-quotes
done

echo "Successfully format codes."

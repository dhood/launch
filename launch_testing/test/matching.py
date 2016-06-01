#!/usr/bin/env python3

# Copyright 2015 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-output', action='store_true')
    parser.add_argument('--prepended-lines', action='store_true')
    parser.add_argument('--appended-lines', action='store_true')
    parser.add_argument('--interleaved-lines', action='store_true')
    parser.add_argument('--repeated-times', action='store', type=int, default=0)
    args = parser.parse_args()

    if not args.no_output:
        if args.prepended_lines:
            print('license output', file=sys.stdout)

        for i in range(args.repeated_times + 1):
            print('this is line 1', file=sys.stdout)

            if args.interleaved_lines:
                print('debug output', file=sys.stdout)

            print('this is line b', file=sys.stdout)

        if args.appended_lines:
            print('extra printout', file=sys.stdout)

    return 0


if __name__ == '__main__':
    sys.exit(main())

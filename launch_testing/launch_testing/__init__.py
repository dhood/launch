from importlib.machinery import SourceFileLoader
import io
import os
import re

import ament_index_python
from launch.output_handler import LineOutput


class UnmatchedOutputError(BaseException):
    pass


class InMemoryHandler(LineOutput):
    """Aggregate data from standard output.

    @param name: Name of the process being tested.
    @param launch_descriptor: L{LaunchDescriptor} object that contains the processes in the test.
    @param expected_lines: A list of lines to match the output literally or a regular expression
        that will only need one line to match, instead of the entire output.
    @param regex_match: If true, treat the expected_lines as a regular expression in match
        accordingly.
    @param filtered_prefixes: A list of prefixes that will cause output lines to be ignored if
        they start with one of the prefixes. By default lines starting with
        the process ID (`pid`) and return code (`rc`) will be ignored.
    @param filtered_rmw_implementations: A list of RMW implementations for which the output will
        be ignored in addition to the default/``filtered_prefixes``.
    @param exit_on_match: If True, then when its output is matched, this handler
        will terminate; otherwise it will simply keep track of the match.
    :raises: :py:class:`UnmatchedOutputError` if :py:meth:`check` does not find that the output
        matches as expected.
    """

    def __init__(
        self, name, launch_descriptor, expected_lines, regex_match=False,
        filtered_prefixes=None, filtered_rmw_implementations=None, exit_on_match=True
    ):
        super(LineOutput, self).__init__()
        if filtered_prefixes is None:
            self.filtered_prefixes = get_default_filtered_prefixes()
        else:
            self.filtered_prefixes = filtered_prefixes

        if filtered_rmw_implementations:
            for rmw_implementation in filtered_rmw_implementations:
                rmw_output_filter = get_rmw_output_filter(rmw_implementation)
                self.filtered_prefixes.extend(rmw_output_filter)

        self.name = name
        self.launch_descriptor = launch_descriptor
        self.expected_lines = expected_lines
        self.expected_output = b'\n'.join(self.expected_lines)
        self.left_over_stdout = b''
        self.left_over_stderr = b''
        self.stdout_data = io.BytesIO()
        self.stderr_data = io.BytesIO()
        self.regex_match = regex_match
        self.exit_on_match = exit_on_match
        self.matched = False

    def on_stdout_lines(self, lines):
        if self.matched:
            return

        for line in lines.splitlines():
            # Filter out stdout that comes from underlying DDS implementations
            if any([line.startswith(prefix) for prefix in self.filtered_prefixes]):
                continue
            self.stdout_data.write(line + b'\n')
            if not self.regex_match and not self.matched:
                output_lines = self.stdout_data.getvalue().splitlines()
                self.matched = output_lines == self.expected_lines

        # Are we ready to quit?
        if self.regex_match and not self.matched:
            self.matched = re.search(self.expected_output, self.stdout_data.getvalue())

        if self.matched and self.exit_on_match:
            # We matched and we're in charge; shut myself down
            for td in self.launch_descriptor.task_descriptors:
                if td.name == self.name:
                    td.terminate()
                    return

    def on_stderr_lines(self, lines):
        self.stderr_data.write(lines)

    def get_description(self):
        return 'InMemoryHandler: ' + self.name

    def check(self):
        output_lines = self.stdout_data.getvalue().splitlines()
        if not self.matched:
            raise UnmatchedOutputError(
                'Example output (%r) does not match expected output (%r)' %
                (output_lines, self.expected_lines))


def get_default_filtered_prefixes():
    return [
        b'pid', b'rc',
    ]


def get_rmw_output_filter(rmw_implementation):
    prefix_with_resource = ament_index_python.has_resource(
        'rmw_output_filter', rmw_implementation)
    if prefix_with_resource:
        rmw_filter_output_found = False
        relative_rmw_filter_output_path = ament_index_python.get_resource(
            'rmw_output_filter', rmw_implementation)
        rmw_filter_output_path = os.path.join(
            prefix_with_resource, 'share', rmw_implementation, relative_rmw_filter_output_path)
        if os.path.isfile(rmw_filter_output_path):
            with open(rmw_filter_output_path, 'r') as h:
                rmw_filter_output = h.read()
                rmw_filter_output_lines = rmw_filter_output.strip().split('\n')
                additional_filtered_prefixes = [
                    str.encode(l) for l in rmw_filter_output_lines]
                rmw_filter_output_found = True
        if not rmw_filter_output_found:
            raise LookupError(
                "Could not read RMW output filter for RMW implementation "
                "'%s' at expected location %s" % (rmw_implementation, rmw_filter_output_path))
    else:
        additional_filtered_prefixes = []
    return additional_filtered_prefixes


def create_handler(
    name, launch_descriptor, output_file, exit_on_match=True, filtered_prefixes=None,
    filtered_rmw_implementations=None
):
    literal_file = output_file + '.txt'
    if os.path.isfile(literal_file):
        with open(literal_file, 'rb') as f:
            expected_output = f.read().splitlines()
        return InMemoryHandler(
            name, launch_descriptor, expected_output, regex_match=False,
            exit_on_match=exit_on_match, filtered_prefixes=filtered_prefixes,
            filtered_rmw_implementations=filtered_rmw_implementations)
    regex_file = output_file + '.regex'
    if os.path.isfile(regex_file):
        with open(regex_file, 'rb') as f:
            expected_output = f.read().splitlines()
        return InMemoryHandler(
            name, launch_descriptor, expected_output, regex_match=True,
            exit_on_match=exit_on_match, filtered_prefixes=filtered_prefixes,
            filtered_rmw_implementations=filtered_rmw_implementations)
    py_file = output_file + '.py'
    if os.path.isfile(py_file):
        checker_module = SourceFileLoader(
            'checker_module', py_file).load_module()
        return checker_module.CheckerHandler(name, launch_descriptor)

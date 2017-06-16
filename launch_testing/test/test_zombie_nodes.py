from launch import LaunchDescriptor
from launch.exit_handler import primary_exit_handler
from launch.launcher import DefaultLauncher


def test_zombie_nodes():
    ld = LaunchDescriptor()

    ld.add_process(
        cmd=['talker'],
        name='talker',
        exit_handler=primary_exit_handler,
    )

    ld.add_process(
        cmd=['fail'],
        name='fail',
    )

    launcher = DefaultLauncher()
    launcher.add_launch_descriptor(ld)
    rc = launcher.launch()

    assert rc == 0, "The launch file failed with exit code '" + str(rc) + "'. "


if __name__ == '__main__':
    test_zombie_nodes()


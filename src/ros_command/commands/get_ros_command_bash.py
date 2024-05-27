import pathlib


def main():
    this_file = pathlib.Path(__file__)
    expected_dir = this_file.parent.parent
    bash = expected_dir / 'ros_command_setup.bash'
    print(bash)

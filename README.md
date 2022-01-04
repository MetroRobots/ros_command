# ros_command
## Unifying the ROS command line tools

One impairment to ROS 2 adoption is that all of the commands that have worked their way into muscle memory for ROS 1 developers no longer work. Also, all of the commands in ROS 2 tend to be at least two characters longer. To get information about a topic in ROS 1, one could type `rosto<tab>` (5 characters before tab), but in ROS 2 the equivalent is `ros2 to<tab>` (7 characters before tab).

The `ros_command` package provides a set of command line interfaces for common actions with syntax similar to ROS 1 and `catkin_tools`, since those are often simpler, shorter and more familiar to a majority of ROS developers [[citation needed]](https://xkcd.com/285/).

# Setup
This tool uses Python 3.

    git clone git@github.com:MetroRobots/ros_command.git
    cd ros_command
    sudo pip3 install -r requirements.txt

It also uses some BASH scripts. It is recommended that you add `source /path/to/ros_command/setup.bash` to your `.bashrc`. This will add the executable scripts to your `PATH` and add the library to your `PYTHONPATH`.

    echo "source $PWD/setup.bash" >> ~/.bashrc

Note that if you are using ROS 1, it is recommended that you source the setup AFTER you source ROS. Many of the commands in this library have the exact same syntax as their native ROS 1 counterparts, so sourcing after ROS gives these scripts priority.

# Commands

## roscd
This command was not implemented in ROS 2. There is the somewhat similar [`colcon_cd`](https://colcon.readthedocs.io/en/released/user/installation.html#quick-directory-changes) command, but it requires additional installation. Instead, this package has implemented a version of `roscd` that works with ROS 2. Because you cannot change the shell's working directory from within a Python script, `roscd` is implemented in `bash`.

## rosdep_install
One useful arcane command that pops up in many places/aliases (in both ROS 1 and ROS 2) is

    rosdep install --ignore-src -y -r --from-paths .


According to the manual , `rosdep install` will "download and install the dependencies of a given package or packages".
 * `--from-paths .` specifies that dependencies should be installed for all packages in the current directory
 * `--ignore-src` will ignore packages that you have the source code checked out
 * `-y` makes it non-interactive (so it defaults to installing everything without prompting)
 * `-r` continues when you get errors

Essentially, this is a command for installing all of the upstream dependencies for the packages in your workspace.

Now there's the new simple command `rosdep_install` which will do the same thing. A version with a terminal GUI similar to `rosbuild` is in development.


## rosmsg / rossrv / rosaction
In ROS 2, `rosmsg` and `rossrv` were replaced by `ros2 interface`, which can also handle actions. For most commands, calling the `rosbuild` version of `rosmsg` and `rossrv` will just call either the ROS 1 `rosmsg/rossrv` command or the equivalent `ros2 interface` command.

In ROS 1, if you call `rosaction <show|md5>`, it will run `rosmsg <command>` on the constituent parts (i.e. Goal/Result/Feedback). The other `rosaction <command>` variations will list only the appropriate content for packages with actions defined.

In ROS 2, if you call `ros<msg|srv|action> show`, there is advanced functionality for matching partial names.
The equivalent command to ROS 1's `rosmsg show Point` is `ros2 interface show geometry_msgs/msg/Point`. This is cumbersome for a number of reasons. First, ROS 1 is nearly half has short (17 chars vs 43 chars). It also requires you remember what package the message you are looking for is. The version implemented here will search for matching fully qualified names, and then print the fully qualified name and the contents of the interface definition.

## source_ros
If you use a single ROS workspace, then you probably source the appropriate `setup.bash` from the `.bashrc` file. However, if you use multiple, you can source the appropriate `setup.bash` with one simple command: `source_ros`. This will find the appropriate `setup.bash` by determining the current ROS Workspace based on the folder the script is executed in. Typically, this will either source the `devel/setup.bash` or `install/setup.bash` depending on whether it is ROS 1 or 2. (You can also have a setup.bash in the workspace root if you need custom logic to source additional environment variables.)

(Under the hood, this runs the `get_current_setup_bash` script to print the appropriate filename)

## rosrun and rosdebug
In ROS 1, `rosrun` works the same way as the standard ROS 1 version. In ROS 2, it runs `ros2 run`.

`rosdebug` does the same things, except it will insert `--prefix 'gdb -ex run --args'` into the appropriate place to run your node using `gdb`.

## rosclean
The `rosclean` command works as a hybrid of `rosclean` and `catkin clean`.
 * With no arguments (`rosclean`) the script will ask whether you want to delete the workspace's `devel/install/build/log` directories as well as the global `~/.ros/log` directory while also printing their sizes.
 * With the `-y` flag (`rosclean -y`) it will not prompt you and just delete things!
 * To just print the sizes without deleting anything, you can run `rosclean check` or `rosclean -c`.
 * You can also avoid the computation of folder sizes with the `-n` flag.
 * You can also provide a list of packages (`rosclean std_msgs nav2_core`) and it will attempt to delete just those portions of the workspace.

You can also throw the word `purge` at the beginning just to mirror the ROS 1 `rosclean` more closely.


# Power Usage
If you like really short, convenient commands, try adding these to your `~/.bashrc`

    alias sros='source_ros'                  # Easier tab completion than source_ros

# This file is intended to be source-d

# roscd is not a Python script because Python cannot change the directory
# https://stackoverflow.com/questions/18166977/cd-to-dir-after-exiting-script-system-independent-way-purely-in-python
# Attempt to implement roscd upstream: https://github.com/ros2/ros2cli/pull/75

# Only define roscd when it is not defined, i.e. don't overwrite the ROS 1 version
if ! type -t roscd >/dev/null 2>&1; then
    roscd()
    {
        if [[ -z "${ROS_VERSION}" ]]; then
            echo "Unable to determine ROS version"
            return
        fi

        cd $(get_ros_directory $1)
        return
    }

    # TODO: Reimplement completions
    _roscd_completions()
    {
        case $COMP_CWORD in
            1)
                COMPREPLY=($(compgen -W "$(ros2 pkg list | sed 's/\t//')" -- "${COMP_WORDS[1]}")) ;;
        esac
    }

    complete -F _roscd_completions roscd
fi

source_ros()
{
    LOCATION="$(get_current_setup_bash)"
    if [[ $LOCATION ]]
    then
        echo "Sourcing $LOCATION"
        source $LOCATION
    fi
}

argcomplete=$(which register-python-argcomplete{,3})

eval "$($argcomplete get_ros_directory)"
eval "$($argcomplete rosaction)"
eval "$($argcomplete rosbuild)"
eval "$($argcomplete rosclean)"
eval "$($argcomplete rosdebug)"
eval "$($argcomplete rosdep_install)"
eval "$($argcomplete rosexecute)"
eval "$($argcomplete roslaunch)"
eval "$($argcomplete rosmsg)"
eval "$($argcomplete rosrun)"
eval "$($argcomplete rossrv)"

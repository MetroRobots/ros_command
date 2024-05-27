# This file is intended to be source-d

# roscd is not a Python script because Python cannot change the directory
# https://stackoverflow.com/questions/18166977/cd-to-dir-after-exiting-script-system-independent-way-purely-in-python
# Attempt to implement roscd upstream: https://github.com/ros2/ros2cli/pull/75

# Only define roscd when it is not defined, i.e. don't overwrite the ROS 1 version
if ! $(type -t roscd) ; then
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

eval "$(register-python-argcomplete3 get_ros_directory)"
eval "$(register-python-argcomplete3 rosaction)"
eval "$(register-python-argcomplete3 rosbuild)"
eval "$(register-python-argcomplete3 rosclean)"
eval "$(register-python-argcomplete3 rosdebug)"
eval "$(register-python-argcomplete3 rosdep_install)"
eval "$(register-python-argcomplete3 rosexecute)"
eval "$(register-python-argcomplete3 roslaunch)"
eval "$(register-python-argcomplete3 rosmsg)"
eval "$(register-python-argcomplete3 rosrun)"
eval "$(register-python-argcomplete3 rossrv)"

#!/usr/bin/bash
FOLDER=$(realpath $( dirname "${BASH_SOURCE[0]}" ))
export PYTHONPATH=$FOLDER:$PYTHONPATH
export PATH=$FOLDER/bin:$PATH

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

        # If no arguments, go to the workspace root
        if [ $# == 0 ] ; then
            cd $(get_current_setup_bash)
            return
        fi

        PKG_ROS2_PATH="$(ros2 pkg prefix $1)"
        if [ "$PKG_ROS2_PATH" == "/opt/ros/$ROS_DISTRO" ]
        then
            cd "$PKG_ROS2_PATH/share/$1"
        else
            if [[ "$PKG_ROS2_PATH" == *"install"* ]]
            then
                # Move to root of project
                cd $(get_current_setup_bash)
                cd $(colcon list --packages-select "$1" --paths-only)
            else
                echo "Unable to find package $1"
            fi
        fi
    }

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

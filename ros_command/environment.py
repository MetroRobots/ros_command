def get_topics(version):
    if version == 1:
        import rosgraph
        m = rosgraph.Master('/ros_command')
        for topic, topic_type in m.getTopicTypes():
            yield topic
    else:
        from ros2cli.node.strategy import NodeStrategy
        with NodeStrategy({}) as node:
            for topic, msg_type in node.get_topic_names_and_types():
                yield topic
